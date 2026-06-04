#!/usr/bin/env python3
"""Pipeline-owned Stage 00 lock wrapper that auto-continues to Stage 01."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PIPELINE_SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
INTAKE_SCRIPT_DIR = PLUGIN_ROOT / "skills" / "video-project-intake" / "scripts"
sys.path.insert(0, str(INTAKE_SCRIPT_DIR))
sys.path.insert(0, str(PIPELINE_SCRIPT_DIR))

import lock_project_brief  # noqa: E402
import run_stage01_from_locked_brief  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="Path to the project directory")
    parser.add_argument("--no-continue", action="store_true", help="Lock the brief but do not automatically continue to Stage 01")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_dir = Path(args.project_dir).resolve()
    draft_path = project_dir / "00_intake" / "project_brief.draft.json"
    locked_path = project_dir / "00_intake" / "project_brief.locked.json"
    exit_code = lock_project_brief.main([
        "lock_project_brief.py",
        str(draft_path),
        str(locked_path),
    ])
    if exit_code != 0:
        return exit_code
    if args.no_continue:
        return 0
    script_json = project_dir / "01_script" / "script.json"
    print("PIPELINE_DISPATCH_STAGE: STAGE_01_SCRIPT_GENERATION")
    print(
        "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py "
        f"{str(locked_path).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')}"
    )
    return run_stage01_from_locked_brief.main([str(locked_path), str(script_json)])


if __name__ == "__main__":
    raise SystemExit(main())
