#!/usr/bin/env python3
"""Generate simple placeholder PNG images for Stage 05 local pipeline testing.

This is only for testing the pipeline and validators. It is not a production image generator.
"""
from __future__ import annotations
import argparse
import json
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "providers"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402
from stage05_image_utils import update_manifest_state  # noqa: E402


def png_bytes(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def color_for(text: str) -> tuple[int, int, int]:
    h = abs(hash(text))
    return (80 + h % 120, 80 + (h // 17) % 120, 80 + (h // 41) % 120)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--width", type=int, default=540)
    parser.add_argument("--height", type=int, default=960)
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        out = Path(job.get("output_path") or job.get("evidence", {}).get("file_path") or "")
        if not out.is_absolute() and not out.exists():
            # If output path was saved as project-relative or CWD-relative, preserve as given when possible.
            out = Path(job.get("output_path"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(png_bytes(args.width, args.height, color_for(job.get("image_id", "image"))))
        job["provider"] = "placeholder_test_generator"
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
        "expected_image_count": expected,
        "generated_image_count": generated,
        "failed_image_count": expected - generated,
        "shot_count": len({j.get("shot_id") for j in data.get("jobs") or [] if isinstance(j, dict) and j.get("shot_id")})
    })
    update_manifest_state(data, path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if data.get("self_check", {}).get("ready_for_video_clip_generation") is True:
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"keyframe_images_confirmed": True},
            status="active",
        )
    print(f"PLACEHOLDER KEYFRAME IMAGES GENERATED: {generated}/{expected}")
    print(f"MANIFEST UPDATED: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
