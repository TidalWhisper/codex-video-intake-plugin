#!/usr/bin/env python3
"""Validate Stage 05 keyframe image manifest.

Final mode requires every required image job to have status=succeeded and a real existing non-empty file.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_keyframe_prompts",
    "image_provider_strategy", "output_root", "keyframes_dir", "jobs", "summary", "self_check", "allowed_next_stage"
]
REQUIRED_JOB = [
    "image_id", "shot_id", "frame_role", "prompt", "negative_prompt", "aspect_ratio", "resolution",
    "provider_priority", "provider", "status", "output_path", "evidence", "errors", "notes"
]
SHOT_ID_RE = re.compile(r"^S\d{3}$")
IMAGE_ID_RE = re.compile(r"^IMG_S\d{3}_(START|END)$")


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
    # Prefer path as written relative to current working tree, but fall back to manifest folder.
    if p.exists():
        return p
    return (base_json.parent / p).resolve()


def validate(data: dict[str, Any], path: Path | None = None, mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = path or Path("keyframe_image_manifest.json")

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_05_KEYFRAME_IMAGES":
        errors.append("stage must be STAGE_05_KEYFRAME_IMAGES")
    if data.get("status") not in {"draft", "confirmed"}:
        errors.append("status must be draft or confirmed")
    for key in ["project_id", "source_brief", "source_keyframe_prompts", "output_root", "keyframes_dir"]:
        if is_blank(data.get(key)):
            errors.append(f"{key} must not be blank")
    if not isinstance(data.get("image_provider_strategy"), dict):
        errors.append("image_provider_strategy must be an object")
    if not isinstance(data.get("jobs"), list):
        errors.append("jobs must be a list")
    if not isinstance(data.get("summary"), dict):
        errors.append("summary must be an object")
    if not isinstance(data.get("self_check"), dict):
        errors.append("self_check must be an object")

    if mode == "draft":
        jobs = data.get("jobs")
        if isinstance(jobs, list) and not jobs:
            warnings.append("draft manifest has no jobs yet")
        if isinstance(jobs, list):
            pending = [j for j in jobs if isinstance(j, dict) and j.get("status") == "pending"]
            if pending:
                warnings.append(f"draft manifest has {len(pending)} pending image jobs")
        return not errors, errors, warnings

    jobs = data.get("jobs")
    seen: set[str] = set()
    by_shot: dict[str, set[str]] = {}
    generated = 0
    if isinstance(jobs, list):
        if not jobs:
            errors.append("jobs must not be empty in final mode")
        for idx, job in enumerate(jobs):
            if not isinstance(job, dict):
                errors.append(f"jobs[{idx}] must be an object")
                continue
            for key in REQUIRED_JOB:
                if key not in job:
                    errors.append(f"jobs[{idx}] missing field: {key}")
            image_id = job.get("image_id")
            if not isinstance(image_id, str) or not IMAGE_ID_RE.match(image_id):
                errors.append(f"jobs[{idx}].image_id must look like IMG_S001_START or IMG_S001_END")
            elif image_id in seen:
                errors.append(f"duplicate image_id: {image_id}")
            else:
                seen.add(image_id)
            shot_id = job.get("shot_id")
            if not isinstance(shot_id, str) or not SHOT_ID_RE.match(shot_id):
                errors.append(f"jobs[{idx}].shot_id must look like S001")
            else:
                by_shot.setdefault(shot_id, set()).add(str(job.get("frame_role")))
            if job.get("frame_role") not in {"start", "end"}:
                errors.append(f"jobs[{idx}].frame_role must be start or end")
            for key in ["prompt", "negative_prompt", "aspect_ratio", "resolution", "output_path"]:
                if is_blank(job.get(key)):
                    errors.append(f"jobs[{idx}].{key} must not be blank in final mode")
            if not isinstance(job.get("provider_priority"), list) or not job.get("provider_priority"):
                errors.append(f"jobs[{idx}].provider_priority must be a non-empty list")
            if is_blank(job.get("provider")):
                errors.append(f"jobs[{idx}].provider must not be blank in final mode")
            if job.get("status") != "succeeded":
                errors.append(f"jobs[{idx}].status must be succeeded in final mode")
            evidence = job.get("evidence")
            if not isinstance(evidence, dict):
                errors.append(f"jobs[{idx}].evidence must be an object")
                continue
            file_path = evidence.get("file_path") or job.get("output_path")
            resolved = resolve_path(manifest_path, file_path)
            if resolved is None:
                errors.append(f"jobs[{idx}].evidence.file_path must not be blank")
                continue
            if not resolved.exists():
                errors.append(f"jobs[{idx}] image file does not exist: {resolved}")
            elif not resolved.is_file():
                errors.append(f"jobs[{idx}] image path is not a file: {resolved}")
            else:
                size = resolved.stat().st_size
                if size <= 0:
                    errors.append(f"jobs[{idx}] image file is empty: {resolved}")
                else:
                    generated += 1
                if evidence.get("file_exists") is not True:
                    errors.append(f"jobs[{idx}].evidence.file_exists must be true")
                if not isinstance(evidence.get("file_size_bytes"), int) or evidence.get("file_size_bytes") <= 0:
                    errors.append(f"jobs[{idx}].evidence.file_size_bytes must be a positive integer")

    for shot_id, roles in by_shot.items():
        if roles != {"start", "end"}:
            errors.append(f"shot {shot_id} must have both start and end images")

    summary = data.get("summary")
    if isinstance(summary, dict):
        if summary.get("expected_image_count") != len(jobs or []):
            errors.append("summary.expected_image_count must equal len(jobs)")
        if summary.get("generated_image_count") != generated:
            errors.append("summary.generated_image_count must equal count of existing non-empty image files")
    self_check = data.get("self_check")
    if isinstance(self_check, dict):
        for key in ["covers_all_keyframe_prompts", "has_start_and_end_for_each_shot", "all_required_images_exist", "ready_for_video_clip_generation"]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")
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
        print("KEYFRAME IMAGE MANIFEST VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"KEYFRAME IMAGE MANIFEST VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"KEYFRAME IMAGE MANIFEST VALIDATION PASSED ({args.mode} mode): {args.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
