#!/usr/bin/env python3
"""Validate Stage 06 video clip manifest.

Final mode requires every clip job to have status=succeeded and a real existing non-empty clip file.
It also verifies source start/end keyframe files exist and are non-empty.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_storyboard", "source_keyframe_prompts",
    "source_keyframe_image_manifest", "video_provider_strategy", "output_root", "clips_dir", "jobs", "summary", "self_check", "allowed_next_stage"
]
REQUIRED_JOB = [
    "clip_id", "shot_id", "source_storyboard_ref", "source_prompt_ref", "source_keyframes", "motion_prompt", "negative_prompt",
    "duration_sec", "fps", "aspect_ratio", "resolution", "provider_priority", "provider", "status", "output_path", "evidence", "errors", "notes"
]
SHOT_ID_RE = re.compile(r"^S\d{3}$")
CLIP_ID_RE = re.compile(r"^CLIP_S\d{3}$")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def resolve_path(base_json: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [Path.cwd(), base_json.parent, *base_json.parents]:
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


def validate(data: dict[str, Any], path: Path | None = None, mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = path or Path("video_clip_manifest.json")

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_06_VIDEO_CLIPS":
        errors.append("stage must be STAGE_06_VIDEO_CLIPS")
    if data.get("status") not in {"draft", "in_progress", "generated", "confirmed", "blocked"}:
        errors.append("status must be draft, in_progress, generated, confirmed, or blocked")
    if is_blank(data.get("project_id")):
        errors.append("project_id must not be blank")
    if not isinstance(data.get("jobs"), list):
        errors.append("jobs must be a list")
        jobs: list[Any] = []
    else:
        jobs = data.get("jobs") or []
    if mode == "final" and not jobs:
        errors.append("jobs must not be empty in final mode")

    generated = 0
    by_shot: set[str] = set()
    source_ok_count = 0
    for idx, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"jobs[{idx}] must be an object")
            continue
        for key in REQUIRED_JOB:
            if key not in job:
                errors.append(f"jobs[{idx}] missing key: {key}")
        shot_id = job.get("shot_id")
        clip_id = job.get("clip_id")
        if not isinstance(shot_id, str) or not SHOT_ID_RE.match(shot_id):
            errors.append(f"jobs[{idx}].shot_id must match S###")
        else:
            by_shot.add(shot_id)
        if not isinstance(clip_id, str) or not CLIP_ID_RE.match(clip_id):
            errors.append(f"jobs[{idx}].clip_id must match CLIP_S###")
        if isinstance(shot_id, str) and isinstance(clip_id, str) and clip_id != f"CLIP_{shot_id}":
            errors.append(f"jobs[{idx}].clip_id must equal CLIP_<shot_id>")
        if mode == "final" and is_blank(job.get("motion_prompt")):
            errors.append(f"jobs[{idx}].motion_prompt must not be blank in final mode")
        duration = job.get("duration_sec")
        try:
            duration_float = float(duration)
        except Exception:
            errors.append(f"jobs[{idx}].duration_sec must be numeric")
            duration_float = 0
        if mode == "final" and not (1 <= duration_float <= 20):
            errors.append(f"jobs[{idx}].duration_sec must be between 1 and 20 in final mode")
        fps = job.get("fps")
        if not isinstance(fps, int) or fps <= 0:
            errors.append(f"jobs[{idx}].fps must be a positive integer")
        if not isinstance(job.get("provider_priority"), list) or not job.get("provider_priority"):
            errors.append(f"jobs[{idx}].provider_priority must be a non-empty list")
        if mode == "final":
            if is_blank(job.get("provider")):
                errors.append(f"jobs[{idx}].provider must not be blank in final mode")
            if job.get("status") != "succeeded":
                errors.append(f"jobs[{idx}].status must be succeeded in final mode")
            keyframes = job.get("source_keyframes")
            if not isinstance(keyframes, dict):
                errors.append(f"jobs[{idx}].source_keyframes must be an object")
            else:
                src_start = resolve_path(manifest_path, keyframes.get("start"))
                src_end = resolve_path(manifest_path, keyframes.get("end"))
                if src_start is None or not src_start.exists() or not src_start.is_file() or src_start.stat().st_size <= 0:
                    errors.append(f"jobs[{idx}] source start keyframe missing or empty: {src_start}")
                if src_end is None or not src_end.exists() or not src_end.is_file() or src_end.stat().st_size <= 0:
                    errors.append(f"jobs[{idx}] source end keyframe missing or empty: {src_end}")
                if src_start and src_end and src_start.exists() and src_end.exists() and src_start.stat().st_size > 0 and src_end.stat().st_size > 0:
                    source_ok_count += 1
            evidence = job.get("evidence")
            if not isinstance(evidence, dict):
                errors.append(f"jobs[{idx}].evidence must be an object")
                continue
            file_path = evidence.get("file_path") or job.get("output_path")
            resolved = resolve_path(manifest_path, file_path)
            if resolved is None:
                errors.append(f"jobs[{idx}].evidence.file_path must not be blank")
                continue
            if resolved.suffix.lower() not in {".mp4", ".mov", ".webm", ".mkv"}:
                errors.append(f"jobs[{idx}] clip file extension must be mp4/mov/webm/mkv: {resolved}")
            if not resolved.exists():
                errors.append(f"jobs[{idx}] clip file does not exist: {resolved}")
            elif not resolved.is_file():
                errors.append(f"jobs[{idx}] clip path is not a file: {resolved}")
            else:
                size = resolved.stat().st_size
                if size <= 0:
                    errors.append(f"jobs[{idx}] clip file is empty: {resolved}")
                else:
                    generated += 1
                if evidence.get("file_exists") is not True:
                    errors.append(f"jobs[{idx}].evidence.file_exists must be true")
                if not isinstance(evidence.get("file_size_bytes"), int) or evidence.get("file_size_bytes") <= 0:
                    errors.append(f"jobs[{idx}].evidence.file_size_bytes must be a positive integer")

    summary = data.get("summary")
    if isinstance(summary, dict):
        if summary.get("expected_clip_count") != len(jobs):
            errors.append("summary.expected_clip_count must equal len(jobs)")
        if summary.get("generated_clip_count") != generated:
            errors.append("summary.generated_clip_count must equal count of existing non-empty clip files")
    self_check = data.get("self_check")
    if isinstance(self_check, dict) and mode == "final":
        for key in ["covers_all_storyboard_shots", "has_source_start_and_end_keyframes_for_each_shot", "all_required_clips_exist", "ready_for_audio_stage"]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")
    quality_signals = data.get("quality_signals")
    if mode == "final":
        if not isinstance(quality_signals, dict):
            errors.append("quality_signals must be an object in final mode")
        else:
            for key in ["intent_route_matches_strategy", "continuity_sources_present", "performance_prompts_present", "quality_targets_defined"]:
                if quality_signals.get(key) is not True:
                    errors.append(f"quality_signals.{key} must be true in final mode")
            if quality_signals.get("workflow_capability_safe_for_all_jobs") is not True:
                errors.append("quality_signals.workflow_capability_safe_for_all_jobs must be true in final mode")
    if mode == "draft" and jobs:
        warnings.append("draft video clip manifest contains planned jobs; final mode still requires generated clip files")
    return not errors, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--mode", choices=["draft", "final"], default="final")
    args = parser.parse_args(argv)
    path = Path(args.manifest_json)
    data = load_json(path)
    ok, errors, warnings = validate(data, path, args.mode)
    if warnings:
        print("VIDEO CLIP MANIFEST VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"VIDEO CLIP MANIFEST VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"VIDEO CLIP MANIFEST VALIDATION PASSED ({args.mode} mode): {args.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
