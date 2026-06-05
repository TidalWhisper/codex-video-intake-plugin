#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "skills" / "video-script-generation" / "scripts"))

from pipeline_core.project_state import load_json_file, write_json_file  # noqa: E402
import continue_pipeline  # noqa: E402
import validate_script  # noqa: E402


def _load(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python confirm_stage01_and_continue.py <project_dir>", file=sys.stderr)
        return 2

    project_dir = Path(args[0]).resolve()
    manifest_path = project_dir / "project_manifest.json"
    script_path = project_dir / "01_script" / "script.json"

    if not manifest_path.exists():
        print(f"ERROR: project manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    if not script_path.exists():
        print(f"ERROR: Stage 01 script not found: {script_path}", file=sys.stderr)
        return 1

    script_data = _load(script_path)
    ok, errors, _warnings = validate_script.validate(script_data, mode="final")
    if not ok:
        print("ERROR: Stage 01 script failed final validation before confirmation:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    script_data["status"] = "confirmed"
    script_data["allowed_next_stage"] = "STAGE_02_STORYBOARD"
    write_json_file(script_path, script_data)

    manifest_data = _load(manifest_path)
    manifest_data["current_stage"] = "STAGE_01_SCRIPT_CONFIRMED"
    manifest_data["brief_locked"] = True
    manifest_data["script_confirmed"] = True
    manifest_data["allowed_next_stage"] = "STAGE_02_STORYBOARD"
    write_json_file(manifest_path, manifest_data)

    print(f"STAGE01_CONFIRMED: {project_dir}")
    return continue_pipeline.main(["--project-dir", str(project_dir)])


if __name__ == "__main__":
    raise SystemExit(main())
