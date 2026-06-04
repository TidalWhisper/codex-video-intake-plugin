#!/usr/bin/env python3
"""Pipeline-owned Stage 00-B entry wrapper."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PIPELINE_SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
INTAKE_SCRIPT_DIR = PLUGIN_ROOT / "skills" / "video-project-intake" / "scripts"
sys.path.insert(0, str(INTAKE_SCRIPT_DIR))

import create_project_folder  # noqa: E402
from run_stage00_brief_codex_flow import main as run_stage00_brief_codex_flow_main  # noqa: E402
from stage00_intake_common import ensure_draft_ready_state, load_or_create_state, utc_now  # noqa: E402


def default_state_path() -> Path:
    return Path(".video_project/intake/intake_state.json").resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-json", default=str(default_state_path()), help="Path to intake_state.json")
    parser.add_argument("--project-root", default="video_projects", help="Root directory for project creation when the intake is still workspace-local")
    parser.add_argument("--project-dir", default=None, help="Explicit project directory to use for Stage 00-B output")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary name or path")
    parser.add_argument("--max-repair-attempts", type=int, default=2, help="How many automatic repair attempts to allow after the first generation fails validation")
    return parser.parse_args(argv)


def _is_project_intake_state(state_path: Path) -> bool:
    return state_path.parent.name == "00_intake" and (state_path.parent.parent / "project_manifest.json").exists()


def _derive_title(state: dict) -> str:
    user_answers = state.get("user_answers") if isinstance(state.get("user_answers"), dict) else {}
    normalized = state.get("normalized") if isinstance(state.get("normalized"), dict) else {}
    return str(user_answers.get("idea") or normalized.get("idea") or "video project").strip()


def materialize_project_intake(state_path: Path, project_root: Path, explicit_project_dir: Path | None) -> tuple[Path, Path]:
    state = load_or_create_state(state_path)
    ensure_draft_ready_state(state)

    if explicit_project_dir is not None:
        project_dir = explicit_project_dir.resolve()
    elif _is_project_intake_state(state_path):
        project_dir = state_path.parent.parent.resolve()
    else:
        project_dir = create_project_folder.create_project(project_root.resolve(), title=_derive_title(state))

    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    target_state_path = intake_dir / "intake_state.json"
    state["project_id"] = project_dir.name
    state["project_dir"] = str(project_dir).replace("\\", "/")
    state["updated_at"] = utc_now()
    target_state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    if state_path.resolve() != target_state_path.resolve():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return project_dir, target_state_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_state_path = Path(args.state_json).resolve()
    explicit_project_dir = Path(args.project_dir).resolve() if args.project_dir else None
    project_dir, state_path = materialize_project_intake(source_state_path, Path(args.project_root), explicit_project_dir)
    draft_json = project_dir / "00_intake" / "project_brief.draft.json"
    print(f"PIPELINE_DISPATCH_STAGE: STAGE_00_BRIEF_GENERATION")
    print(
        "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage00_brief_from_intake.py "
        f"--state-json {str(state_path).replace(chr(92), '/')} --project-dir {str(project_dir).replace(chr(92), '/')}"
    )
    return run_stage00_brief_codex_flow_main([
        str(state_path),
        str(draft_json),
        "--codex-bin",
        str(args.codex_bin),
        "--max-repair-attempts",
        str(args.max_repair_attempts),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
