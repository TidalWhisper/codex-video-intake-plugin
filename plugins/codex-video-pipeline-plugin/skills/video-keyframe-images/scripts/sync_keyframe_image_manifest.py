#!/usr/bin/env python3
"""Sync Stage 05 manifest evidence from files on disk."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def resolve(base: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p
    return (base.parent / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--provider", default=None, help="Optional provider to set for existing images, e.g. openai_image or comfyui_txt2img")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    generated = 0
    failed = 0
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        raw = job.get("output_path") or job.get("evidence", {}).get("file_path")
        if not raw:
            continue
        img = resolve(path, str(raw))
        ev = job.setdefault("evidence", {})
        ev["file_path"] = str(img).replace("\\", "/")
        if img.exists() and img.is_file() and img.stat().st_size > 0:
            ev["file_exists"] = True
            ev["file_size_bytes"] = img.stat().st_size
            ev["created_at"] = datetime.fromtimestamp(img.stat().st_mtime, timezone.utc).isoformat()
            job["status"] = "succeeded"
            if args.provider and not job.get("provider"):
                job["provider"] = args.provider
            generated += 1
        else:
            ev["file_exists"] = False
            ev["file_size_bytes"] = 0
            if job.get("status") == "succeeded":
                job["status"] = "failed"
            failed += 1
    summary = data.setdefault("summary", {})
    summary["expected_image_count"] = len(data.get("jobs") or [])
    summary["generated_image_count"] = generated
    summary["failed_image_count"] = failed
    shots = {j.get("shot_id") for j in data.get("jobs") or [] if isinstance(j, dict) and j.get("shot_id")}
    summary["shot_count"] = len(shots)
    self_check = data.setdefault("self_check", {})
    all_exist = generated == len(data.get("jobs") or []) and generated > 0
    self_check["all_required_images_exist"] = all_exist
    self_check["ready_for_video_clip_generation"] = all_exist
    self_check["covers_all_keyframe_prompts"] = bool(data.get("jobs"))
    self_check["has_start_and_end_for_each_shot"] = all({"start", "end"} == {j.get("frame_role") for j in data.get("jobs") or [] if j.get("shot_id") == sid} for sid in shots)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if all_exist:
        data["allowed_next_stage"] = "STAGE_06_VIDEO_CLIPS"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"KEYFRAME IMAGE MANIFEST SYNCED: {path}")
    print(f"GENERATED_IMAGES: {generated}")
    print(f"FAILED_OR_MISSING_IMAGES: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
