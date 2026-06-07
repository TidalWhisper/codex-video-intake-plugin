#!/usr/bin/env python3
"""Validate Stage 03 character-bible JSON without third-party dependencies.

Usage:
  python validate_character_bible.py --mode draft video_projects/<project_id>/03_characters/character_bible.json
  python validate_character_bible.py --mode final video_projects/<project_id>/03_characters/character_bible.json
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_script", "source_storyboard",
    "characters", "reference_image_required", "reference_image_handoff", "self_check", "allowed_next_stage"
]
REQUIRED_CHARACTER = [
    "character_id", "name", "role", "age", "gender_presentation", "appearance", "personality",
    "emotional_arc", "voice_profile", "visual_consistency_prompt", "negative_consistency_prompt", "performance_profile"
]
REQUIRED_APPEARANCE = ["face", "hair", "body", "clothing", "accessories"]
CHAR_ID_RE = re.compile(r"^CHAR_\d{3}$")


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
    if data.get("stage") != "STAGE_03_CHARACTER_BIBLE":
        errors.append("stage must be STAGE_03_CHARACTER_BIBLE")
    if data.get("status") not in {"draft", "confirmed"}:
        errors.append("status must be draft or confirmed")
    for key in ["project_id", "source_brief", "source_script", "source_storyboard"]:
        if is_blank(data.get(key)):
            errors.append(f"{key} must not be blank")
    if not isinstance(data.get("characters"), list):
        errors.append("characters must be a list")
    if not isinstance(data.get("reference_image_required"), bool):
        errors.append("reference_image_required must be a boolean")
    if data.get("reference_image_plan") is not None and not isinstance(data.get("reference_image_plan"), dict):
        errors.append("reference_image_plan must be an object when present")
    if data.get("reference_image_status") is not None and not isinstance(data.get("reference_image_status"), dict):
        errors.append("reference_image_status must be an object when present")
    if data.get("stage05_execution_readiness") is not None and not isinstance(data.get("stage05_execution_readiness"), dict):
        errors.append("stage05_execution_readiness must be an object when present")
    if not isinstance(data.get("self_check"), dict):
        errors.append("self_check must be an object")

    if mode == "draft":
        if isinstance(data.get("characters"), list) and len(data.get("characters")) == 0:
            warnings.append("draft character_bible has zero characters; expected until Codex fills Stage 03 content")
        return not errors, errors, warnings

    chars = data.get("characters")
    if isinstance(chars, list):
        if not chars:
            errors.append("characters must not be empty in final mode")
        seen = set()
        for idx, ch in enumerate(chars):
            if not isinstance(ch, dict):
                errors.append(f"characters[{idx}] must be an object")
                continue
            for key in REQUIRED_CHARACTER:
                if key not in ch:
                    errors.append(f"characters[{idx}] missing field: {key}")
            cid = ch.get("character_id")
            if not isinstance(cid, str) or not CHAR_ID_RE.match(cid):
                errors.append(f"characters[{idx}].character_id must look like CHAR_001")
            elif cid in seen:
                errors.append(f"duplicate character_id: {cid}")
            else:
                seen.add(cid)
            for key in ["name", "role", "age", "gender_presentation", "personality", "visual_consistency_prompt", "negative_consistency_prompt"]:
                if is_blank(ch.get(key)):
                    errors.append(f"characters[{idx}].{key} must not be blank in final mode")
            app = ch.get("appearance")
            if not isinstance(app, dict):
                errors.append(f"characters[{idx}].appearance must be an object")
            else:
                for key in REQUIRED_APPEARANCE:
                    if is_blank(app.get(key)):
                        errors.append(f"characters[{idx}].appearance.{key} must not be blank in final mode")
            arc = ch.get("emotional_arc")
            if not isinstance(arc, list) or not arc or any(is_blank(item) for item in arc):
                errors.append(f"characters[{idx}].emotional_arc must be a non-empty list of strings")
            vp = ch.get("voice_profile")
            if not isinstance(vp, dict):
                errors.append(f"characters[{idx}].voice_profile must be an object")
            else:
                if not isinstance(vp.get("needed"), bool):
                    errors.append(f"characters[{idx}].voice_profile.needed must be a boolean")
                if is_blank(vp.get("suggested_voice")):
                    errors.append(f"characters[{idx}].voice_profile.suggested_voice must not be blank in final mode")
            performance_profile = ch.get("performance_profile")
            if not isinstance(performance_profile, dict):
                errors.append(f"characters[{idx}].performance_profile must be an object")
            else:
                for key in ["baseline_expression", "movement_style", "dialogue_delivery", "continuity_anchor"]:
                    if is_blank(performance_profile.get(key)):
                        errors.append(f"characters[{idx}].performance_profile.{key} must not be blank in final mode")
                gesture_rules = performance_profile.get("gesture_rules")
                if not isinstance(gesture_rules, list) or not gesture_rules or any(is_blank(item) for item in gesture_rules):
                    errors.append(f"characters[{idx}].performance_profile.gesture_rules must be a non-empty list of strings")

    self_check = data.get("self_check")
    if isinstance(self_check, dict):
        for key in ["matches_locked_brief", "matches_script", "matches_storyboard", "ready_for_keyframe_stage"]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")
        for key in ["reference_images_planned", "reference_images_ready", "safe_for_character_locked_image_generation"]:
            value = self_check.get(key)
            if value is not None and not isinstance(value, bool):
                errors.append(f"self_check.{key} must be a boolean when present")
    reference_handoff = data.get("reference_image_handoff")
    if not isinstance(reference_handoff, dict):
        errors.append("reference_image_handoff must be an object")
    else:
        if not isinstance(reference_handoff.get("ready_for_stage05"), bool):
            errors.append("reference_image_handoff.ready_for_stage05 must be a boolean")
        for key in ["summary", "next_action"]:
            if is_blank(reference_handoff.get(key)):
                errors.append(f"reference_image_handoff.{key} must not be blank in final mode")
        capture_focus = reference_handoff.get("capture_focus")
        if not isinstance(capture_focus, list) or any(is_blank(item) for item in capture_focus):
            errors.append("reference_image_handoff.capture_focus must be a list of non-blank strings")
    reference_status = data.get("reference_image_status")
    if isinstance(reference_status, dict):
        for key in ["required", "all_present"]:
            if key in reference_status and not isinstance(reference_status.get(key), bool):
                errors.append(f"reference_image_status.{key} must be a boolean when present")
        for key in ["target_paths", "existing_paths", "missing_paths", "items"]:
            if key in reference_status and not isinstance(reference_status.get(key), list):
                errors.append(f"reference_image_status.{key} must be a list when present")
    stage05_execution_readiness = data.get("stage05_execution_readiness")
    if isinstance(stage05_execution_readiness, dict):
        if "safe_to_auto_generate" in stage05_execution_readiness and not isinstance(stage05_execution_readiness.get("safe_to_auto_generate"), bool):
            errors.append("stage05_execution_readiness.safe_to_auto_generate must be a boolean when present")
        for key in ["blocker_reasons", "missing_reference_images"]:
            if key in stage05_execution_readiness and not isinstance(stage05_execution_readiness.get(key), list):
                errors.append(f"stage05_execution_readiness.{key} must be a list when present")
    return not errors, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("character_bible_json")
    parser.add_argument("--mode", choices=["draft", "final"], default="final")
    args = parser.parse_args(argv)
    data = load_json(Path(args.character_bible_json))
    ok, errors, warnings = validate(data, args.mode)
    if warnings:
        print("CHARACTER BIBLE VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"CHARACTER BIBLE VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"CHARACTER BIBLE VALIDATION PASSED ({args.mode} mode): {args.character_bible_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
