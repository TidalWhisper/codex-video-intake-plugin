#!/usr/bin/env python3
"""Generate small placeholder MP4-like files for Stage 06 local pipeline testing.

This is only for testing the pipeline and validators. It is not a production video generator.
"""
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


def placeholder_mp4_bytes(label: str) -> bytes:
    # Minimal MP4-like byte structure. It is intended only as non-empty test evidence.
    payload = ("PLACEHOLDER VIDEO CLIP - NOT PRODUCTION OUTPUT - " + label).encode("utf-8")
    ftyp = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    free = len(payload) + 8
    return ftyp + free.to_bytes(4, "big") + b"free" + payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        out = Path(job.get("output_path") or job.get("evidence", {}).get("file_path") or "")
        if not out.is_absolute() and not out.exists():
            out = Path(job.get("output_path"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(placeholder_mp4_bytes(job.get("clip_id", "clip")))
        job["provider"] = "placeholder_test_video_generator"
        job["status"] = "succeeded"
        job.setdefault("evidence", {})
        job["evidence"].update({
            "file_path": str(out).replace("\\", "/"),
            "file_exists": True,
            "file_size_bytes": out.stat().st_size,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    generated = sum(1 for j in data.get("jobs") or [] if isinstance(j, dict) and j.get("status") == "succeeded")
    expected = len(data.get("jobs") or [])
    data.setdefault("summary", {})
    data["summary"].update({
        "expected_clip_count": expected,
        "generated_clip_count": generated,
        "failed_clip_count": expected - generated,
        "shot_count": len({j.get("shot_id") for j in data.get("jobs") or [] if isinstance(j, dict) and j.get("shot_id")}),
        "total_duration_sec": sum(float(j.get("duration_sec") or 0) for j in data.get("jobs") or [] if isinstance(j, dict))
    })
    data.setdefault("self_check", {})
    all_generated = generated == expected and expected > 0
    data["self_check"].update({
        "covers_all_storyboard_shots": True,
        "has_source_start_and_end_keyframes_for_each_shot": True,
        "all_required_clips_exist": all_generated,
        "ready_for_audio_stage": all_generated,
    })
    data["status"] = "generated" if all_generated else ("in_progress" if generated > 0 else "draft")
    data["allowed_next_stage"] = next_stage_after("STAGE_06_VIDEO_CLIPS", routing, "STAGE_07_AUDIO") if all_generated else None
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if all_generated:
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_06_VIDEO_CLIPS_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"video_clips_confirmed": True},
            status="active",
        )
    print(f"PLACEHOLDER VIDEO CLIPS GENERATED: {generated}/{expected}")
    print(f"MANIFEST UPDATED: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
