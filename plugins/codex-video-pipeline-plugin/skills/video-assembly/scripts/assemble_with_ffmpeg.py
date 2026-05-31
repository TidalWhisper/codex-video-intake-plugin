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
from pipeline_core.media_evidence import MIN_PRODUCTION_VIDEO_BYTES, assembly_output_ready, clip_output_ready, provider_is_nonproduction  # noqa: E402
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
    base_abs = base_json if base_json.is_absolute() else (Path.cwd() / base_json).resolve()

    def plugin_root_candidates() -> list[Path]:
        candidates: list[Path] = []
        seen: set[str] = set()

        def add(path: Path) -> None:
            resolved = path.resolve()
            if resolved.name != "codex-video-pipeline-plugin":
                return
            key = str(resolved).lower()
            if key not in seen:
                candidates.append(resolved)
                seen.add(key)

        for anchor in [base_abs.parent, *base_abs.parents]:
            add(anchor)
        cwd = Path.cwd().resolve()
        for anchor in [cwd, *cwd.parents]:
            add(anchor)
        add(ROOT)
        return candidates

    plugin_roots = plugin_root_candidates()
    special_roots: list[Path] = []
    repo_roots: list[Path] = []
    for plugin_root in plugin_roots:
        if plugin_root.parent.name == "plugins":
            repo_root = plugin_root.parent.parent.resolve()
            if repo_root not in repo_roots:
                repo_roots.append(repo_root)
    if p.parts:
        first = p.parts[0].lower()
        if first == "plugins":
            special_roots.extend(repo_roots)
        elif first in KNOWN_PLUGIN_ROOT_CHILDREN:
            special_roots.extend(plugin_roots)
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [*special_roots, *repo_roots, *plugin_roots, Path.cwd().resolve(), base_abs.parent, *base_abs.parents]:
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
    return (base_abs.parent / p).resolve()


def maybe_load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists() or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def clip_manifest_ready(manifest_path: Path | None, clip_manifest: dict[str, Any]) -> bool:
    if manifest_path is None or not clip_manifest:
        return False
    if not bool((clip_manifest.get("self_check") or {}).get("ready_for_audio_stage")):
        return False
    jobs = clip_manifest.get("jobs") if isinstance(clip_manifest.get("jobs"), list) else []
    if not jobs:
        return False
    for job in jobs:
        if not isinstance(job, dict):
            return False
        raw = job.get("output_path") or (job.get("evidence") or {}).get("file_path")
        if not raw:
            return False
        clip_path = resolve_path(manifest_path, str(raw))
        if not clip_output_ready(clip_path, job.get("provider")):
            return False
    return True


def upstream_blocking_state(base_json: Path, data: dict[str, Any]) -> tuple[str, dict[str, bool], list[str]]:
    clip_manifest_path = resolve_path(base_json, data.get("source_video_clip_manifest") or "")
    audio_manifest_path = resolve_path(base_json, data.get("source_audio_manifest") or "")
    clip_manifest = maybe_load_json(clip_manifest_path)
    audio_manifest = maybe_load_json(audio_manifest_path)
    blockers: list[str] = []
    clip_ready = clip_manifest_ready(clip_manifest_path, clip_manifest) if clip_manifest else True
    audio_ready = bool((audio_manifest.get("self_check") or {}).get("ready_for_assembly_stage")) if audio_manifest else True
    if not clip_ready:
        blockers.append("source_video_clip_manifest not ready_for_audio_stage or contains non-production clip evidence")
        return "STAGE_06_VIDEO_CLIPS", {"video_clips_confirmed": False, "audio_confirmed": False, "assembly_confirmed": False}, blockers
    if not audio_ready:
        blockers.append("source_audio_manifest not ready_for_assembly_stage")
        return "STAGE_07_AUDIO", {"audio_confirmed": False, "assembly_confirmed": False}, blockers
    return "STAGE_08_ASSEMBLY", {"assembly_confirmed": False}, blockers


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
    concat_list = resolve_path(
        manifest_path,
        data.get("runtime_concat_list_path") or data.get("concat_list_path") or "ffmpeg_concat_list.txt",
    )
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


def build_fallback_visual_segment(
    ffmpeg_path: str,
    image_path: Path,
    output_path: Path,
    *,
    duration_sec: float,
    spec: dict[str, Any],
) -> tuple[int, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width = safe_int(spec.get("width"), DEFAULT_OUTPUT_SPEC["width"])
    height = safe_int(spec.get("height"), DEFAULT_OUTPUT_SPEC["height"])
    fps = safe_int(spec.get("fps"), DEFAULT_OUTPUT_SPEC["fps"])
    cmd = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps={fps},format=yuv420p,setsar=1",
        "-t",
        f"{max(0.5, duration_sec):.3f}",
        "-r",
        str(fps),
        "-c:v",
        str(spec.get("video_codec") or DEFAULT_OUTPUT_SPEC["video_codec"]),
        "-preset",
        "veryfast",
        "-pix_fmt",
        str(spec.get("pixel_format") or DEFAULT_OUTPUT_SPEC["pixel_format"]),
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return int(result.returncode), ((result.stderr or result.stdout or "").strip())


def prepare_runtime_concat_inputs(data: dict[str, Any], manifest_path: Path, ffmpeg_path: str) -> tuple[Path | None, str | None]:
    timeline = data.get("timeline") if isinstance(data.get("timeline"), list) else []
    temp_dir = resolve_path(manifest_path, data.get("temp_dir") or "temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    fallback_dir = temp_dir / "fallback_visual_clips"
    fallback_dir.mkdir(parents=True, exist_ok=True)
    concat_path = temp_dir / "ffmpeg_concat_runtime.txt"
    spec = output_spec_for_manifest(data)
    concat_lines: list[str] = []
    fallback_segments: list[dict[str, Any]] = []
    for item in timeline:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id") or "shot").strip() or "shot"
        clip_path = resolve_path(manifest_path, item.get("clip_path") or "")
        if clip_output_ready(clip_path):
            concat_lines.append(f"file '{str(clip_path).replace(chr(92), '/')}'")
            continue
        fallback = item.get("fallback_visual") if isinstance(item.get("fallback_visual"), dict) else {}
        preferred_image = str(fallback.get("preferred_image_path") or "").strip()
        if not preferred_image:
            return None, f"timeline clip file is non-production or too small and no fallback keyframe is available: {shot_id}"
        image_path = resolve_path(manifest_path, preferred_image)
        if not image_path.exists() or not image_path.is_file() or image_path.stat().st_size <= 0:
            return None, f"fallback keyframe missing or empty for shot {shot_id}: {image_path}"
        fallback_clip_path = fallback_dir / f"{shot_id}.mp4"
        duration = safe_float(item.get("duration_sec"), 0.0)
        return_code, error_text = build_fallback_visual_segment(
            ffmpeg_path,
            image_path,
            fallback_clip_path,
            duration_sec=duration,
            spec=spec,
        )
        if return_code != 0 or not fallback_clip_path.exists() or fallback_clip_path.stat().st_size <= 0:
            return None, error_text or f"failed to render fallback visual clip for {shot_id}"
        concat_lines.append(f"file '{str(fallback_clip_path).replace(chr(92), '/')}'")
        fallback_segments.append({
            "shot_id": shot_id,
            "source_image_path": str(image_path).replace("\\", "/"),
            "rendered_clip_path": str(fallback_clip_path).replace("\\", "/"),
            "duration_sec": round(duration, 3),
            "strategy": str(fallback.get("fallback_strategy") or "stage05_keyframe_reel"),
        })
    concat_path.write_text("\n".join(concat_lines) + ("\n" if concat_lines else ""), encoding="utf-8")
    data["runtime_concat_list_path"] = str(concat_path).replace("\\", "/")
    data["fallback_visual_segments"] = fallback_segments
    return concat_path, None


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


def write_review_markdown(data: dict[str, Any], manifest_path: Path, output_path: Path) -> None:
    review_path = manifest_path.parent / "assembly_review.md"
    evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    size = int(evidence.get("file_size_bytes") or 0)
    fallback_count = int((data.get("summary") or {}).get("fallback_visual_segment_count") or 0)
    provider = str(data.get("assembly_provider") or "").strip() or "unknown"
    notes = [str(item).strip() for item in (data.get("self_check", {}).get("notes") or []) if str(item).strip()]
    errors = data.get("errors") if isinstance(data.get("errors"), list) else []
    lines = [
        "# Stage 08 粗剪合成 Review",
        "",
        f"- 状态：`{data.get('status')}`",
        f"- 执行器：`{provider}`",
        f"- 输出文件：`{str(output_path).replace(chr(92), '/')}`",
        f"- 文件大小：`{size}` bytes",
        f"- fallback 关键帧补段数：`{fallback_count}`",
        "",
    ]
    if data.get("status") == "generated":
        lines.append("已生成可播放 rough cut，可继续进入 QA 或人工审片。")
        lines.append("")
    if notes:
        lines.append("## 状态备注")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    if errors:
        lines.append("## 最近错误")
        lines.append("")
        for item in errors[-3:]:
            if not isinstance(item, dict):
                continue
            message = str(item.get("message") or "").strip()
            if message:
                lines.append(f"- {message}")
        lines.append("")
    review_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


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
    data["summary"]["fallback_visual_segment_count"] = len(data.get("fallback_visual_segments") or [])
    if provider:
        data["assembly_provider"] = provider
    if provider and not provider_is_nonproduction(provider):
        commands = data.get("ffmpeg_commands") if isinstance(data.get("ffmpeg_commands"), list) else []
        data["ffmpeg_commands"] = [
            item for item in commands
            if not (
                isinstance(item, dict)
                and (
                    provider_is_nonproduction(item.get("provider"))
                    or str(item.get("strategy") or "").strip().lower() == "placeholder_test"
                )
            )
        ]
    production_ready = assembly_output_ready(data, out, min_bytes=MIN_PRODUCTION_VIDEO_BYTES)
    fallback_stage, fallback_flags, blockers = upstream_blocking_state(path, data)
    data.setdefault("self_check", {})
    data["self_check"].update({
        "has_timeline_from_confirmed_clips": bool(data.get("timeline")),
        "has_audio_mix_plan": mix_plan.exists(),
        "has_edit_decision_list": edit_list.exists(),
        "has_final_output_file": production_ready,
        "ready_for_qa_stage": production_ready,
        "source_video_clips_ready": fallback_stage != "STAGE_06_VIDEO_CLIPS",
        "source_audio_ready": fallback_stage not in {"STAGE_06_VIDEO_CLIPS", "STAGE_07_AUDIO"},
    })
    data["self_check"]["notes"] = [
        note for note in (data["self_check"].get("notes") or [])
        if isinstance(note, str) and not note.startswith("upstream_blocker:")
    ]
    data["self_check"]["notes"].extend([f"upstream_blocker:{item}" for item in blockers])
    if data["summary"].get("fallback_visual_segment_count"):
        data["self_check"]["notes"].append(
            f"fallback_visual_segments:{int(data['summary']['fallback_visual_segment_count'])}"
        )
    data["self_check"]["notes"] = dedupe_preserve_order(data["self_check"]["notes"])
    if production_ready:
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
        update_project_manifest_for_stage(
            path,
            current_stage=fallback_stage,
            allowed_next_stage=None,
            flags=fallback_flags,
            status="active",
        )
    data["updated_at"] = utc_now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_review_markdown(data, path, out)


def validate_source_inputs(data: dict[str, Any], manifest_path: Path) -> str | None:
    concat_list = resolve_path(
        manifest_path,
        data.get("runtime_concat_list_path") or data.get("concat_list_path") or "ffmpeg_concat_list.txt",
    )
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
            fallback = item.get("fallback_visual") if isinstance(item.get("fallback_visual"), dict) else {}
            if str(fallback.get("preferred_image_path") or "").strip():
                continue
            return f"timeline clip file missing or empty: {clip_path}"
        if not clip_output_ready(clip_path):
            fallback = item.get("fallback_visual") if isinstance(item.get("fallback_visual"), dict) else {}
            if str(fallback.get("preferred_image_path") or "").strip():
                continue
            return f"timeline clip file is non-production or too small: {clip_path} ({clip_path.stat().st_size} bytes)"
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
    runtime_concat, runtime_error = prepare_runtime_concat_inputs(data, path, ffmpeg)
    if runtime_error:
        finalize_manifest(data, path, out, provider="ffmpeg", error=runtime_error)
        print(f"ERROR: {runtime_error}")
        return 1
    if runtime_concat is None:
        finalize_manifest(data, path, out, provider="ffmpeg", error="runtime concat list unavailable")
        print("ERROR: runtime concat list unavailable")
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
