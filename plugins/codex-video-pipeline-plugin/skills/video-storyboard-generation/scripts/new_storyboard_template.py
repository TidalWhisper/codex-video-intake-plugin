#!/usr/bin/env python3
"""Create a Stage 02 storyboard draft from Codex structured output."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.project_state import load_json_file, update_project_manifest_for_stage  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage  # noqa: E402
from pipeline_core.codex_flow import structured_validation_errors  # noqa: E402
import validate_storyboard as validate_storyboard_module  # noqa: E402
from build_stage02_prompt_packet import build_packet, ensure_locked_brief  # noqa: E402
from build_stage02_repair_packet import build_repair_packet  # noqa: E402
from write_stage02_outputs import write_stage02_outputs  # noqa: E402


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    llm_output_override: Path | None = None
    filtered: list[str] = []
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--allow-beyond-requested-scope":
            idx += 1
            continue
        if arg == "--llm-output":
            if idx + 1 >= len(argv):
                print("ERROR: --llm-output requires a path", file=sys.stderr)
                return 2
            llm_output_override = Path(argv[idx + 1])
            idx += 2
            continue
        filtered.append(arg)
        idx += 1
    argv = filtered
    if len(argv) != 4:
        print("Usage: python new_storyboard_template.py [--llm-output <stage02_llm_output.json>] <locked_brief.json> <script.json> <storyboard.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    out_path = Path(argv[3])
    brief = load_json(brief_path)
    script = load_json(script_path)
    ensure_locked_brief(brief)
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_02", compiled):
        print("ERROR: requested output scope does not allow Stage 02. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        print("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_packet_path = out_path.parent / "stage02_prompt_packet.json"
    write_json(prompt_packet_path, build_packet(brief, script, brief_path, script_path))

    llm_output_path = llm_output_override or (out_path.parent / "stage02_llm_output.json")
    if not llm_output_path.exists():
        print(
            f"ERROR: missing Stage 02 Codex structured output: {llm_output_path}. "
            "Generate stage02_llm_output.json from stage02_prompt_packet.json first.",
            file=sys.stderr,
        )
        return 1

    llm_output = load_json(llm_output_path)
    try:
        storyboard_payload = write_stage02_outputs(brief, script, llm_output, brief_path, script_path, llm_output_path, out_path)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    ok, errors, warnings = validate_storyboard_module.validate(storyboard_payload, mode="final")
    if not ok:
        validation_errors = structured_validation_errors(errors)
        validation_errors_path = out_path.parent / "stage02_validation_errors.json"
        write_json(validation_errors_path, {"errors": validation_errors})
        repair_packet = build_repair_packet(brief, script, storyboard_payload, brief_path, script_path, out_path, validation_errors)
        repair_packet_path = out_path.parent / "stage02_repair_packet.json"
        write_json(repair_packet_path, repair_packet)
        print(f"STORYBOARD VALIDATION FAILED: {out_path}", file=sys.stderr)
        print(f"STAGE02_REPAIR_PACKET_CREATED: {repair_packet_path}", file=sys.stderr)
        return 1

    update_project_manifest_for_stage(
        out_path,
        current_stage="STAGE_02_STORYBOARD_GENERATION",
        allowed_next_stage=None,
        flags={"storyboard_confirmed": False},
        status="active",
    )
    if warnings:
        for warning in warnings:
            print(f"WARNING: {warning}")
    print(f"STAGE02_STORYBOARD_CREATED: {out_path}")
    print(f"STAGE02_PROMPT_PACKET_CREATED: {prompt_packet_path}")
    print(f"STAGE02_LLM_OUTPUT_USED: {llm_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
