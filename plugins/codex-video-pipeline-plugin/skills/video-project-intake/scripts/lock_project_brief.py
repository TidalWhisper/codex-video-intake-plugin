#!/usr/bin/env python3
"""Lock a validated Stage 00 video project brief.

Usage:
  python lock_project_brief.py video_projects/<project_id>/00_intake/project_brief.draft.json video_projects/<project_id>/00_intake/project_brief.locked.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import validator from same directory without third-party dependencies.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
PLUGIN_ROOT = next(anchor for anchor in [SCRIPT_DIR, *SCRIPT_DIR.parents] if anchor.name == "codex-video-pipeline-plugin")
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
from validate_project_brief import validate  # noqa: E402
from pipeline_core.pipeline_blueprints import routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file, update_project_manifest_for_stage, utc_now  # noqa: E402
from pipeline_core.quality_contracts import build_quality_contract  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements  # noqa: E402


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python lock_project_brief.py <draft.json> <locked.json>", file=sys.stderr)
        return 2

    draft_path = Path(argv[1])
    locked_path = Path(argv[2])
    data = load_json(draft_path)

    ok, errors, warnings = validate(data, draft_path)
    if errors:
        print("DRAFT CANNOT BE LOCKED:")
        for error in errors:
            print(f"- {error}")
        return 1

    if data.get("required_fields_complete") is not True:
        print("DRAFT CANNOT BE LOCKED: required_fields_complete must be true")
        return 1
    if data.get("missing_required_fields"):
        print("DRAFT CANNOT BE LOCKED: missing_required_fields must be empty")
        return 1

    # The locked file must be written back into the same project folder.
    if draft_path.parent.name == "00_intake" and locked_path.parent.resolve() != draft_path.parent.resolve():
        print("DRAFT CANNOT BE LOCKED: locked.json must be written to the same 00_intake folder as draft.json")
        return 1

    data["status"] = "locked"
    data["confirmed_by_user"] = True
    data["allowed_next_stage"] = "STAGE_01_SCRIPT_GENERATION"
    data["locked_at"] = utc_now()
    data["routing"] = routing_from_brief(data)
    data["compiled_requirements"] = compile_requirements(data)
    data["quality_contract"] = build_quality_contract(data, data["compiled_requirements"])

    manifest_path = draft_path.parent.parent / "project_manifest.json"
    if manifest_path.exists():
        try:
            manifest = load_json_file(manifest_path)
        except json.JSONDecodeError as exc:
            print(f"LOCKED BRIEF WARNING: project_manifest.json is invalid JSON: {exc}")
        else:
            manifest["current_stage"] = "STAGE_00_BRIEF_LOCKED"
            manifest["requested_output_scope"] = data["routing"]["requested_output_scope"]
            manifest["requested_output_label"] = data["routing"]["requested_output_label"]
            manifest["requested_terminal_stage"] = data["routing"]["requested_terminal_stage"]
            manifest["allowed_next_stage"] = "STAGE_01_SCRIPT_GENERATION"
            manifest["brief_locked"] = True
            manifest["compiled_requirements"] = data["compiled_requirements"]
            manifest["quality_contract"] = data["quality_contract"]
            manifest["updated_at"] = utc_now()
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        update_project_manifest_for_stage(
            draft_path,
            current_stage="STAGE_00_BRIEF_LOCKED",
            allowed_next_stage="STAGE_01_SCRIPT_GENERATION",
            flags={"brief_locked": True},
            status="active",
        )

    ok2, errors2, warnings2 = validate(data, locked_path)
    if not ok2:
        print("LOCKED BRIEF VALIDATION FAILED:")
        for error in errors2:
            print(f"- {error}")
        return 1

    locked_path.parent.mkdir(parents=True, exist_ok=True)
    locked_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"LOCKED: {locked_path}")
    if warnings or warnings2:
        print("WARNINGS:")
        for warning in warnings + warnings2:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
