#!/usr/bin/env python3
"""Run the Stage 00-A Codex-first intake turn flow."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from build_stage00_intake_prompt_packet import build_packet  # noqa: E402
from pipeline_core.codex_flow import (  # noqa: E402
    build_generation_request,
)
from stage00_local_semantics import evaluate_intake_turn  # noqa: E402
from stage00_intake_common import load_or_create_state, references_dir  # noqa: E402
from write_stage00_intake_state import write_state  # noqa: E402


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_json", help="Path to intake_state.json")
    parser.add_argument("--user-reply", required=True, help="Raw user reply for this Stage 00 turn")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary name or path")
    args = parser.parse_args(argv)

    state_path = Path(args.state_json).resolve()
    intake_dir = state_path.parent
    intake_dir.mkdir(parents=True, exist_ok=True)
    state = load_or_create_state(state_path)

    prompt_packet_path = intake_dir / "stage00_intake_prompt_packet.json"
    prompt_packet = build_packet(state, state_path, args.user_reply)
    write_json(prompt_packet_path, prompt_packet)

    refs = references_dir()
    schema_path = refs / "stage00_intake_turn_output.schema.json"
    generation_prompt_path = refs / "stage00_intake_generation_prompt.md"
    llm_output_path = intake_dir / "stage00_intake_turn_llm_output.json"
    generation_last_message_path = intake_dir / "stage00_intake_codex_last_message.txt"
    generation_request_path = intake_dir / "stage00_intake_codex_generation_request.txt"

    generation_request = build_generation_request(
        stage_label="Stage 00-A",
        generation_prompt_path=generation_prompt_path,
        schema_path=schema_path,
        prompt_packet_path=prompt_packet_path,
    )
    generation_request_path.write_text(generation_request, encoding="utf-8")
    # Stage 00 intake is intentionally executed locally to avoid recursive
    # Codex CLI deadlocks inside the desktop environment while preserving the
    # same packet/output artifact chain for inspection and validation.
    generation_last_message_path.write_text("STAGE00_LOCAL_EXECUTION_MODE\n", encoding="utf-8")
    llm_output = evaluate_intake_turn(state, args.user_reply)
    llm_output_path.write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    write_state(state_path, llm_output, state_path)

    print(f"STAGE00_INTAKE_CODEX_FLOW_COMPLETED: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
