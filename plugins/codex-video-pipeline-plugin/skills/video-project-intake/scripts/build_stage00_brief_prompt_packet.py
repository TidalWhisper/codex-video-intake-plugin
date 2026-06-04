#!/usr/bin/env python3
"""Build a deterministic Stage 00-B brief prompt packet from intake state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from stage00_intake_common import (  # noqa: E402
    ensure_draft_ready_state,
    load_or_create_state,
    load_text,
    references_dir,
    utc_now,
)


def build_packet(state: dict[str, Any], state_path: Path, draft_path: Path) -> dict[str, Any]:
    ensure_draft_ready_state(state)
    refs = references_dir()
    return {
        "packet_version": "0.1.0",
        "stage_label": "Stage 00-B",
        "project_id": str(state.get("project_id") or ""),
        "project_dir": str(state.get("project_dir") or ""),
        "source_state": str(state_path.resolve()).replace("\\", "/"),
        "target_draft_path": str(draft_path.resolve()).replace("\\", "/"),
        "created_at": utc_now(),
        "intake_completion_state": {
            "status": str(state.get("status") or ""),
            "required_fields_complete": bool(state.get("required_fields_complete")),
            "missing_required_fields": list(state.get("missing_required_fields") or []),
            "ready_for_brief_generation": bool(state.get("ready_for_brief_generation")),
        },
        "answers": dict(state.get("answers") or {}),
        "user_answers": dict(state.get("user_answers") or {}),
        "normalized": dict(state.get("normalized") or {}),
        "target_contract": {
            "stage": "STAGE_00_INTAKE",
            "status": "draft",
            "confirmed_by_user": False,
            "allowed_next_stage": None,
            "must_preserve_user_intent": True,
            "must_keep_current_normalized_values_stable": True,
        },
        "behavior_rules": [
            "Generate one complete Stage 00 draft-brief structured output object.",
            "Do not invent a new story idea or override the collected answers.",
            "Keep canonical normalized values stable unless the intake state is internally inconsistent.",
            "Return a creator-facing confirmation summary for all 9 intake items.",
            "Do not mark the brief locked in this stage.",
        ],
        "schema_refs": {
            "llm_output_schema": "skills/video-project-intake/references/stage00_brief_llm_output.schema.json",
            "generation_prompt": "skills/video-project-intake/references/stage00_brief_generation_prompt.md",
            "repair_prompt": "skills/video-project-intake/references/stage00_brief_repair_prompt.md",
            "project_brief_schema": "skills/video-project-intake/references/project_brief.schema.json",
            "canonical_options": "skills/video-project-intake/references/first_layer_options.md",
            "canonical_question_blocks": "skills/video-project-intake/references/stage00_question_blocks.md",
        },
        "reference_materials": {
            "first_layer_options_markdown": load_text(refs / "first_layer_options.md").strip(),
            "question_blocks_markdown": load_text(refs / "stage00_question_blocks.md").strip(),
            "project_brief_schema_json": load_text(refs / "project_brief.schema.json").strip(),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_json", help="Path to intake_state.json")
    parser.add_argument("draft_json", help="Target path for project_brief.draft.json")
    parser.add_argument("output_json", help="Path to stage00_brief_prompt_packet.json")
    args = parser.parse_args(argv)

    state_path = Path(args.state_json)
    draft_path = Path(args.draft_json)
    output_path = Path(args.output_json)
    state = load_or_create_state(state_path)
    packet = build_packet(state, state_path, draft_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE00_BRIEF_PROMPT_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
