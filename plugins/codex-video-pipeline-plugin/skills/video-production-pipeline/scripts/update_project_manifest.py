#!/usr/bin/env python3
"""Patch a video project manifest with stage flags.

Usage:
  python update_project_manifest.py <project_dir> --stage STAGE_01_SCRIPT_CONFIRMED --script-confirmed true --allowed-next-stage STAGE_02_STORYBOARD
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_core.project_state import load_json_file_if_exists, sync_project_manifest_truth, utc_now, write_json_file  # noqa: E402


def load_manifest(path: Path) -> dict:
    return load_json_file_if_exists(path) or {}


def parse_bool(value: str | None):
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "y", "确认", "是"}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("project_dir")
    p.add_argument("--stage", required=True)
    p.add_argument("--allowed-next-stage", default=None)
    p.add_argument("--brief-locked", default=None)
    p.add_argument("--script-confirmed", default=None)
    p.add_argument("--storyboard-confirmed", default=None)
    p.add_argument("--character-bible-confirmed", default=None)
    p.add_argument("--keyframe-prompts-confirmed", default=None)
    p.add_argument("--keyframe-images-confirmed", default=None)
    p.add_argument("--video-clips-confirmed", default=None)
    p.add_argument("--audio-confirmed", default=None)
    p.add_argument("--assembly-confirmed", default=None)
    p.add_argument("--qa-confirmed", default=None)
    p.add_argument("--delivery-complete", default=None)
    args = p.parse_args()

    project_dir = Path(args.project_dir)
    manifest_path = project_dir / "project_manifest.json"
    data = load_manifest(manifest_path)
    data.setdefault("project_id", project_dir.name)
    data.setdefault("project_dir", str(project_dir).replace("\\", "/"))
    data["current_stage"] = args.stage
    data["updated_at"] = utc_now()
    data["allowed_next_stage"] = args.allowed_next_stage

    for key, raw in [
        ("brief_locked", args.brief_locked),
        ("script_confirmed", args.script_confirmed),
        ("storyboard_confirmed", args.storyboard_confirmed),
        ("character_bible_confirmed", args.character_bible_confirmed),
        ("keyframe_prompts_confirmed", args.keyframe_prompts_confirmed),
        ("keyframe_images_confirmed", args.keyframe_images_confirmed),
        ("video_clips_confirmed", args.video_clips_confirmed),
        ("audio_confirmed", args.audio_confirmed),
        ("assembly_confirmed", args.assembly_confirmed),
        ("qa_confirmed", args.qa_confirmed),
        ("delivery_complete", args.delivery_complete),
    ]:
        parsed = parse_bool(raw)
        if parsed is not None:
            data[key] = parsed

    write_json_file(manifest_path, data)
    sync_project_manifest_truth(manifest_path)
    print(f"MANIFEST UPDATED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
