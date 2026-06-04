#!/usr/bin/env python3
"""Pipeline-owned Stage 00-A entry wrapper."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PIPELINE_SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
INTAKE_SCRIPT_DIR = PLUGIN_ROOT / "skills" / "video-project-intake" / "scripts"
sys.path.insert(0, str(INTAKE_SCRIPT_DIR))

from run_stage00_intake_turn_codex_flow import main as run_stage00_intake_turn_codex_flow_main  # noqa: E402
from stage00_intake_common import canonical_question_block, load_or_create_state  # noqa: E402


def default_state_path() -> Path:
    return Path(".video_project/intake/intake_state.json").resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-json", default=str(default_state_path()), help="Path to intake_state.json")
    parser.add_argument("--user-reply", default="", help="Raw user reply for the current Stage 00 turn")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary name or path")
    return parser.parse_args(argv)


def print_current_prompt(state_path: Path) -> int:
    state = load_or_create_state(state_path)
    status = str(state.get("status") or "")
    print(f"PIPELINE_STAGE00_STATE: {status or 'collecting'}")
    if status == "locked":
        print("PIPELINE_STAGE00_LOCKED")
        return 0
    prompt_text = str(state.get("next_prompt_text") or "")
    if not prompt_text:
        question_key = str(state.get("current_question_key") or "idea")
        prompt_text = canonical_question_block(question_key)
    print(f"PIPELINE_STAGE00_CURRENT_QUESTION_KEY: {state.get('current_question_key') or ''}")
    print("PIPELINE_STAGE00_PROMPT_BEGIN")
    print(prompt_text)
    print("PIPELINE_STAGE00_PROMPT_END")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state_path = Path(args.state_json).resolve()
    if not str(args.user_reply or "").strip():
        return print_current_prompt(state_path)
    return run_stage00_intake_turn_codex_flow_main([
        str(state_path),
        "--user-reply",
        str(args.user_reply),
        "--codex-bin",
        str(args.codex_bin),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
