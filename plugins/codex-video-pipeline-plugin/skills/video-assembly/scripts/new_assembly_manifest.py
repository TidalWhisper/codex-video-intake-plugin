#!/usr/bin/env python3
"""Create Stage 08 rough-cut assembly manifest from confirmed clips and audio.

Usage:
  python new_assembly_manifest.py <locked_brief.json> <storyboard.json> <video_clip_manifest.json> <audio_manifest.json> <assembly_manifest.json>
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.quality_contracts import build_quality_contract, build_stage_quality_targets  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage, stage_meets_requested_output  # noqa: E402

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


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rel_or_abs(path: Path) -> str:
    return str(path).replace("\\", "/")


def resolve_path(base_json: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    p = Path(str(raw))
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


def sec_to_srt_time(sec: float) -> str:
    sec = max(0.0, float(sec or 0))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def default_output_video_spec() -> dict:
    return {
        "width": 1080,
        "height": 1920,
        "fps": 24,
        "video_codec": "libx264",
        "pixel_format": "yuv420p",
        "audio_codec": "aac",
        "audio_sample_rate": 48000,
    }


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 6:
        print("Usage: python new_assembly_manifest.py <locked_brief.json> <storyboard.json> <video_clip_manifest.json> <audio_manifest.json> <assembly_manifest.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    storyboard_path = Path(argv[2])
    clip_manifest_path = Path(argv[3])
    audio_manifest_path = Path(argv[4])
    out_path = Path(argv[5])

    brief = load_json(brief_path)
    storyboard = load_json(storyboard_path)
    clip_manifest = load_json(clip_manifest_path)
    audio_manifest = load_json(audio_manifest_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_08", compiled):
        print("ERROR: requested output scope does not allow Stage 08. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if clip_manifest.get("stage") != "STAGE_06_VIDEO_CLIPS" or not (clip_manifest.get("self_check") or {}).get("ready_for_audio_stage"):
        print("ERROR: video_clip_manifest must be final-ready before Stage 08", file=sys.stderr)
        return 1
    if audio_manifest.get("stage") != "STAGE_07_AUDIO" or not (audio_manifest.get("self_check") or {}).get("ready_for_assembly_stage"):
        print("ERROR: audio_manifest must be final-ready before Stage 08", file=sys.stderr)
        return 1

    project_id = brief.get("project_id") or clip_manifest.get("project_id") or audio_manifest.get("project_id") or out_path.parents[1].name
    routing = routing_from_brief(brief)
    quality_contract = build_quality_contract(brief, compiled)
    quality_targets = build_stage_quality_targets("STAGE_08", quality_contract)
    assembly_dir = out_path.parent
    rough_cut_dir = assembly_dir / "rough_cut"
    temp_dir = assembly_dir / "temp"
    rough_cut_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    clip_by_shot = {j.get("shot_id"): j for j in clip_manifest.get("jobs") or [] if isinstance(j, dict)}
    current = 0.0
    timeline = []
    concat_lines = []
    edl_events = []
    subtitle_lines = []
    srt_idx = 1

    shots = storyboard.get("shots") or []
    if not shots:
        # Fallback to clip order if storyboard omitted shots.
        shots = [{"shot_id": j.get("shot_id"), "duration_sec": j.get("duration_sec"), "voiceover": "", "dialogue": ""} for j in clip_manifest.get("jobs") or []]

    for shot in shots:
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id")
        clip = clip_by_shot.get(shot_id)
        if not clip:
            continue
        duration = float(clip.get("duration_sec") or shot.get("duration_sec") or 0)
        clip_path = resolve_path(
            clip_manifest_path,
            clip.get("output_path") or (clip.get("evidence") or {}).get("file_path"),
        )
        if clip_path is None:
            continue
        timeline.append({
            "shot_id": shot_id,
            "source_clip_id": clip.get("clip_id"),
            "clip_path": rel_or_abs(clip_path),
            "start_sec": round(current, 3),
            "duration_sec": duration,
            "transition_in": shot.get("transition_in") or "cut",
            "transition_out": shot.get("transition_to_next") or clip.get("transition_out_prompt") or "cut",
            "notes": shot.get("composition") or shot.get("action") or ""
        })
        concat_lines.append(f"file '{rel_or_abs(clip_path)}'")
        edl_events.append({
            "event_id": f"EDL_{len(edl_events)+1:03d}",
            "shot_id": shot_id,
            "clip_path": rel_or_abs(clip_path),
            "timeline_in_sec": round(current, 3),
            "timeline_out_sec": round(current + duration, 3),
            "duration_sec": duration,
            "transition": shot.get("transition_to_next") or "cut"
        })
        caption = (shot.get("voiceover") or shot.get("dialogue") or "").strip()
        if caption:
            subtitle_lines.append(str(srt_idx))
            subtitle_lines.append(f"{sec_to_srt_time(current)} --> {sec_to_srt_time(current + duration)}")
            subtitle_lines.append(caption)
            subtitle_lines.append("")
            srt_idx += 1
        current += duration

    audio_tracks = []
    for job in audio_manifest.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        audio_path = resolve_path(
            audio_manifest_path,
            job.get("output_path") or (job.get("evidence") or {}).get("file_path"),
        )
        if audio_path is None:
            continue
        audio_tracks.append({
            "audio_id": f"ASM_{job.get('audio_id')}",
            "audio_type": job.get("audio_type"),
            "source_audio_id": job.get("audio_id"),
            "audio_path": rel_or_abs(audio_path),
            "start_sec": 0.0 if job.get("audio_type") == "music" else None,
            "duration_sec": float(job.get("duration_sec") or 0),
            "volume": -18 if job.get("audio_type") == "music" else -6,
            "notes": job.get("text") or job.get("music_prompt") or ""
        })

    concat_list = assembly_dir / "ffmpeg_concat_list.txt"
    edl_path = assembly_dir / "edit_decision_list.json"
    mix_path = assembly_dir / "audio_mix_plan.json"
    subtitle_path = assembly_dir / "subtitles.srt"
    plan_path = assembly_dir / "assembly_plan.md"
    review_path = assembly_dir / "assembly_review.md"
    final_out = rough_cut_dir / "rough_cut.mp4"

    concat_list.write_text("\n".join(concat_lines) + ("\n" if concat_lines else ""), encoding="utf-8")
    write_json(edl_path, {"project_id": project_id, "events": edl_events})
    output_spec = default_output_video_spec()
    write_json(mix_path, {
        "project_id": project_id,
        "target_video_spec": output_spec,
        "target_audio_sample_rate": output_spec["audio_sample_rate"],
        "mix_strategy": "voice/dialogue prioritized over background music",
        "audio_tracks": audio_tracks,
        "notes": "Voice/dialogue/music mix plan for FFmpeg or manual editor.",
    })
    subtitle_path.write_text("\n".join(subtitle_lines), encoding="utf-8")
    plan_path.write_text(f"# Stage 08 粗剪合成计划\n\n- 项目：{project_id}\n- 镜头数量：{len(timeline)}\n- 预计时长：{round(current, 2)} 秒\n- 输出：{rel_or_abs(final_out)}\n\n优先使用 FFmpeg 合成；如 FFmpeg 不可用，记录错误并等待人工修复。\n", encoding="utf-8")
    review_path.write_text("# Stage 08 粗剪合成 Review\n\n待生成 rough_cut.mp4 后确认。\n", encoding="utf-8")

    manifest = {
        "schema_version": "0.9.0",
        "stage": "STAGE_08_ASSEMBLY",
        "status": "draft",
        "project_id": project_id,
        "source_brief": rel_or_abs(brief_path),
        "source_storyboard": rel_or_abs(storyboard_path),
        "source_video_clip_manifest": rel_or_abs(clip_manifest_path),
        "source_audio_manifest": rel_or_abs(audio_manifest_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "assembly_provider_strategy": {
            "primary": "ffmpeg",
            "fallback": ["manual"],
            "execution_mode": "provider_or_manual"
        },
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing,
        "output_root": rel_or_abs(assembly_dir),
        "rough_cut_dir": rel_or_abs(rough_cut_dir),
        "temp_dir": rel_or_abs(temp_dir),
        "concat_list_path": rel_or_abs(concat_list),
        "edit_decision_list_path": rel_or_abs(edl_path),
        "audio_mix_plan_path": rel_or_abs(mix_path),
        "subtitle_path": rel_or_abs(subtitle_path),
        "final_output_path": rel_or_abs(final_out),
        "timeline": timeline,
        "audio_tracks": audio_tracks,
        "subtitle_tracks": [{"subtitle_id": "SUB_MAIN", "path": rel_or_abs(subtitle_path), "format": "srt", "language": "zh-CN", "burn_in": False}],
        "ffmpeg_commands": [],
        "evidence": {"file_path": rel_or_abs(final_out), "file_exists": final_out.exists(), "file_size_bytes": final_out.stat().st_size if final_out.exists() else 0, "created_at": None},
        "summary": {
            "timeline_clip_count": len(timeline),
            "audio_track_count": len(audio_tracks),
            "rough_cut_duration_sec": round(current, 3),
            "output_video_spec": output_spec,
        },
        "quality_signals": {
            "intent_route_matches_strategy": routing.get("legacy_mode") or requested_output_allows_stage("STAGE_08", compiled),
            "timeline_matches_storyboard_order": len(timeline) == len([shot for shot in shots if isinstance(shot, dict) and clip_by_shot.get(shot.get("shot_id"))]),
            "audio_tracks_match_strategy": (not audio_tracks) or any(track.get("audio_type") == "music" for track in audio_tracks) or any(track.get("audio_type") in {"voiceover", "dialogue"} for track in audio_tracks),
            "quality_targets_defined": bool(quality_targets),
        },
        "self_check": {
            "has_timeline_from_confirmed_clips": bool(timeline),
            "has_audio_mix_plan": mix_path.exists(),
            "has_edit_decision_list": edl_path.exists(),
            "has_final_output_file": final_out.exists() and final_out.stat().st_size > 0 if final_out.exists() else False,
            "ready_for_qa_stage": False,
            "notes": []
        },
        "errors": [],
        "allowed_next_stage": None
    }
    write_json(out_path, manifest)
    print(f"ASSEMBLY MANIFEST CREATED: {out_path}")
    print(f"ROUGH CUT TARGET: {final_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
