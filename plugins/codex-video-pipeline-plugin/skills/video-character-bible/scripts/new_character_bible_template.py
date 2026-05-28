#!/usr/bin/env python3
"""Create a Stage 03 character-bible JSON template from a locked brief, script, and storyboard.

This script only scaffolds the file. Codex must fill character-level content.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print("Usage: python new_character_bible_template.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    out_path = Path(argv[4])
    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        print("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION", file=sys.stderr)
        return 1
    if storyboard.get("stage") != "STAGE_02_STORYBOARD_GENERATION":
        print("ERROR: storyboard.stage must be STAGE_02_STORYBOARD_GENERATION", file=sys.stderr)
        return 1
    project_id = brief.get("project_id") or script.get("project_id") or storyboard.get("project_id") or brief_path.parents[1].name
    normalized = brief.get("normalized", {})
    voice_raw = (normalized.get("voice") or {}).get("raw", "")
    voice_needed = not ("不需要" in voice_raw)
    fixed_chars_raw = (normalized.get("fixed_characters") or {}).get("raw", "")
    ref_required = True if ("有固定主角" in fixed_chars_raw or "自动判断" in fixed_chars_raw or "不确定" in fixed_chars_raw) else False
    template = {
        "schema_version": "0.4.0",
        "stage": "STAGE_03_CHARACTER_BIBLE",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_script": str(script_path).replace("\\", "/"),
        "source_storyboard": str(storyboard_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "characters": [],
        "reference_image_required": ref_required,
        "default_voice_needed": voice_needed,
        "self_check": {
            "matches_locked_brief": None,
            "matches_script": None,
            "matches_storyboard": None,
            "ready_for_keyframe_stage": None,
            "notes": []
        },
        "allowed_next_stage": None
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"CHARACTER BIBLE TEMPLATE CREATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
