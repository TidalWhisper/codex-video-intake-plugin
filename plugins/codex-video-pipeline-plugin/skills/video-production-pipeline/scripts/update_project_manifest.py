#!/usr/bin/env python3
"""Patch a video project manifest with stage flags.

Usage:
  python update_project_manifest.py <project_dir> --stage STAGE_01_SCRIPT_CONFIRMED --script-confirmed true --allowed-next-stage STAGE_02_STORYBOARD
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load_manifest(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


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
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
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

    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"MANIFEST UPDATED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
