#!/usr/bin/env python3
"""LEGACY/DEBUG ONLY: create a blank Stage 00 project brief draft template.

Usage:
  python new_project_brief_template.py .video_project/intake/project_brief.draft.json

This script is no longer part of the official Stage 00 codex-first path.
Normal intake must go through:
  python skills/video-production-pipeline/scripts/run_stage00_controller.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def infer_project_context(output: Path) -> tuple[str, str]:
    if output.parent.name in {"00_intake", "intake"}:
        project_dir = output.parent.parent.resolve()
    else:
        project_dir = output.parent.resolve()
    project_id = project_dir.name or "video_intake_draft"
    return project_id, str(project_dir).replace("\\", "/")


def main(argv: list[str]) -> int:
    output = Path(argv[1]) if len(argv) > 1 else Path(".video_project/intake/project_brief.draft.json")
    print(
        "LEGACY_DEBUG_ONLY: new_project_brief_template.py is not the official Stage 00 entry. "
        "Use skills/video-production-pipeline/scripts/run_stage00_controller.py for normal intake flow.",
        file=sys.stderr,
    )
    now = datetime.now(timezone.utc).isoformat()
    project_id, project_dir = infer_project_context(output)
    data = {
        "schema_version": "0.3.0",
        "project_id": project_id,
        "project_dir": project_dir,
        "stage": "STAGE_00_INTAKE",
        "status": "draft",
        "confirmed_by_user": False,
        "required_fields_complete": False,
        "missing_required_fields": [
            "idea",
            "target_duration",
            "genre",
            "style",
            "visual_spec",
            "characters",
            "voice",
            "music",
            "final_output",
        ],
        "source": "Legacy/debug blank template created outside the official Stage 00 codex-first flow.",
        "user_answers": {},
        "normalized": {
            "idea": "",
            "target_duration_sec": "",
            "target_duration_label": "",
            "genre": "",
            "style": "",
            "aspect_ratio": "",
            "aspect_ratio_label": "",
            "resolution": "",
            "resolution_label": "",
            "characters_mode": "",
            "characters_required": "",
            "voice_mode": "",
            "voice_required": "",
            "music_mode": "",
            "music_profile": "",
            "music_required": "",
            "final_output": "",
        },
        "allowed_next_stage": None,
        "created_at": now,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"LEGACY_TEMPLATE_CREATED: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
