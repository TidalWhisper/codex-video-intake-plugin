#!/usr/bin/env python3
"""Build a deterministic Stage 00-A intake-turn prompt packet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from stage00_intake_common import (  # noqa: E402
    QUESTION_KEYS,
    canonical_question_block,
    load_or_create_state,
    load_text,
    references_dir,
    utc_now,
)


def ensure_collecting_state(state: dict[str, Any]) -> None:
    status = str(state.get("status") or "")
    if status == "locked":
        raise SystemExit("ERROR: Stage 00 intake is already locked")
    if status == "draft_ready":
        raise SystemExit("ERROR: Stage 00 intake is already draft_ready; use Stage 00-B next")


def build_packet(state: dict[str, Any], state_path: Path, user_reply: str) -> dict[str, Any]:
    ensure_collecting_state(state)
    current_question_key = str(state.get("current_question_key") or "")
    current_question = int(state.get("current_question") or 1)
    refs = references_dir()
    return {
        "packet_version": "0.1.0",
        "stage_label": "Stage 00-A",
        "project_id": str(state.get("project_id") or ""),
        "project_dir": str(state.get("project_dir") or ""),
        "source_state": str(state_path.resolve()).replace("\\", "/"),
        "created_at": utc_now(),
        "current_state": {
            "status": str(state.get("status") or ""),
            "current_question": current_question,
            "current_question_key": current_question_key,
            "missing_required_fields": list(state.get("missing_required_fields") or []),
            "required_fields_complete": bool(state.get("required_fields_complete")),
        },
        "answers_so_far": dict(state.get("answers") or {}),
        "user_answers_so_far": dict(state.get("user_answers") or {}),
        "normalized_so_far": dict(state.get("normalized") or {}),
        "user_reply_raw": user_reply,
        "canonical_context": {
            "question_order": list(QUESTION_KEYS),
            "current_question_block": canonical_question_block(current_question_key),
            "final_confirmation_block": canonical_question_block("final_confirmation"),
            "first_layer_options_markdown": load_text(refs / "first_layer_options.md").strip(),
            "question_blocks_markdown": load_text(refs / "stage00_question_blocks.md").strip(),
        },
        "behavior_rules": [
            "Interpret only the current Stage 00 question unless the user explicitly includes a direct correction for a prior answer.",
            "Preserve option letters and free-text notes separately when possible.",
            "If the answer is incomplete for the current question, keep the same question and repeat the exact canonical question block.",
            "If all nine questions are complete, set status=draft_ready and use the exact canonical final confirmation block as next_prompt_text.",
            "Do not generate project_brief.draft.json in this stage.",
        ],
        "schema_refs": {
            "llm_output_schema": "skills/video-project-intake/references/stage00_intake_turn_output.schema.json",
            "generation_prompt": "skills/video-project-intake/references/stage00_intake_generation_prompt.md",
            "intake_state_schema": "skills/video-project-intake/references/intake_state.schema.json",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_json", help="Path to intake_state.json")
    parser.add_argument("output_json", help="Path to stage00_intake_prompt_packet.json")
    parser.add_argument("--user-reply", required=True, help="Raw user reply for the current Stage 00 turn")
    args = parser.parse_args(argv)

    state_path = Path(args.state_json)
    output_path = Path(args.output_json)
    state = load_or_create_state(state_path)
    packet = build_packet(state, state_path, args.user_reply)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE00_INTAKE_PROMPT_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
