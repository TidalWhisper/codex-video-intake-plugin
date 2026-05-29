#!/usr/bin/env python3
"""Assemble Stage 08 rough cut with FFmpeg.

Default mode performs normalized concat + optional audio mix + optional subtitle burn-in.
Test mode writes a non-empty placeholder rough_cut.mp4.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KNOWN_PLUGIN_ROOT_CHILDREN = {
    "video_projects",
    "templates",
    "config",
    "workflows",
    "skills",
    "scripts",
    "tests",
    "docs",
    "prompts",
}

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402


DEFAULT_OUTPUT_SPEC = {
    "width": 1080,
    "height": 1920,
    "fps": 24,
    "video_codec": "libx264",
    "pixel_format": "yuv420p",
    "audio_codec": "aac",
    "audio_sample_rate": 48000,
}


def resolve_path(base_json: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    special_roots: list[Path] = []
    plugin_root = next(
        (anchor.resolve() for anchor in [base_json.parent, *base_json.parents] if anchor.name == "codex-video-pipeline-plugin"),
        None,
    )
    repo_root = plugin_root.parent.parent.resolve() if plugin_root and plugin_root.parent.name == "plugins" else None
    if p.parts:
        first = p.parts[0].lower()
        if first == "plugins" and repo_root is not None:
            special_roots.append(repo_root)
        elif first in KNOWN_PLUGIN_ROOT_CHILDREN and plugin_root is not None:
            special_roots.append(plugin_root)
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [*special_roots, Path.cwd(), base_json.parent, *base_json.parents]:
        key = str(anchor.resolve()).lower()
        if key not in seen:
            anchors.append(anchor)
            seen.add(key)
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.exists():
            return candidate
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.parent.exists():
            return candidate
    return (base_json.parent / p).resolve()


def find_ffmpeg() -> str | None:
    configured = os.environ.get("FFMPEG_PATH", "").strip()
    if configured:
        candidate = Path(configured)
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg  # type: ignore

        candidate = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    except Exception:
        return None
    return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def placeholder_mp4_bytes(label: str) -> bytes:
    payload = ("PLACEHOLDER ROUGH CUT - NOT PRODUCTION OUTPUT - " + label).encode("utf-8")
    ftyp = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    free = len(payload) + 8
    return ftyp + free.to_bytes(4, "big") + b"free" + payload


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def output_spec_for_manifest(data: dict[str, Any]) -> dict[str, Any]:
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    existing = summary.get("output_video_spec") if isinstance(summary.get("output_video_spec"), dict) else {}
    spec = dict(DEFAULT_OUTPUT_SPEC)
    spec.update({key: existing[key] for key in existing if key in spec})
    return spec


def normalize_volume_db(track: dict[str, Any]) -> float:
    return safe_float(track.get("volume"), -6.0 if track.get("audio_type") in {"voiceover", "dialogue"} else -18.0)


def subtitle_burn_in_requested(data: dict[str, Any]) -> bool:
    subtitle_tracks = data.get("subtitle_tracks") if isinstance(data.get("subtitle_tracks"), list) else []
    return any(isinstance(track, dict) and track.get("burn_in") is True for track in subtitle_tracks)


def escape_subtitles_path(path: Path) -> str:
    raw = str(path.resolve()).replace("\\", "/")
    raw = raw.replace(":", "\\:")
    raw = raw.replace("'", r"\'")
    return raw


def build_filter_complex(
    data: dict[str, Any],
    manifest_path: Path,
    spec: dict[str, Any],
    *,
    burn_subtitles: bool,
    include_video: bool = True,
) -> tuple[str, bool]:
    parts: list[str] = []
    if include_video:
        width = safe_int(spec.get("width"), DEFAULT_OUTPUT_SPEC["width"])
        height = safe_int(spec.get("height"), DEFAULT_OUTPUT_SPEC["height"])
        fps = safe_int(spec.get("fps"), DEFAULT_OUTPUT_SPEC["fps"])
        video_chain = [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            f"fps={fps}",
            "format=yuv420p",
            "setsar=1",
        ]
        if burn_subtitles:
            subtitle_tracks = data.get("subtitle_tracks") if isinstance(data.get("subtitle_tracks"), list) else []
            subtitle_path = None
            for track in subtitle_tracks:
                if isinstance(track, dict) and track.get("burn_in") is True:
                    raw = track.get("path")
                    if isinstance(raw, str) and raw.strip():
                        subtitle_path = resolve_path(manifest_path, raw)
                        break
            if subtitle_path and subtitle_path.exists():
                video_chain.append(f"subtitles='{escape_subtitles_path(subtitle_path)}'")
        parts.append(f"[0:v]{','.join(video_chain)}[vout]")

    audio_tracks = data.get("audio_tracks") if isinstance(data.get("audio_tracks"), list) else []
    audio_labels: list[str] = []
    for idx, track in enumerate(audio_tracks, start=1):
        if not isinstance(track, dict):
            continue
        delay_ms = max(0, int(round(safe_float(track.get("start_sec"), 0.0) * 1000)))
        duration = safe_float(track.get("duration_sec"), 0.0)
        volume_db = normalize_volume_db(track)
        chain = ["aresample=48000"]
        if duration > 0:
            chain.append(f"atrim=0:{duration:.3f}")
        if delay_ms > 0:
            chain.append(f"adelay={delay_ms}|{delay_ms}")
        chain.append(f"volume={volume_db:.2f}dB")
        chain.append("apad")
        label = f"a{idx}"
        parts.append(f"[{idx}:a]{','.join(chain)}[{label}]")
        audio_labels.append(f"[{label}]")

    if audio_labels:
        parts.append(
            f"{''.join(audio_labels)}amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0:normalize=0,"
            "aresample=48000[aout]"
        )
    return ";".join(parts), bool(audio_labels)


def build_ffmpeg_attempts(data: dict[str, Any], manifest_path: Path, ffmpeg_path: str) -> list[dict[str, Any]]:
    concat_list = resolve_path(manifest_path, data.get("concat_list_path") or "ffmpeg_concat_list.txt")
    final_output = resolve_path(manifest_path, data.get("final_output_path") or "rough_cut/rough_cut.mp4")
    spec = output_spec_for_manifest(data)
    burn_subtitles = subtitle_burn_in_requested(data)
    filter_complex, has_audio_mix = build_filter_complex(data, manifest_path, spec, burn_subtitles=burn_subtitles)
    rough_cut_duration = safe_float(
        (data.get("summary") or {}).get("rough_cut_duration_sec"),
        sum(
            safe_float(item.get("duration_sec"), 0.0)
            for item in (data.get("timeline") if isinstance(data.get("timeline"), list) else [])
            if isinstance(item, dict)
        ),
    )

    audio_tracks = data.get("audio_tracks") if isinstance(data.get("audio_tracks"), list) else []
    inputs = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error", "-fflags", "+genpts", "-f", "concat", "-safe", "0", "-i", str(concat_list)]
    for track in audio_tracks:
        if not isinstance(track, dict):
            continue
        audio_path = resolve_path(manifest_path, track.get("audio_path") or "")
        inputs.extend(["-i", str(audio_path)])

    attempts: list[dict[str, Any]] = []
    if not has_audio_mix and not burn_subtitles:
        attempts.append({
            "strategy": "concat_copy",
            "command": [
                *inputs,
                "-c", "copy",
                "-movflags", "+faststart",
                str(final_output),
            ],
        })

    if has_audio_mix and not burn_subtitles:
        audio_only_filter, _ = build_filter_complex(
            data,
            manifest_path,
            spec,
            burn_subtitles=False,
            include_video=False,
        )
        copy_video_mix = [*inputs]
        if audio_only_filter:
            copy_video_mix.extend(["-filter_complex", audio_only_filter])
        copy_video_mix.extend([
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", str(spec["audio_codec"]),
            "-ar", str(spec["audio_sample_rate"]),
            "-movflags", "+faststart",
            "-t", f"{rough_cut_duration:.3f}",
            "-shortest",
            str(final_output),
        ])
        attempts.append({
            "strategy": "copy_video_mix_audio",
            "command": copy_video_mix,
        })

    reencode_base = [
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
    ]
    if has_audio_mix:
        reencode_base.extend(["-map", "[aout]"])
    else:
        reencode_base.append("-an")
    reencode_base.extend([
        "-r", str(spec["fps"]),
        "-c:v", str(spec["video_codec"]),
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", str(spec["pixel_format"]),
    ])
    if has_audio_mix:
        reencode_base.extend(["-c:a", str(spec["audio_codec"]), "-ar", str(spec["audio_sample_rate"])])
    reencode_base.extend(["-movflags", "+faststart", "-t", f"{rough_cut_duration:.3f}", "-shortest", str(final_output)])
    attempts.append({
        "strategy": "reencode_mix",
        "command": reencode_base,
    })

    fallback_base = [
        *inputs,
        "-max_muxing_queue_size", "2048",
        "-vsync", "cfr",
        "-filter_complex", filter_complex,
        "-map", "[vout]",
    ]
    if has_audio_mix:
        fallback_base.extend(["-map", "[aout]"])
    else:
        fallback_base.append("-an")
    fallback_base.extend([
        "-r", str(spec["fps"]),
        "-c:v", str(spec["video_codec"]),
        "-preset", "ultrafast",
        "-crf", "20",
        "-pix_fmt", str(spec["pixel_format"]),
    ])
    if has_audio_mix:
        fallback_base.extend(["-c:a", str(spec["audio_codec"]), "-ar", str(spec["audio_sample_rate"])])
    fallback_base.extend(["-movflags", "+faststart", "-t", f"{rough_cut_duration:.3f}", "-shortest", str(final_output)])
    attempts.append({
        "strategy": "reencode_mix_fallback",
        "command": fallback_base,
    })
    return attempts


def record_attempt(data: dict[str, Any], *, provider: str, strategy: str, command: list[str], return_code: int, stdout: str, stderr: str) -> None:
    data.setdefault("ffmpeg_commands", [])
    data["ffmpeg_commands"].append({
        "command": command,
        "provider": provider,
        "strategy": strategy,
        "return_code": return_code,
        "stdout_excerpt": stdout.strip()[-2000:],
        "stderr_excerpt": stderr.strip()[-2000:],
        "ran_at": utc_now(),
    })


def finalize_manifest(
    data: dict[str, Any],
    path: Path,
    out: Path,
    *,
    provider: str,
    error: str | None = None,
) -> None:
    exists = out.exists() and out.is_file()
    size = out.stat().st_size if exists else 0
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    concat_list = resolve_path(path, data.get("concat_list_path") or "ffmpeg_concat_list.txt")
    edit_list = resolve_path(path, data.get("edit_decision_list_path") or "edit_decision_list.json")
    mix_plan = resolve_path(path, data.get("audio_mix_plan_path") or "audio_mix_plan.json")
    spec = output_spec_for_manifest(data)
    if error:
        data.setdefault("errors", [])
        data["errors"].append({"message": error, "created_at": utc_now(), "provider": provider})
    data.setdefault("evidence", {})
    data["evidence"].update({
        "file_path": str(out).replace("\\", "/"),
        "file_exists": exists,
        "file_size_bytes": size,
        "created_at": utc_now() if exists else None,
    })
    data.setdefault("summary", {})
    data["summary"]["output_video_spec"] = spec
    data.setdefault("self_check", {})
    data["self_check"].update({
        "has_timeline_from_confirmed_clips": bool(data.get("timeline")),
        "has_audio_mix_plan": mix_plan.exists(),
        "has_edit_decision_list": edit_list.exists(),
        "has_final_output_file": exists and size > 0,
        "ready_for_qa_stage": exists and size > 0,
    })
    if exists and size > 0:
        data["status"] = "generated"
        data["allowed_next_stage"] = next_stage_after("STAGE_08_ASSEMBLY", routing, "STAGE_09_QA")
        data["assembly_provider"] = provider
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_08_ASSEMBLY_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"assembly_confirmed": True},
            status="active",
        )
    else:
        data["status"] = "in_progress"
        data["allowed_next_stage"] = None
    data["updated_at"] = utc_now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_source_inputs(data: dict[str, Any], manifest_path: Path) -> str | None:
    concat_list = resolve_path(manifest_path, data.get("concat_list_path") or "ffmpeg_concat_list.txt")
    if not concat_list.exists():
        return f"concat list not found: {concat_list}"
    timeline = data.get("timeline") if isinstance(data.get("timeline"), list) else []
    for item in timeline:
        if not isinstance(item, dict):
            continue
        raw = item.get("clip_path")
        if not isinstance(raw, str) or not raw.strip():
            return f"timeline clip_path missing for shot: {item.get('shot_id')}"
        clip_path = resolve_path(manifest_path, raw)
        if not clip_path.exists() or not clip_path.is_file() or clip_path.stat().st_size <= 0:
            return f"timeline clip file missing or empty: {clip_path}"
    audio_tracks = data.get("audio_tracks") if isinstance(data.get("audio_tracks"), list) else []
    for item in audio_tracks:
        if not isinstance(item, dict):
            continue
        raw = item.get("audio_path")
        if not isinstance(raw, str) or not raw.strip():
            return f"audio track path missing for audio_id: {item.get('audio_id')}"
        audio_path = resolve_path(manifest_path, raw)
        if not audio_path.exists() or not audio_path.is_file() or audio_path.stat().st_size <= 0:
            return f"audio track file missing or empty: {audio_path}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--placeholder-test", action="store_true", help="Create non-empty placeholder rough_cut.mp4 for local pipeline tests only")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Allow this executor to run even when the project brief requested an earlier terminal output")
    args = parser.parse_args(argv)
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not args.allow_beyond_requested_scope:
        scope_error = requested_output_scope_guard_message("STAGE_08", compiled_requirements_from_context(data))
        if scope_error:
            print(f"ERROR: {scope_error}")
            return 1
    out = resolve_path(path, data.get("final_output_path") or "rough_cut/rough_cut.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.placeholder_test:
        out.write_bytes(placeholder_mp4_bytes(data.get("project_id", "project")))
        record_attempt(
            data,
            provider="placeholder_test_assembly_generator",
            strategy="placeholder_test",
            command=["placeholder_test"],
            return_code=0,
            stdout="placeholder rough cut generated",
            stderr="",
        )
        finalize_manifest(data, path, out, provider="placeholder_test_assembly_generator")
        print(f"PLACEHOLDER ROUGH CUT GENERATED: {out}")
        return 0

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        error = "ffmpeg executable not found in PATH"
        finalize_manifest(data, path, out, provider="ffmpeg", error=error)
        print(f"ERROR: {error}")
        return 1

    source_error = validate_source_inputs(data, path)
    if source_error:
        finalize_manifest(data, path, out, provider="ffmpeg", error=source_error)
        print(f"ERROR: {source_error}")
        return 1

    attempts = build_ffmpeg_attempts(data, path, ffmpeg)
    last_error = "ffmpeg failed"
    for attempt in attempts:
        cmd = attempt["command"]
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        record_attempt(
            data,
            provider="ffmpeg",
            strategy=str(attempt["strategy"]),
            command=cmd,
            return_code=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )
        if result.returncode == 0 and out.exists() and out.is_file() and out.stat().st_size > 0:
            finalize_manifest(data, path, out, provider="ffmpeg")
            print(f"FFMPEG ROUGH CUT GENERATED: {out}")
            return 0
        last_error = ((result.stderr or result.stdout or "ffmpeg failed").strip() or "ffmpeg failed")[-2000:]

    finalize_manifest(data, path, out, provider="ffmpeg", error=last_error)
    print("FFMPEG ASSEMBLY FAILED")
    print(last_error)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
