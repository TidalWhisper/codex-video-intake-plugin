#!/usr/bin/env python3
"""Sync Stage 06 video clip manifest evidence from files on disk."""
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


def resolve_from_source(base_json: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    p = Path(str(raw))
    if p.is_absolute():
        return p
    if p.exists():
        return p
    return (base_json.parent / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--provider", default=None, help="Optional provider to set for existing clips, e.g. comfyui_ltx_i2v or manual")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    generated = 0
    failed = 0
    source_ok = 0
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        # Source keyframe evidence
        keyframes = job.get("source_keyframes") if isinstance(job.get("source_keyframes"), dict) else {}
        start = resolve_from_source(path, keyframes.get("start"))
        end = resolve_from_source(path, keyframes.get("end"))
        if start and end and start.exists() and end.exists() and start.stat().st_size > 0 and end.stat().st_size > 0:
            source_ok += 1
        # Clip evidence
        raw = job.get("output_path") or job.get("evidence", {}).get("file_path")
        if not raw:
            continue
        clip = resolve(path, str(raw))
        ev = job.setdefault("evidence", {})
        ev["file_path"] = str(clip).replace("\\", "/")
        if clip.exists() and clip.is_file() and clip.stat().st_size > 0:
            ev["file_exists"] = True
            ev["file_size_bytes"] = clip.stat().st_size
            ev["created_at"] = datetime.fromtimestamp(clip.stat().st_mtime, timezone.utc).isoformat()
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
    jobs = data.get("jobs") or []
    summary = data.setdefault("summary", {})
    summary["expected_clip_count"] = len(jobs)
    summary["generated_clip_count"] = generated
    summary["failed_clip_count"] = failed
    summary["shot_count"] = len({j.get("shot_id") for j in jobs if isinstance(j, dict) and j.get("shot_id")})
    summary["total_duration_sec"] = sum(float(j.get("duration_sec") or 0) for j in jobs if isinstance(j, dict))
    self_check = data.setdefault("self_check", {})
    all_clips = generated == len(jobs) and generated > 0
    self_check["all_required_clips_exist"] = all_clips
    self_check["ready_for_audio_stage"] = all_clips
    self_check["has_source_start_and_end_keyframes_for_each_shot"] = source_ok == len(jobs) and bool(jobs)
    self_check.setdefault("covers_all_storyboard_shots", bool(jobs))
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if all_clips:
        data["allowed_next_stage"] = "STAGE_07_AUDIO"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"VIDEO CLIP MANIFEST SYNCED: {path}")
    print(f"GENERATED_CLIPS: {generated}")
    print(f"FAILED_OR_MISSING_CLIPS: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
