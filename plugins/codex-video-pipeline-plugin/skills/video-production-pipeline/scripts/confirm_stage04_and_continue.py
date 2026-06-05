#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "video-keyframe-prompts" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "video-keyframe-images" / "scripts"))

from pipeline_core.project_state import load_json_file, write_json_file  # noqa: E402
import validate_keyframe_prompts  # noqa: E402
import new_keyframe_image_jobs  # noqa: E402


def _load(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python confirm_stage04_and_continue.py <project_dir>", file=sys.stderr)
        return 2

    project_dir = Path(args[0]).resolve()
    manifest_path = project_dir / "project_manifest.json"
    brief_path = project_dir / "00_intake" / "project_brief.locked.json"
    keyframe_path = project_dir / "04_keyframes" / "keyframe_prompts.json"
    stage05_manifest_path = project_dir / "05_images" / "keyframe_image_manifest.json"

    if not manifest_path.exists():
        print(f"ERROR: project manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    if not brief_path.exists():
        print(f"ERROR: locked brief not found: {brief_path}", file=sys.stderr)
        return 1
    if not keyframe_path.exists():
        print(f"ERROR: Stage 04 keyframe prompts not found: {keyframe_path}", file=sys.stderr)
        return 1

    keyframe_data = _load(keyframe_path)
    ok, errors, _warnings = validate_keyframe_prompts.validate(keyframe_data, mode="final")
    if not ok:
        print("ERROR: Stage 04 keyframe prompts failed final validation before confirmation:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    keyframe_data["status"] = "confirmed"
    keyframe_data["allowed_next_stage"] = "STAGE_05_KEYFRAME_IMAGES"
    write_json_file(keyframe_path, keyframe_data)

    manifest_data = _load(manifest_path)
    manifest_data["current_stage"] = "STAGE_04_KEYFRAME_PROMPTS_CONFIRMED"
    manifest_data["brief_locked"] = True
    manifest_data["script_confirmed"] = True
    manifest_data["storyboard_confirmed"] = True
    manifest_data["character_bible_confirmed"] = True
    manifest_data["keyframe_prompts_confirmed"] = True
    manifest_data["allowed_next_stage"] = "STAGE_05_KEYFRAME_IMAGES"
    write_json_file(manifest_path, manifest_data)

    print(f"STAGE04_CONFIRMED: {project_dir}")
    return new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(brief_path),
        str(keyframe_path),
        str(stage05_manifest_path),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
