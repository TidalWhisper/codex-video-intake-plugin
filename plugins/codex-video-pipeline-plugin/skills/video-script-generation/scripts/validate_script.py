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

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import extract_story_anchors  # noqa: E402

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief",
    "title", "logline", "theme", "characters", "settings", "duration_plan",
    "script", "self_check", "allowed_next_stage"
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def try_load_source_brief(source_brief: Any) -> dict[str, Any] | None:
    if not isinstance(source_brief, str) or not source_brief.strip():
        return None
    path = Path(source_brief)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def explicit_brief_subject(brief: dict[str, Any]) -> str:
    subject = brief.get("explicit_subject")
    if isinstance(subject, str) and subject.strip():
        return subject.strip()
    normalized = brief.get("normalized") if isinstance(brief.get("normalized"), dict) else {}
    subject = normalized.get("subject")
    if isinstance(subject, str) and subject.strip():
        return subject.strip()
    return ""


def explicit_brief_scene(brief: dict[str, Any]) -> str:
    normalized = brief.get("normalized") if isinstance(brief.get("normalized"), dict) else {}
    for key in ["scene", "scene_label", "location"]:
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    story_anchors = brief.get("story_anchors") if isinstance(brief.get("story_anchors"), dict) else {}
    for key in ["scene_label", "location"]:
        value = story_anchors.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def music_cue_matches_profile(cue: Any, profile: str) -> bool:
    text = str(cue or "").strip().lower()
    if not profile:
        return not text
    if profile == "song":
        return text.startswith("song")
    if profile == "instrumental":
        return text.startswith("instrumental")
    if profile == "underscore":
        return text.startswith("underscore")
    return True


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
        music_profile = str(script.get("music_profile") or "").strip()
        if music_profile and isinstance(sections, list):
            for idx, section in enumerate(sections):
                if not isinstance(section, dict):
                    errors.append(f"script.sections[{idx}] must be an object")
                    continue
                if not music_cue_matches_profile(section.get("music_cue"), music_profile):
                    errors.append(
                        f"script.sections[{idx}].music_cue must match script.music_profile={music_profile}"
                    )

    self_check = data.get("self_check")
    if isinstance(self_check, dict):
        for key in [
            "matches_locked_brief",
            "duration_fits",
            "genre_style_fits",
            "aspect_ratio_fits",
            "character_requirement_fits",
            "voice_fits",
            "music_fits",
            "final_output_scope_fits",
            "ready_for_storyboard",
        ]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")

    source_brief = try_load_source_brief(data.get("source_brief"))
    if source_brief:
        expected = extract_story_anchors(source_brief, 1).to_dict()
        expected_age = str(expected.get("subject_age") or "").strip()
        expected_subject = explicit_brief_subject(source_brief) or str(expected.get("subject") or "").strip()
        expected_scene = explicit_brief_scene(source_brief)

        if expected_age and isinstance(characters, list) and characters:
            first_age = str((characters[0] or {}).get("age") or "").strip()
            if expected_age not in first_age:
                errors.append(f"characters[0].age must preserve explicit brief age: expected {expected_age}")

        if expected_subject and any(token in expected_subject for token in ["规划师", "巡护员", "摄影师", "设计师", "工程师"]):
            first_name = str((characters[0] or {}).get("name") or "").strip() if isinstance(characters, list) and characters else ""
            if expected_subject not in first_name:
                errors.append(f"characters[0].name must preserve explicit brief subject identity: expected {expected_subject}")

        if expected_scene and isinstance(settings, list):
            normalized_settings = [str(item or "").strip() for item in settings]
            if not any(expected_scene in item or item in expected_scene for item in normalized_settings):
                errors.append(f"settings must preserve explicit brief scene: expected {expected_scene}")

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
