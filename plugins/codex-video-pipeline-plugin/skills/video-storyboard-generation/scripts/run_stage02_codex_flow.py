#!/usr/bin/env python3
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

from build_stage02_prompt_packet import build_packet, ensure_locked_brief  # noqa: E402
import new_storyboard_template  # noqa: E402
from pipeline_core.codex_flow import (  # noqa: E402
    build_generation_request,
    build_repair_request,
    cleanup_failure_artifacts,
    resolve_codex_bin,
    run_codex_exec,
    write_codex_output_json,
)
from pipeline_core.project_state import load_json_file  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("locked_brief")
    parser.add_argument("script_json")
    parser.add_argument("storyboard_json")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--max-repair-attempts", type=int, default=2)
    args = parser.parse_args(argv)

    brief_path = Path(args.locked_brief).resolve()
    script_path = Path(args.script_json).resolve()
    storyboard_json_path = Path(args.storyboard_json).resolve()
    storyboard_dir = storyboard_json_path.parent
    storyboard_dir.mkdir(parents=True, exist_ok=True)

    brief = load_json(brief_path)
    script = load_json(script_path)
    ensure_locked_brief(brief)

    prompt_packet_path = storyboard_dir / "stage02_prompt_packet.json"
    write_json(prompt_packet_path, build_packet(brief, script, brief_path, script_path))
    resolved_codex_bin = resolve_codex_bin(args.codex_bin)

    references_dir = SCRIPT_DIR.parent / "references"
    schema_path = references_dir / "stage02_llm_output.schema.json"
    generation_prompt_path = references_dir / "stage02_codex_generation_prompt.md"
    repair_prompt_path = references_dir / "stage02_codex_repair_prompt.md"

    llm_output_path = storyboard_dir / "stage02_llm_output.json"
    generation_last_message_path = storyboard_dir / "stage02_codex_last_message.txt"
    generation_request_path = storyboard_dir / "stage02_codex_generation_request.txt"
    generation_request = build_generation_request(
        stage_label="Stage 02",
        generation_prompt_path=generation_prompt_path,
        schema_path=schema_path,
        prompt_packet_path=prompt_packet_path,
    )
    generation_request_path.write_text(generation_request, encoding="utf-8")
    run_codex_exec(generation_request, schema_path, generation_last_message_path, codex_bin=resolved_codex_bin, cwd=REPO_ROOT)
    write_codex_output_json(generation_last_message_path, llm_output_path)

    total_attempts = max(0, int(args.max_repair_attempts))
    for attempt_index in range(total_attempts + 1):
        exit_code = new_storyboard_template.main([
            "new_storyboard_template.py",
            str(brief_path),
            str(script_path),
            str(storyboard_json_path),
        ])
        if exit_code == 0:
            cleanup_failure_artifacts(storyboard_dir, ["stage02_validation_errors.json", "stage02_repair_packet.json"])
            print(f"STAGE02_CODEX_FLOW_COMPLETED: {storyboard_json_path}")
            return 0
        if attempt_index >= total_attempts:
            break
        repair_packet_path = storyboard_dir / "stage02_repair_packet.json"
        if not repair_packet_path.exists():
            break
        repair_last_message_path = storyboard_dir / f"stage02_codex_repair_last_message_attempt_{attempt_index + 1}.txt"
        repair_request_path = storyboard_dir / f"stage02_codex_repair_request_attempt_{attempt_index + 1}.txt"
        repair_request = build_repair_request(
            stage_label="Stage 02",
            repair_prompt_path=repair_prompt_path,
            schema_path=schema_path,
            prompt_packet_path=prompt_packet_path,
            repair_packet_path=repair_packet_path,
            current_llm_output_path=llm_output_path,
        )
        repair_request_path.write_text(repair_request, encoding="utf-8")
        run_codex_exec(repair_request, schema_path, repair_last_message_path, codex_bin=resolved_codex_bin, cwd=REPO_ROOT)
        write_codex_output_json(repair_last_message_path, llm_output_path)

    print(f"STAGE02_CODEX_FLOW_FAILED: {storyboard_json_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
