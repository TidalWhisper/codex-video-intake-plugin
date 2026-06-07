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
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from build_stage00_intake_prompt_packet import build_packet  # noqa: E402
from pipeline_core.codex_flow import (  # noqa: E402
    build_generation_request,
    build_repair_request,
    cleanup_failure_artifacts,
    resolve_codex_bin,
    run_codex_exec,
    write_codex_output_json,
)
from stage00_intake_common import load_or_create_state, references_dir  # noqa: E402
from write_stage00_intake_state import write_state  # noqa: E402


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_stage00_intake_llm_output(
    *,
    request_text: str,
    schema_path: Path,
    llm_output_path: Path,
    output_message_path: Path,
    codex_bin: str,
    cwd: Path,
) -> dict[str, Any]:
    run_codex_exec(
        request_text,
        schema_path,
        output_message_path,
        codex_bin=codex_bin,
        cwd=cwd,
        timeout_seconds=300,
        max_transient_retries=4,
    )
    return write_codex_output_json(output_message_path, llm_output_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_json", help="Path to intake_state.json")
    parser.add_argument("--user-reply", required=True, help="Raw user reply for this Stage 00 turn")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary name or path")
    parser.add_argument("--max-repair-attempts", type=int, default=2, help="How many automatic repair attempts to allow after the first generation fails validation")
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
    repair_prompt_path = refs / "stage00_intake_repair_prompt.md"
    llm_output_path = intake_dir / "stage00_intake_turn_llm_output.json"
    generation_last_message_path = intake_dir / "stage00_intake_codex_last_message.txt"
    generation_request_path = intake_dir / "stage00_intake_codex_generation_request.txt"
    resolved_codex_bin = resolve_codex_bin(args.codex_bin)

    generation_request = build_generation_request(
        stage_label="Stage 00-A",
        generation_prompt_path=generation_prompt_path,
        schema_path=schema_path,
        prompt_packet_path=prompt_packet_path,
    )
    generation_request_path.write_text(generation_request, encoding="utf-8")
    generate_stage00_intake_llm_output(
        request_text=generation_request,
        schema_path=schema_path,
        llm_output_path=llm_output_path,
        output_message_path=generation_last_message_path,
        codex_bin=resolved_codex_bin,
        cwd=PLUGIN_ROOT,
    )

    total_attempts = max(0, int(args.max_repair_attempts))
    for attempt_index in range(total_attempts + 1):
        exit_code = write_state_main(state_path, llm_output_path)
        if exit_code == 0:
            cleanup_failure_artifacts(intake_dir, ["stage00_intake_validation_errors.json", "stage00_intake_repair_packet.json"])
            print(f"STAGE00_INTAKE_CODEX_FLOW_COMPLETED: {state_path}")
            return 0
        if attempt_index >= total_attempts:
            return exit_code

        repair_packet_path = intake_dir / "stage00_intake_repair_packet.json"
        if not repair_packet_path.exists():
            print(
                "ERROR: Stage 00-A validation failed but no repair packet was created for automatic retry.",
                file=sys.stderr,
            )
            return exit_code

        repair_request_path = intake_dir / f"stage00_intake_codex_repair_request_attempt_{attempt_index + 1}.txt"
        repair_last_message_path = intake_dir / f"stage00_intake_codex_repair_last_message_attempt_{attempt_index + 1}.txt"
        repair_request = build_repair_request(
            stage_label="Stage 00-A",
            repair_prompt_path=repair_prompt_path,
            schema_path=schema_path,
            prompt_packet_path=prompt_packet_path,
            repair_packet_path=repair_packet_path,
            current_llm_output_path=llm_output_path,
        )
        repair_request_path.write_text(repair_request, encoding="utf-8")
        generate_stage00_intake_llm_output(
            request_text=repair_request,
            schema_path=schema_path,
            llm_output_path=llm_output_path,
            output_message_path=repair_last_message_path,
            codex_bin=resolved_codex_bin,
            cwd=PLUGIN_ROOT,
        )

    return 1


def write_state_main(state_path: Path, llm_output_path: Path) -> int:
    llm_output = json.loads(llm_output_path.read_text(encoding="utf-8-sig"))
    try:
        write_state(state_path, llm_output, state_path)
    except SystemExit as exc:
        return int(str(exc)) if str(exc).isdigit() else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
