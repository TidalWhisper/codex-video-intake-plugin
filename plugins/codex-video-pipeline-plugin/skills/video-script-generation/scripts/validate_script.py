#!/usr/bin/env python3
"""Validate Stage 01 script JSON without third-party dependencies.

Usage:
  python validate_script.py --mode draft video_projects/<project_id>/01_script/script.json
  python validate_script.py --mode final video_projects/<project_id>/01_script/script.json

Modes:
  draft: structure-only validation for newly scaffolded script templates.
  final: content validation for a completed Stage 01 script before user review.

Default mode is final.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief",
    "title", "logline", "theme", "characters", "settings", "duration_plan",
    "script", "self_check", "allowed_next_stage"
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def validate(data: dict[str, Any], mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    if data.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        errors.append("stage must be STAGE_01_SCRIPT_GENERATION")
    if data.get("status") not in {"draft", "confirmed"}:
        errors.append("status must be draft or confirmed")
    if is_blank(data.get("project_id")):
        errors.append("project_id must not be blank")
    if is_blank(data.get("source_brief")):
        errors.append("source_brief must not be blank")
    if is_blank(data.get("logline")):
        errors.append("logline must not be blank")
    if not isinstance(data.get("characters"), list):
        errors.append("characters must be a list")
    if not isinstance(data.get("settings"), list):
        errors.append("settings must be a list")
    if not isinstance(data.get("duration_plan"), dict):
        errors.append("duration_plan must be an object")
    if not isinstance(data.get("script"), dict):
        errors.append("script must be an object")
    if not isinstance(data.get("self_check"), dict):
        errors.append("self_check must be an object")

    if mode == "draft":
        # Draft mode is meant for new_script_template.py output. It checks the
        # file shape and locked-brief linkage, but it intentionally allows
        # creative fields to be empty until Codex fills them.
        if is_blank(data.get("title")):
            warnings.append("draft script title is blank; expected until Codex fills Stage 01 content")
        if is_blank(data.get("theme")):
            warnings.append("draft script theme is blank; expected until Codex fills Stage 01 content")
        return not errors, errors, warnings

    # final mode: completed script must contain actual creative content.
    if is_blank(data.get("title")):
        errors.append("title must not be blank in final mode")
    if is_blank(data.get("theme")):
        errors.append("theme must not be blank in final mode")

    characters = data.get("characters")
    if isinstance(characters, list) and not characters:
        errors.append("characters must not be empty in final mode")

    settings = data.get("settings")
    if isinstance(settings, list) and not settings:
        errors.append("settings must not be empty in final mode")

    duration_plan = data.get("duration_plan")
    if isinstance(duration_plan, dict):
        beats = duration_plan.get("beats")
        if not isinstance(beats, list) or not beats:
            errors.append("duration_plan.beats must be a non-empty list in final mode")

    script = data.get("script")
    if isinstance(script, dict):
        sections = script.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append("script.sections must be a non-empty list in final mode")

    self_check = data.get("self_check")
    if isinstance(self_check, dict):
        for key in ["matches_locked_brief", "duration_fits", "genre_style_fits", "ready_for_storyboard"]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")

    return not errors, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("script_json", help="Path to script.json")
    parser.add_argument("--mode", choices=["draft", "final"], default="final", help="Validation strictness")
    args = parser.parse_args(argv)

    path = Path(args.script_json)
    data = load_json(path)
    ok, errors, warnings = validate(data, args.mode)

    if warnings:
        print("SCRIPT VALIDATION WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")

    if not ok:
        print(f"SCRIPT VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1

    print(f"SCRIPT VALIDATION PASSED ({args.mode} mode): {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
