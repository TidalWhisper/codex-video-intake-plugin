#!/usr/bin/env python3
"""Create a Stage 01 script JSON template from a locked project brief.

This script only scaffolds the file. Codex must fill creative content.
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
    if len(argv) != 3:
        print("Usage: python new_script_template.py <locked_brief.json> <script.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    out_path = Path(argv[2])
    brief = load_json(brief_path)
    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    normalized = brief.get("normalized", {})
    project_id = brief.get("project_id") or brief_path.parents[1].name
    template = {
        "schema_version": "0.3.0",
        "stage": "STAGE_01_SCRIPT_GENERATION",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "",
        "logline": normalized.get("idea", ""),
        "theme": "",
        "characters": [],
        "settings": [],
        "duration_plan": {
            "target_duration_sec": normalized.get("target_duration_sec"),
            "target_duration_label": normalized.get("target_duration_label"),
            "beats": []
        },
        "script": {
            "format": "screenplay",
            "voice_mode": normalized.get("voice_mode"),
            "music_mode": normalized.get("music_mode"),
            "sections": []
        },
        "self_check": {
            "matches_locked_brief": None,
            "duration_fits": None,
            "genre_style_fits": None,
            "ready_for_storyboard": None,
            "notes": []
        },
        "allowed_next_stage": None
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"SCRIPT TEMPLATE CREATED: {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
