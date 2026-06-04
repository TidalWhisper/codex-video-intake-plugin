#!/usr/bin/env python3
"""Continue the official video-production pipeline from project manifest state.

This script dispatches the real Stage 01-04 Codex-first pipeline runners based
on manifest truth.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_core.project_state import load_json_file, sync_project_manifest_truth  # noqa: E402
import run_stage00_controller  # noqa: E402
import run_stage01_from_locked_brief  # noqa: E402
import run_stage02_from_confirmed_script  # noqa: E402
import run_stage03_from_confirmed_storyboard  # noqa: E402
import run_stage04_from_confirmed_character_bible  # noqa: E402


def _latest_project(root: Path) -> Path | None:
    if not root.exists() or not root.is_dir():
        return None
    candidates: list[tuple[str, float, Path]] = []
    for item in root.iterdir():
        manifest = item / "project_manifest.json"
        if not item.is_dir() or not manifest.exists():
            continue
        try:
            data = load_json_file(manifest)
            stamp = str(data.get("updated_at") or data.get("created_at") or "")
        except Exception:
            stamp = ""
        candidates.append((stamp, item.stat().st_mtime, item))
    if not candidates:
        return None
    candidates.sort(key=lambda record: (record[0], record[1]), reverse=True)
    return candidates[0][2]


def _resolve_manifest(args: argparse.Namespace) -> Path | None:
    if args.manifest:
        return Path(args.manifest).resolve()
    if args.project_dir:
        return (Path(args.project_dir).resolve() / "project_manifest.json").resolve()
    latest = _latest_project(Path(args.root))
    if latest is None:
        return None
    return (latest / "project_manifest.json").resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="video_projects", help="Project root used when no project is explicitly provided")
    parser.add_argument("--project-dir", default=None, help="Specific project directory to continue")
    parser.add_argument("--manifest", default=None, help="Explicit project_manifest.json path")
    parser.add_argument("--stage00-state", default=str(run_stage00_controller.default_state_path()), help="Workspace Stage 00 intake state path used before a project folder exists")
    return parser.parse_args(argv)


def _load_stage00_state_if_active(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = load_json_file(path)
    except Exception:
        return None
    status = str(data.get("status") or "").strip()
    if status in {"collecting", "draft_ready"}:
        return data
    return None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.manifest and not args.project_dir:
        workspace_state_path = Path(args.stage00_state).resolve()
        workspace_state = _load_stage00_state_if_active(workspace_state_path)
        if workspace_state is not None:
            project_dir_text = str(workspace_state.get("project_dir") or "").strip()
            if project_dir_text:
                manifest_candidate = Path(project_dir_text) / "project_manifest.json"
                if manifest_candidate.exists():
                    args.project_dir = str(Path(project_dir_text))
                else:
                    project_dir_text = ""
            if not project_dir_text:
                status = str(workspace_state.get("status") or "").strip()
                if status == "draft_ready":
                    return run_stage00_controller.main([
                        "--state-json",
                        str(workspace_state_path),
                    ])
                return run_stage00_controller.main([
                    "--state-json",
                    str(workspace_state_path),
                ])

    manifest_path = _resolve_manifest(args)
    if manifest_path is None or not manifest_path.exists():
        print("NO_PROJECT_FOUND")
        return 1

    synced = sync_project_manifest_truth(manifest_path)
    if synced is None or not synced.exists():
        print(f"ERROR: unable to sync manifest: {manifest_path}")
        return 1
    data = load_json_file(synced)
    project_dir = synced.parent

    current_stage = str(data.get("current_stage") or "").strip()
    allowed_next_stage = str(data.get("allowed_next_stage") or "").strip()
    brief_locked = bool(data.get("brief_locked"))
    script_confirmed = bool(data.get("script_confirmed"))
    storyboard_confirmed = bool(data.get("storyboard_confirmed"))
    character_bible_confirmed = bool(data.get("character_bible_confirmed"))
    keyframe_prompts_confirmed = bool(data.get("keyframe_prompts_confirmed"))
    intake_state_path = project_dir / "00_intake" / "intake_state.json"

    if not brief_locked and current_stage == "STAGE_00_INTAKE" and intake_state_path.exists():
        intake_state = _load_stage00_state_if_active(intake_state_path)
        if intake_state is not None:
            if str(intake_state.get("status") or "").strip() == "draft_ready":
                return run_stage00_controller.main([
                    "--state-json",
                    str(intake_state_path),
                    "--project-dir",
                    str(project_dir),
                ])
            return run_stage00_controller.main([
                "--state-json",
                str(intake_state_path),
                "--project-dir",
                str(project_dir),
            ])

    if brief_locked and not script_confirmed and current_stage in {"STAGE_00_BRIEF_LOCKED", "STAGE_01_SCRIPT_GENERATION"} and allowed_next_stage == "STAGE_01_SCRIPT_GENERATION":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        script_json = project_dir / "01_script" / "script.json"
        if not locked_brief.exists():
            print(f"ERROR: locked brief not found: {locked_brief}")
            return 1
        print(f"PIPELINE_DISPATCH_STAGE: STAGE_01_SCRIPT_GENERATION")
        print(f"PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py {str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')}")
        return run_stage01_from_locked_brief.main([str(locked_brief), str(script_json)])

    if brief_locked and script_confirmed and not storyboard_confirmed and current_stage in {"STAGE_01_SCRIPT_CONFIRMED", "STAGE_02_STORYBOARD_GENERATION"} and allowed_next_stage == "STAGE_02_STORYBOARD":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        script_json = project_dir / "01_script" / "script.json"
        storyboard_json = project_dir / "02_storyboard" / "storyboard.json"
        if not locked_brief.exists() or not script_json.exists():
            print("ERROR: Stage 02 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_02_STORYBOARD_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage02_from_confirmed_script.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')}"
        )
        return run_stage02_from_confirmed_script.main([str(locked_brief), str(script_json), str(storyboard_json)])

    if brief_locked and storyboard_confirmed and not character_bible_confirmed and current_stage in {"STAGE_02_STORYBOARD_CONFIRMED", "STAGE_03_CHARACTER_BIBLE_GENERATION"} and allowed_next_stage == "STAGE_03_CHARACTER_BIBLE":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        script_json = project_dir / "01_script" / "script.json"
        storyboard_json = project_dir / "02_storyboard" / "storyboard.json"
        character_json = project_dir / "03_characters" / "character_bible.json"
        if not locked_brief.exists() or not script_json.exists() or not storyboard_json.exists():
            print("ERROR: Stage 03 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_03_CHARACTER_BIBLE_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage03_from_confirmed_storyboard.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')} {str(character_json).replace(chr(92), '/')}"
        )
        return run_stage03_from_confirmed_storyboard.main([str(locked_brief), str(script_json), str(storyboard_json), str(character_json)])

    if brief_locked and character_bible_confirmed and not keyframe_prompts_confirmed and current_stage in {"STAGE_03_CHARACTER_BIBLE_CONFIRMED", "STAGE_04_KEYFRAME_PROMPTS_GENERATION"} and allowed_next_stage == "STAGE_04_KEYFRAME_PROMPTS":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        script_json = project_dir / "01_script" / "script.json"
        storyboard_json = project_dir / "02_storyboard" / "storyboard.json"
        character_json = project_dir / "03_characters" / "character_bible.json"
        keyframe_json = project_dir / "04_keyframes" / "keyframe_prompts.json"
        if not locked_brief.exists() or not script_json.exists() or not storyboard_json.exists() or not character_json.exists():
            print("ERROR: Stage 04 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_04_KEYFRAME_PROMPTS_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage04_from_confirmed_character_bible.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')} {str(character_json).replace(chr(92), '/')} {str(keyframe_json).replace(chr(92), '/')}"
        )
        return run_stage04_from_confirmed_character_bible.main([str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(keyframe_json)])

    print(f"PIPELINE_CONTINUE_NOT_IMPLEMENTED: {current_stage or 'UNKNOWN_STAGE'}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
