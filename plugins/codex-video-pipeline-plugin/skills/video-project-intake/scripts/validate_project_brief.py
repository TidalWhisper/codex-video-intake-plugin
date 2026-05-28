#!/usr/bin/env python3
"""Validate Stage 00 video project brief without third-party dependencies.

Usage:
  python validate_project_brief.py video_projects/<project_id>/00_intake/project_brief.draft.json

This validator checks both content structure and project-folder consistency:
- brief.project_id must match the basename of brief.project_dir
- when the file is inside video_projects/<project_id>/00_intake/, brief.project_id
  must match that folder name
- when project_manifest.json exists, manifest.project_id must match the brief
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = [
    "schema_version",
    "project_id",
    "project_dir",
    "stage",
    "status",
    "confirmed_by_user",
    "required_fields_complete",
    "missing_required_fields",
    "source",
    "normalized",
]

REQUIRED_NORMALIZED = [
    "idea",
    "target_duration_sec",
    "target_duration_label",
    "genre",
    "style",
    "aspect_ratio",
    "aspect_ratio_label",
    "resolution",
    "resolution_label",
    "characters_mode",
    "characters_required",
    "voice_mode",
    "voice_required",
    "music_mode",
    "music_required",
    "final_output",
]

MISSING_IF_BLANK = [
    "idea",
    "target_duration_sec",
    "genre",
    "style",
    "aspect_ratio",
    "resolution",
    "characters_mode",
    "voice_mode",
    "music_mode",
    "final_output",
]


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def normalized_path_basename(path_text: Any) -> str:
    if not isinstance(path_text, str) or not path_text.strip():
        return ""
    normalized = path_text.replace("\\", "/").rstrip("/")
    return normalized.split("/")[-1] if normalized else ""


def infer_project_id_from_file_path(path: Path | None) -> str:
    if path is None:
        return ""
    # Expected: <project_dir>/00_intake/project_brief.*.json
    try:
        if path.parent.name == "00_intake":
            return path.parent.parent.name
    except IndexError:
        return ""
    return ""


def maybe_load_manifest(file_path: Path | None) -> dict[str, Any] | None:
    if file_path is None or file_path.parent.name != "00_intake":
        return None
    manifest_path = file_path.parent.parent / "project_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"__invalid_json__": str(manifest_path)}


def validate(data: dict[str, Any], file_path: Path | None = None) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    if data.get("stage") != "STAGE_00_INTAKE":
        errors.append("stage must be STAGE_00_INTAKE")

    if data.get("status") not in {"draft", "locked"}:
        errors.append("status must be draft or locked")

    if not isinstance(data.get("confirmed_by_user"), bool):
        errors.append("confirmed_by_user must be boolean")

    project_id = data.get("project_id")
    project_dir = data.get("project_dir")
    if not isinstance(project_id, str) or not project_id.strip():
        errors.append("project_id must be a non-blank string")
        project_id = ""
    else:
        project_id = project_id.strip()

    if not isinstance(project_dir, str) or not project_dir.strip():
        errors.append("project_dir must be a non-blank string")
    else:
        declared_dir_id = normalized_path_basename(project_dir)
        if project_id and declared_dir_id and declared_dir_id != project_id:
            errors.append(
                "project_id must match basename of project_dir: "
                f"project_id={project_id}, project_dir_basename={declared_dir_id}"
            )

    inferred_path_id = infer_project_id_from_file_path(file_path)
    if inferred_path_id and project_id and inferred_path_id != project_id:
        errors.append(
            "project_id must match the containing project folder: "
            f"project_id={project_id}, folder={inferred_path_id}"
        )

    manifest = maybe_load_manifest(file_path)
    if manifest:
        if "__invalid_json__" in manifest:
            errors.append(f"project_manifest.json is invalid JSON: {manifest['__invalid_json__']}")
        else:
            manifest_project_id = manifest.get("project_id")
            if manifest_project_id and project_id and manifest_project_id != project_id:
                errors.append(
                    "project_id must match project_manifest.json: "
                    f"brief={project_id}, manifest={manifest_project_id}"
                )
            manifest_project_dir = manifest.get("project_dir")
            if manifest_project_dir and normalized_path_basename(manifest_project_dir) != project_id:
                errors.append(
                    "project_manifest.json project_dir basename must match project_id: "
                    f"project_id={project_id}, manifest_project_dir={manifest_project_dir}"
                )

    normalized = data.get("normalized")
    if not isinstance(normalized, dict):
        errors.append("normalized must be an object")
        normalized = {}

    for key in REQUIRED_NORMALIZED:
        if key not in normalized:
            errors.append(f"missing normalized key: {key}")

    missing = []
    for key in MISSING_IF_BLANK:
        if is_blank(normalized.get(key)):
            missing.append(key)

    declared_missing = data.get("missing_required_fields")
    if not isinstance(declared_missing, list):
        errors.append("missing_required_fields must be a list")
        declared_missing = []

    # Draft can be incomplete, but if it claims complete, missing must be empty.
    if data.get("required_fields_complete") is True and missing:
        errors.append(
            "required_fields_complete is true but these normalized fields are blank: "
            + ", ".join(missing)
        )

    if data.get("required_fields_complete") is True and declared_missing:
        errors.append("required_fields_complete is true but missing_required_fields is not empty")

    if data.get("required_fields_complete") is False and not declared_missing:
        warnings.append("required_fields_complete is false but missing_required_fields is empty")

    if data.get("status") == "locked":
        if data.get("confirmed_by_user") is not True:
            errors.append("locked brief must have confirmed_by_user=true")
        if data.get("allowed_next_stage") != "STAGE_01_SCRIPT_GENERATION":
            errors.append("locked brief must allow STAGE_01_SCRIPT_GENERATION")
        if not data.get("locked_at"):
            errors.append("locked brief must include locked_at")
    else:
        if data.get("confirmed_by_user") is True:
            errors.append("draft brief must not have confirmed_by_user=true")
        if data.get("allowed_next_stage") not in (None, ""):
            errors.append("draft brief must not set allowed_next_stage")

    return not errors, errors, warnings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python validate_project_brief.py <project_brief.json>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    data = load_json(path)
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
