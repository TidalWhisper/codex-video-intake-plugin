#!/usr/bin/env python3
"""Sync Stage 05 manifest evidence from files on disk."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402


def resolve(base: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [Path.cwd(), base.parent, *base.parents]:
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
    return (base.parent / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--provider", default=None, help="Optional provider to set for existing images, e.g. openai_image or comfyui_txt2img")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
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
    data["status"] = "generated" if all_exist else ("in_progress" if generated > 0 else "draft")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if all_exist:
        data["allowed_next_stage"] = next_stage_after("STAGE_05_KEYFRAME_IMAGES", routing, "STAGE_06_VIDEO_CLIPS")
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"keyframe_images_confirmed": True},
            status="active",
        )
    else:
        data["allowed_next_stage"] = None
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"KEYFRAME IMAGE MANIFEST SYNCED: {path}")
    print(f"GENERATED_IMAGES: {generated}")
    print(f"FAILED_OR_MISSING_IMAGES: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
