#!/usr/bin/env python3
"""Create a Stage 02 storyboard JSON template from a locked brief and script.

This script only scaffolds the file. Codex must fill shot-level content.
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
    if len(argv) != 4:
        print("Usage: python new_storyboard_template.py <locked_brief.json> <script.json> <storyboard.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    out_path = Path(argv[3])
    brief = load_json(brief_path)
    script = load_json(script_path)
    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        print("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION", file=sys.stderr)
        return 1
    project_id = brief.get("project_id") or script.get("project_id") or brief_path.parents[1].name
    normalized = brief.get("normalized", {})
    template = {
        "schema_version": "0.3.0",
        "stage": "STAGE_02_STORYBOARD_GENERATION",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_script": str(script_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_duration_sec": normalized.get("target_duration_sec") or script.get("duration_plan", {}).get("target_duration_sec"),
        "shot_count": 0,
        "shots": [],
        "self_check": {
            "matches_locked_brief": None,
            "matches_script": None,
            "duration_fits": None,
            "ready_for_character_stage": None,
            "notes": []
        },
        "allowed_next_stage": None
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STORYBOARD TEMPLATE CREATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
