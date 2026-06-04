#!/usr/bin/env python3
"""Run the Stage 00-B Codex-first brief generation flow end to end."""
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

from build_stage00_brief_prompt_packet import build_packet  # noqa: E402
from pipeline_core.codex_flow import (  # noqa: E402
    cleanup_failure_artifacts,
)
from stage00_local_semantics import build_brief_llm_output  # noqa: E402
from stage00_intake_common import ensure_draft_ready_state, load_or_create_state, references_dir  # noqa: E402
import validate_project_structure as validate_project_structure_module  # noqa: E402
import write_stage00_brief_outputs as write_stage00_brief_outputs_module  # noqa: E402


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def maybe_validate_project_structure(project_dir: Path) -> None:
    manifest_path = project_dir / "project_manifest.json"
    if not manifest_path.exists():
        return
    exit_code = validate_project_structure_module.main([
        "validate_project_structure.py",
        str(project_dir),
    ])
    if exit_code != 0:
        raise SystemExit(exit_code)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("state_json", help="Path to intake_state.json")
    parser.add_argument("draft_json", help="Path to project_brief.draft.json")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary name or path")
    parser.add_argument("--max-repair-attempts", type=int, default=2, help="How many automatic repair attempts to allow after the first generation fails validation")
    args = parser.parse_args(argv)

    state_path = Path(args.state_json).resolve()
    draft_json_path = Path(args.draft_json).resolve()
    intake_dir = draft_json_path.parent
    intake_dir.mkdir(parents=True, exist_ok=True)

    state = load_or_create_state(state_path)
    ensure_draft_ready_state(state)
    maybe_validate_project_structure(Path(str(state.get("project_dir") or draft_json_path.parents[1])))

    prompt_packet_path = intake_dir / "stage00_brief_prompt_packet.json"
    prompt_packet = build_packet(state, state_path, draft_json_path)
    write_json(prompt_packet_path, prompt_packet)

    refs = references_dir()
    llm_output_path = intake_dir / "stage00_brief_llm_output.json"
    generation_last_message_path = intake_dir / "stage00_brief_codex_last_message.txt"
    generation_request_path = intake_dir / "stage00_brief_codex_generation_request.txt"

    generation_request = (
        "STAGE00_LOCAL_EXECUTION_MODE\n"
        "Prompt packet preserved for audit, but Stage 00-B brief output is generated locally "
        "from validated intake state to avoid recursive Codex CLI deadlocks.\n"
        f"Prompt packet: {str(prompt_packet_path).replace(chr(92), '/')}\n"
        f"Schema reference: {str((refs / 'stage00_brief_llm_output.schema.json')).replace(chr(92), '/')}\n"
    )
    generation_request_path.write_text(generation_request, encoding="utf-8")
    generation_last_message_path.write_text("STAGE00_LOCAL_EXECUTION_MODE\n", encoding="utf-8")
    llm_output = build_brief_llm_output(state)
    llm_output_path.write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    exit_code = write_stage00_brief_outputs_module.main([
        "write_stage00_brief_outputs.py",
        str(state_path),
        str(llm_output_path),
        str(draft_json_path),
    ])
    if exit_code == 0:
        cleanup_failure_artifacts(intake_dir, ["stage00_brief_validation_errors.json", "stage00_brief_repair_packet.json"])
        print(f"STAGE00_BRIEF_CODEX_FLOW_COMPLETED: {draft_json_path}")
        return 0
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
