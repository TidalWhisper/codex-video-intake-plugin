#!/usr/bin/env python3
"""Validate Stage 02 storyboard JSON without third-party dependencies.

Usage:
  python validate_storyboard.py --mode draft video_projects/<project_id>/02_storyboard/storyboard.json
  python validate_storyboard.py --mode final video_projects/<project_id>/02_storyboard/storyboard.json
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_script",
    "target_duration_sec", "shot_count", "shots", "self_check", "allowed_next_stage"
]
REQUIRED_SHOT = [
    "shot_id", "start", "end", "duration_sec", "scene", "camera", "composition", "action",
    "emotion", "dialogue", "voiceover", "sound_music", "transition_to_next", "production_note"
]
SHOT_ID_RE = re.compile(r"^S\d{3}$")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def validate(data: dict[str, Any], mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_02_STORYBOARD_GENERATION":
        errors.append("stage must be STAGE_02_STORYBOARD_GENERATION")
    if data.get("status") not in {"draft", "confirmed"}:
        errors.append("status must be draft or confirmed")
    for key in ["project_id", "source_brief", "source_script"]:
        if is_blank(data.get(key)):
            errors.append(f"{key} must not be blank")
    if not isinstance(data.get("target_duration_sec"), int) or data.get("target_duration_sec", 0) <= 0:
        errors.append("target_duration_sec must be a positive integer")
    if not isinstance(data.get("shot_count"), int) or data.get("shot_count", -1) < 0:
        errors.append("shot_count must be a non-negative integer")
    if not isinstance(data.get("shots"), list):
        errors.append("shots must be a list")
    if not isinstance(data.get("self_check"), dict):
        errors.append("self_check must be an object")

    if mode == "draft":
        if data.get("shot_count") == 0:
            warnings.append("draft storyboard has zero shots; expected until Codex fills Stage 02 content")
        return not errors, errors, warnings

    shots = data.get("shots")
    if isinstance(shots, list):
        if not shots:
            errors.append("shots must not be empty in final mode")
        if data.get("shot_count") != len(shots):
            errors.append("shot_count must equal len(shots) in final mode")
        seen = set()
        total = 0
        for idx, shot in enumerate(shots):
            if not isinstance(shot, dict):
                errors.append(f"shots[{idx}] must be an object")
                continue
            for key in REQUIRED_SHOT:
                if key not in shot:
                    errors.append(f"shots[{idx}] missing field: {key}")
            shot_id = shot.get("shot_id")
            if not isinstance(shot_id, str) or not SHOT_ID_RE.match(shot_id):
                errors.append(f"shots[{idx}].shot_id must look like S001")
            elif shot_id in seen:
                errors.append(f"duplicate shot_id: {shot_id}")
            else:
                seen.add(shot_id)
            duration = shot.get("duration_sec")
            if not isinstance(duration, (int, float)) or duration <= 0:
                errors.append(f"shots[{idx}].duration_sec must be positive")
            else:
                total += float(duration)
            for text_key in ["scene", "camera", "composition", "action", "emotion", "transition_to_next", "production_note"]:
                if is_blank(shot.get(text_key)):
                    errors.append(f"shots[{idx}].{text_key} must not be blank in final mode")
        target = data.get("target_duration_sec")
        if isinstance(target, int) and target > 0 and shots:
            tolerance = max(2.0, target * 0.15)
            if abs(total - target) > tolerance:
                errors.append(f"sum(duration_sec)={total:g} differs from target_duration_sec={target} by more than tolerance {tolerance:g}")

    self_check = data.get("self_check")
    if isinstance(self_check, dict):
        for key in ["matches_locked_brief", "matches_script", "duration_fits", "ready_for_character_stage"]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")
    return not errors, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("storyboard_json")
    parser.add_argument("--mode", choices=["draft", "final"], default="final")
    args = parser.parse_args(argv)
    data = load_json(Path(args.storyboard_json))
    ok, errors, warnings = validate(data, args.mode)
    if warnings:
        print("STORYBOARD VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"STORYBOARD VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"STORYBOARD VALIDATION PASSED ({args.mode} mode): {args.storyboard_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
