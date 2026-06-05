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

from build_stage04_prompt_packet import build_packet, ensure_locked_brief  # noqa: E402
import new_keyframe_prompts_template  # noqa: E402
from pipeline_core.codex_flow import (  # noqa: E402
    build_generation_request,
    build_repair_request,
    cleanup_failure_artifacts,
    run_codex_exec,
    resolve_codex_bin,
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


def generate_stage04_llm_output(
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
    parser.add_argument("locked_brief")
    parser.add_argument("script_json")
    parser.add_argument("storyboard_json")
    parser.add_argument("character_bible_json")
    parser.add_argument("keyframe_prompts_json")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--max-repair-attempts", type=int, default=2)
    args = parser.parse_args(argv)

    brief_path = Path(args.locked_brief).resolve()
    script_path = Path(args.script_json).resolve()
    storyboard_path = Path(args.storyboard_json).resolve()
    character_path = Path(args.character_bible_json).resolve()
    out_path = Path(args.keyframe_prompts_json).resolve()
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    character_bible = load_json(character_path)
    ensure_locked_brief(brief)

    prompt_packet_path = out_dir / "stage04_prompt_packet.json"
    prompt_packet = build_packet(brief, script, storyboard, character_bible, brief_path, script_path, storyboard_path, character_path)
    write_json(prompt_packet_path, prompt_packet)

    references_dir = SCRIPT_DIR.parent / "references"
    schema_path = references_dir / "stage04_llm_output.schema.json"
    generation_prompt_path = references_dir / "stage04_codex_generation_prompt.md"
    repair_prompt_path = references_dir / "stage04_codex_repair_prompt.md"

    llm_output_path = out_dir / "stage04_llm_output.json"
    generation_last_message_path = out_dir / "stage04_codex_last_message.txt"
    generation_request_path = out_dir / "stage04_codex_generation_request.txt"
    resolved_codex_bin = resolve_codex_bin(args.codex_bin)
    generation_request = build_generation_request(
        stage_label="Stage 04",
        generation_prompt_path=generation_prompt_path,
        schema_path=schema_path,
        prompt_packet_path=prompt_packet_path,
    )
    generation_request_path.write_text(generation_request, encoding="utf-8")
    generate_stage04_llm_output(
        request_text=generation_request,
        schema_path=schema_path,
        llm_output_path=llm_output_path,
        output_message_path=generation_last_message_path,
        codex_bin=resolved_codex_bin,
        cwd=REPO_ROOT,
    )

    total_attempts = max(0, int(args.max_repair_attempts))
    for attempt_index in range(total_attempts + 1):
        exit_code = new_keyframe_prompts_template.main([
            "new_keyframe_prompts_template.py",
            str(brief_path),
            str(script_path),
            str(storyboard_path),
            str(character_path),
            str(out_path),
        ])
        if exit_code == 0:
            cleanup_failure_artifacts(out_dir, ["stage04_validation_errors.json", "stage04_repair_packet.json"])
            print(f"STAGE04_CODEX_FLOW_COMPLETED: {out_path}")
            return 0
        if attempt_index >= total_attempts:
            break
        repair_packet_path = out_dir / "stage04_repair_packet.json"
        if not repair_packet_path.exists():
            break
        repair_last_message_path = out_dir / f"stage04_codex_repair_last_message_attempt_{attempt_index + 1}.txt"
        repair_request_path = out_dir / f"stage04_codex_repair_request_attempt_{attempt_index + 1}.txt"
        repair_request = build_repair_request(
            stage_label="Stage 04",
            repair_prompt_path=repair_prompt_path,
            schema_path=schema_path,
            prompt_packet_path=prompt_packet_path,
            repair_packet_path=repair_packet_path,
            current_llm_output_path=llm_output_path,
        )
        repair_request_path.write_text(repair_request, encoding="utf-8")
        generate_stage04_llm_output(
            request_text=repair_request,
            schema_path=schema_path,
            llm_output_path=llm_output_path,
            output_message_path=repair_last_message_path,
            codex_bin=resolved_codex_bin,
            cwd=REPO_ROOT,
        )

    print(f"STAGE04_CODEX_FLOW_FAILED: {out_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
