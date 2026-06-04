#!/usr/bin/env python3
"""Write Stage 00-A intake state from Codex structured output."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from stage00_intake_common import (  # noqa: E402
    QUESTION_KEY_TO_INDEX,
    canonical_question_block,
    load_json,
    load_or_create_state,
    utc_now,
)
import validate_stage00_intake_state as validate_stage00_intake_state_module  # noqa: E402

REQUIRED_KEYS = [
    "answered_question_key",
    "user_answer_entry",
    "user_answers_patch",
    "normalized_patch",
    "missing_required_fields",
    "required_fields_complete",
    "status",
    "next_question_key",
    "next_prompt_text",
    "needs_followup",
    "followup_reason",
    "completion_summary",
]


def ensure_shape(data: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise SystemExit(f"ERROR: missing required keys in Stage 00 intake llm output: {', '.join(missing)}")


def merge_dict(target: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(target)
    merged.update(patch)
    return merged


def write_state(state_path: Path, llm_output: dict[str, Any], output_state_path: Path | None = None) -> dict[str, Any]:
    ensure_shape(llm_output)
    state = load_or_create_state(state_path)
    current_question_key = str(state.get("current_question_key") or "")
    answered_question_key = str(llm_output.get("answered_question_key") or "")
    if answered_question_key != current_question_key:
        raise SystemExit(
            "ERROR: Stage 00 intake llm output answered_question_key does not match current state question: "
            f"{answered_question_key} != {current_question_key}"
        )

    answers = dict(state.get("answers") or {})
    answer_entry = dict(llm_output.get("user_answer_entry") or {})
    answer_entry["question_key"] = answered_question_key
    answers[answered_question_key] = answer_entry
    state["answers"] = answers

    state["user_answers"] = merge_dict(
        dict(state.get("user_answers") or {}),
        dict(llm_output.get("user_answers_patch") or {}),
    )
    state["normalized"] = merge_dict(
        dict(state.get("normalized") or {}),
        dict(llm_output.get("normalized_patch") or {}),
    )
    state["missing_required_fields"] = list(llm_output.get("missing_required_fields") or [])
    state["required_fields_complete"] = bool(llm_output.get("required_fields_complete"))
    state["status"] = str(llm_output.get("status") or "collecting")
    state["last_user_reply"] = str(answer_entry.get("raw_input") or "")
    state["needs_followup"] = bool(llm_output.get("needs_followup"))
    state["followup_reason"] = str(llm_output.get("followup_reason") or "")
    state["completion_summary"] = str(llm_output.get("completion_summary") or "")

    if state["status"] == "draft_ready":
        state["ready_for_brief_generation"] = True
        state["next_question_key"] = ""
        state["next_prompt_text"] = canonical_question_block("final_confirmation")
        state["current_question"] = QUESTION_KEY_TO_INDEX["final_output"]
        state["current_question_key"] = "final_output"
    else:
        next_question_key = str(llm_output.get("next_question_key") or "")
        state["ready_for_brief_generation"] = False
        state["next_question_key"] = next_question_key
        state["next_prompt_text"] = str(llm_output.get("next_prompt_text") or "")
        if next_question_key not in QUESTION_KEY_TO_INDEX:
            raise SystemExit(f"ERROR: unknown next_question_key from Stage 00 intake llm output: {next_question_key}")
        state["current_question"] = QUESTION_KEY_TO_INDEX[next_question_key]
        state["current_question_key"] = next_question_key

    state["updated_at"] = utc_now()

    ok, errors, warnings = validate_stage00_intake_state_module.validate(state, output_state_path or state_path)
    if not ok:
        raise SystemExit("ERROR: Stage 00 intake state validation failed after write:\n- " + "\n- ".join(errors))
    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}")

    final_path = output_state_path or state_path
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def main(argv: list[str]) -> int:
    if len(argv) not in {3, 4}:
        print(
            "Usage: python write_stage00_intake_state.py <intake_state.json> <stage00_intake_turn_llm_output.json> [<output_state.json>]",
            file=sys.stderr,
        )
        return 2
    state_path = Path(argv[1])
    llm_output_path = Path(argv[2])
    output_state_path = Path(argv[3]) if len(argv) == 4 else state_path
    llm_output = load_json(llm_output_path)
    write_state(state_path, llm_output, output_state_path)
    print(f"STAGE00_INTAKE_STATE_WRITTEN: {output_state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
