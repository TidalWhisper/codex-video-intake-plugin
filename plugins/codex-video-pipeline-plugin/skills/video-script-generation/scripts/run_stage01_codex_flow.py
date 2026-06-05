#!/usr/bin/env python3
"""Run the Stage 01 Codex-first generation flow end to end.

Flow:
1. Build `stage01_prompt_packet.json`
2. Generate `stage01_llm_output.json` through Codex structured output
3. Render official Stage 01 outputs through `new_script_template.py`
4. If validation fails, build a repair packet and request a corrected full
   structured output from Codex again
"""
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

from build_stage01_prompt_packet import build_packet, ensure_locked_brief  # noqa: E402
import new_script_template  # noqa: E402
from pipeline_core.codex_flow import (  # noqa: E402
    build_generation_request,
    build_repair_request,
    cleanup_failure_artifacts,
    run_codex_exec,
    resolve_codex_bin,
    write_codex_output_json,
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_stage01_llm_output(
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
    )
    return write_codex_output_json(output_message_path, llm_output_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("locked_brief", help="Path to project_brief.locked.json")
    parser.add_argument("script_json", help="Path to 01_script/script.json")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary name or path")
    parser.add_argument("--max-repair-attempts", type=int, default=2, help="How many automatic repair attempts to allow after the first generation fails validation")
    args = parser.parse_args(argv)

    brief_path = Path(args.locked_brief).resolve()
    script_json_path = Path(args.script_json).resolve()
    script_dir = script_json_path.parent
    script_dir.mkdir(parents=True, exist_ok=True)

    brief = load_json(brief_path)
    ensure_locked_brief(brief)

    prompt_packet_path = script_dir / "stage01_prompt_packet.json"
    prompt_packet = build_packet(brief, brief_path)
    write_json(prompt_packet_path, prompt_packet)

    references_dir = SCRIPT_DIR.parent / "references"
    schema_path = references_dir / "stage01_llm_output.schema.json"
    generation_prompt_path = references_dir / "stage01_codex_generation_prompt.md"
    repair_prompt_path = references_dir / "stage01_codex_repair_prompt.md"

    llm_output_path = script_dir / "stage01_llm_output.json"
    generation_last_message_path = script_dir / "stage01_codex_last_message.txt"
    generation_request_path = script_dir / "stage01_codex_generation_request.txt"
    resolved_codex_bin = resolve_codex_bin(args.codex_bin)

    generation_request = build_generation_request(
        stage_label="Stage 01",
        generation_prompt_path=generation_prompt_path,
        schema_path=schema_path,
        prompt_packet_path=prompt_packet_path,
    )
    generation_request_path.write_text(generation_request, encoding="utf-8")
    generate_stage01_llm_output(
        request_text=generation_request,
        schema_path=schema_path,
        llm_output_path=llm_output_path,
        output_message_path=generation_last_message_path,
        codex_bin=resolved_codex_bin,
        cwd=REPO_ROOT,
    )

    total_attempts = max(0, int(args.max_repair_attempts))
    for attempt_index in range(total_attempts + 1):
        exit_code = new_script_template.main([
            "new_script_template.py",
            str(brief_path),
            str(script_json_path),
        ])
        if exit_code == 0:
            cleanup_failure_artifacts(script_dir, ["stage01_validation_errors.json", "stage01_repair_packet.json"])
            print(f"STAGE01_CODEX_FLOW_COMPLETED: {script_json_path}")
            return 0
        if attempt_index >= total_attempts:
            return exit_code

        repair_packet_path = script_dir / "stage01_repair_packet.json"
        if not repair_packet_path.exists():
            print(
                "ERROR: Stage 01 validation failed but no repair packet was created for automatic retry.",
                file=sys.stderr,
            )
            return exit_code

        repair_request_path = script_dir / f"stage01_codex_repair_request_attempt_{attempt_index + 1}.txt"
        repair_last_message_path = script_dir / f"stage01_codex_repair_last_message_attempt_{attempt_index + 1}.txt"
        repair_request = build_repair_request(
            stage_label="Stage 01",
            repair_prompt_path=repair_prompt_path,
            schema_path=schema_path,
            prompt_packet_path=prompt_packet_path,
            repair_packet_path=repair_packet_path,
            current_llm_output_path=llm_output_path,
        )
        repair_request_path.write_text(repair_request, encoding="utf-8")
        generate_stage01_llm_output(
            request_text=repair_request,
            schema_path=schema_path,
            llm_output_path=llm_output_path,
            output_message_path=repair_last_message_path,
            codex_bin=resolved_codex_bin,
            cwd=REPO_ROOT,
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
