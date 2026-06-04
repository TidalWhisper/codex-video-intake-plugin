#!/usr/bin/env python3
"""Validate Stage 00-A intake state."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from stage00_intake_common import (  # noqa: E402
    QUESTION_KEYS,
    QUESTION_KEY_TO_INDEX,
    canonical_question_block,
    load_or_create_state,
)

REQUIRED_TOP_LEVEL = [
    "schema_version",
    "stage",
    "status",
    "project_id",
    "project_dir",
    "current_question",
    "current_question_key",
    "answers",
    "missing_required_fields",
]


def validate(data: dict[str, Any], file_path: Path | None = None) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    if data.get("stage") != "STAGE_00_INTAKE":
        errors.append("stage must be STAGE_00_INTAKE")

    status = str(data.get("status") or "")
    if status not in {"collecting", "draft_ready", "locked"}:
        errors.append("status must be collecting, draft_ready, or locked")

    question_index = data.get("current_question")
    if not isinstance(question_index, int) or question_index < 1 or question_index > 9:
        errors.append("current_question must be an integer between 1 and 9")
        question_index = 1

    current_question_key = str(data.get("current_question_key") or "")
    if current_question_key not in QUESTION_KEYS:
        errors.append("current_question_key must be one of the 9 Stage 00 question keys")
    elif QUESTION_KEY_TO_INDEX[current_question_key] != question_index:
        errors.append("current_question must match current_question_key")

    answers = data.get("answers")
    if not isinstance(answers, dict):
        errors.append("answers must be an object")

    user_answers = data.get("user_answers")
    if user_answers is not None and not isinstance(user_answers, dict):
        errors.append("user_answers must be an object when present")

    normalized = data.get("normalized")
    if normalized is not None and not isinstance(normalized, dict):
        errors.append("normalized must be an object when present")

    missing_required_fields = data.get("missing_required_fields")
    if not isinstance(missing_required_fields, list):
        errors.append("missing_required_fields must be a list")
        missing_required_fields = []
    else:
        invalid_missing = [item for item in missing_required_fields if item not in QUESTION_KEYS]
        if invalid_missing:
            errors.append("missing_required_fields contains unknown question keys")

    required_fields_complete = data.get("required_fields_complete")
    if not isinstance(required_fields_complete, bool):
        errors.append("required_fields_complete must be boolean")

    ready_for_brief_generation = data.get("ready_for_brief_generation")
    if ready_for_brief_generation is not None and not isinstance(ready_for_brief_generation, bool):
        errors.append("ready_for_brief_generation must be boolean when present")

    next_question_key = str(data.get("next_question_key") or "")
    next_prompt_text = str(data.get("next_prompt_text") or "")

    if status == "collecting":
        if next_question_key not in QUESTION_KEYS:
            errors.append("collecting state must set next_question_key to a valid Stage 00 question key")
        if next_question_key and current_question_key and next_question_key != current_question_key:
            errors.append("collecting state must keep next_question_key aligned with current_question_key")
        if current_question_key:
            expected_prompt = canonical_question_block(current_question_key)
            if next_prompt_text != expected_prompt:
                errors.append("collecting state next_prompt_text must equal the exact canonical current question block")
        if required_fields_complete is True:
            errors.append("collecting state cannot set required_fields_complete=true")
        if ready_for_brief_generation is True:
            errors.append("collecting state cannot set ready_for_brief_generation=true")

    if status == "draft_ready":
        if missing_required_fields:
            errors.append("draft_ready state must have empty missing_required_fields")
        if required_fields_complete is not True:
            errors.append("draft_ready state must set required_fields_complete=true")
        if ready_for_brief_generation is not True:
            errors.append("draft_ready state must set ready_for_brief_generation=true")
        if next_prompt_text != canonical_question_block("final_confirmation"):
            errors.append("draft_ready state next_prompt_text must equal the exact canonical final confirmation block")

    if status == "locked":
        if ready_for_brief_generation is True:
            warnings.append("locked state still has ready_for_brief_generation=true")

    if file_path and file_path.name != "intake_state.json":
        warnings.append("state file is not named intake_state.json")

    return not errors, errors, warnings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python validate_stage00_intake_state.py <intake_state.json>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    data = load_or_create_state(path)
    ok, errors, warnings = validate(data, path)

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")

    if not ok:
        print("VALIDATION FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"VALIDATION PASSED: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
