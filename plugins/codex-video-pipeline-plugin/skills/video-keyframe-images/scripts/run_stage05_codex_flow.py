#!/usr/bin/env python3
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

from build_stage05_prompt_packet import build_packet, ensure_stage04_keyframe_prompts, load_json  # noqa: E402
from pipeline_core.codex_flow import (  # noqa: E402
    build_generation_request,
    build_repair_request,
    cleanup_failure_artifacts,
    resolve_codex_bin,
    run_codex_exec,
    write_codex_output_json,
)
from build_stage04_prompt_packet import ensure_locked_brief  # noqa: E402


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_stage05_contract(
    *,
    request_text: str,
    schema_path: Path,
    llm_output_path: Path,
    output_message_path: Path,
    codex_bin: str,
    cwd: Path,
) -> dict[str, Any]:
    try:
        run_codex_exec(
            request_text,
            schema_path,
            output_message_path,
            codex_bin=codex_bin,
            cwd=cwd,
            timeout_seconds=600,
            max_transient_retries=4,
        )
    except SystemExit as exc:
        if output_message_path.exists():
            raw = output_message_path.read_text(encoding="utf-8").strip()
            if raw:
                try:
                    return write_codex_output_json(output_message_path, llm_output_path)
                except SystemExit:
                    pass
        raise exc
    return write_codex_output_json(output_message_path, llm_output_path)


def validate_stage05_contract(contract: dict[str, Any], keyframe_prompts: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(contract.get("mode") or "").strip() != "codex_contract":
        errors.append("mode must be codex_contract")
    self_check = contract.get("self_check") if isinstance(contract.get("self_check"), dict) else {}
    for key in [
        "matches_stage04_prompts",
        "preserves_reference_guided_mainline",
        "python_can_execute_mechanically",
    ]:
        if self_check.get(key) is not True:
            errors.append(f"self_check.{key} must be true")
    defaults = contract.get("defaults") if isinstance(contract.get("defaults"), dict) else {}
    if str(defaults.get("prompt_composition_mode") or "").strip() != "codex_contract":
        errors.append("defaults.prompt_composition_mode must be codex_contract")
    if str(defaults.get("stage05_mode") or "").strip() != "reference_guided_storyboard":
        errors.append("defaults.stage05_mode must be reference_guided_storyboard")
    if str(defaults.get("comfyui_control_mode") or "").strip() != "reference_guided":
        errors.append("defaults.comfyui_control_mode must be reference_guided")
    provider_strategy = contract.get("provider_strategy") if isinstance(contract.get("provider_strategy"), dict) else {}
    if not str(provider_strategy.get("primary") or "").strip():
        errors.append("provider_strategy.primary must not be blank")
    bootstrap = contract.get("bootstrap") if isinstance(contract.get("bootstrap"), dict) else {}
    if str(bootstrap.get("semantic_source") or "").strip() != "codex_contract":
        errors.append("bootstrap.semantic_source must be codex_contract")
    if not str(bootstrap.get("target_reference_image_path") or "").strip():
        errors.append("bootstrap.target_reference_image_path must not be blank")
    if not str(bootstrap.get("provider_prompt") or "").strip():
        errors.append("bootstrap.provider_prompt must not be blank")

    expected_shot_ids = {
        str(item.get("shot_id") or "").strip()
        for item in (keyframe_prompts.get("shot_prompts") or [])
        if isinstance(item, dict) and str(item.get("shot_id") or "").strip()
    }
    jobs = [item for item in (contract.get("jobs") or []) if isinstance(item, dict)]
    seen_roles: dict[str, set[str]] = {}
    for index, job in enumerate(jobs):
        shot_id = str(job.get("shot_id") or "").strip()
        frame_role = str(job.get("frame_role") or "").strip().lower()
        if shot_id not in expected_shot_ids:
            errors.append(f"jobs[{index}].shot_id references unknown Stage04 shot: {shot_id}")
            continue
        if frame_role not in {"start", "mid", "end"}:
            errors.append(f"jobs[{index}].frame_role must be start|mid|end")
            continue
        seen_roles.setdefault(shot_id, set()).add(frame_role)
        if str(job.get("semantic_source") or "").strip() != "codex_contract":
            errors.append(f"jobs[{index}].semantic_source must be codex_contract")
        if not str(job.get("provider_prompt") or "").strip():
            errors.append(f"jobs[{index}].provider_prompt must not be blank")
        if not isinstance(job.get("reference_images"), list):
            errors.append(f"jobs[{index}].reference_images must be a list")
        if "review" not in job or not isinstance(job.get("review"), dict):
            errors.append(f"jobs[{index}].review must be an object")
            continue
        if "repair" not in job or not isinstance(job.get("repair"), dict):
            errors.append(f"jobs[{index}].repair must be an object")
            continue
        review = job.get("review") if isinstance(job.get("review"), dict) else {}
        repair = job.get("repair") if isinstance(job.get("repair"), dict) else {}
        if str(review.get("semantic_source") or "").strip() != "codex_contract":
            errors.append(f"jobs[{index}].review.semantic_source must be codex_contract")
        if "requires_manual_review" not in review:
            errors.append(f"jobs[{index}].review.requires_manual_review must be provided")
        if not isinstance(review.get("creator_repair_suggestions"), list):
            errors.append(f"jobs[{index}].review.creator_repair_suggestions must be a list")
        if not isinstance(repair.get("creator_repair_suggestions"), list):
            errors.append(f"jobs[{index}].repair.creator_repair_suggestions must be a list")
        if not isinstance(repair.get("repair_prompt_sections"), list):
            errors.append(f"jobs[{index}].repair.repair_prompt_sections must be a list")
        if not isinstance(repair.get("repair_negative_hints"), list):
            errors.append(f"jobs[{index}].repair.repair_negative_hints must be a list")
        review_card = job.get("review_card")
        if review_card is not None and not isinstance(review_card, dict):
            errors.append(f"jobs[{index}].review_card must be an object when provided")
    for shot_id in sorted(expected_shot_ids):
        roles = seen_roles.get(shot_id, set())
        if "start" not in roles or "end" not in roles:
            errors.append(f"shot {shot_id} must include explicit start and end jobs in Stage05 contract")
    return errors


def build_repair_packet(
    *,
    prompt_packet_path: Path,
    current_contract_path: Path,
    validation_errors: list[str],
) -> dict[str, Any]:
    return {
        "packet_version": "0.1.0",
        "source_prompt_packet": str(prompt_packet_path.resolve()).replace("\\", "/"),
        "current_contract_path": str(current_contract_path.resolve()).replace("\\", "/"),
        "validation_errors": list(validation_errors),
        "repair_goal": "Return a full replacement Stage05 semantic contract that removes the missing or invalid semantics so Python can execute mechanically.",
    }


def attach_contract_to_keyframe_prompts(
    keyframe_path: Path,
    keyframe_prompts: dict[str, Any],
    contract: dict[str, Any],
    *,
    llm_output_path: Path,
) -> None:
    updated = dict(keyframe_prompts)
    updated["stage05_semantic_contract"] = contract
    updated["stage05_semantic_contract_source"] = str(llm_output_path.resolve()).replace("\\", "/")
    updated["stage05_semantic_contract_summary"] = {
        "mode": str(contract.get("mode") or "").strip() or "codex_contract",
        "source": str(contract.get("source") or "").strip() or "stage05_codex_flow",
        "job_count": len([item for item in (contract.get("jobs") or []) if isinstance(item, dict)]),
    }
    write_json(keyframe_path, updated)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("locked_brief")
    parser.add_argument("keyframe_prompts_json")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--max-repair-attempts", type=int, default=1)
    args = parser.parse_args(argv)

    brief_path = Path(args.locked_brief).resolve()
    keyframe_path = Path(args.keyframe_prompts_json).resolve()
    out_dir = keyframe_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    brief = load_json(brief_path)
    keyframe_prompts = load_json(keyframe_path)
    ensure_locked_brief(brief)
    ensure_stage04_keyframe_prompts(keyframe_prompts)

    prompt_packet_path = out_dir / "stage05_prompt_packet.json"
    prompt_packet = build_packet(brief, keyframe_prompts, brief_path=brief_path, keyframe_path=keyframe_path)
    write_json(prompt_packet_path, prompt_packet)

    references_dir = SCRIPT_DIR.parent / "references"
    schema_path = references_dir / "stage05_semantic_contract.schema.json"
    generation_prompt_path = references_dir / "stage05_codex_generation_prompt.md"
    repair_prompt_path = references_dir / "stage05_codex_repair_prompt.md"

    llm_output_path = out_dir / "stage05_semantic_contract.json"
    generation_last_message_path = out_dir / "stage05_codex_last_message.txt"
    generation_request_path = out_dir / "stage05_codex_generation_request.txt"
    resolved_codex_bin = resolve_codex_bin(args.codex_bin)
    generation_request = build_generation_request(
        stage_label="Stage 05",
        generation_prompt_path=generation_prompt_path,
        schema_path=schema_path,
        prompt_packet_path=prompt_packet_path,
    )
    generation_request_path.write_text(generation_request, encoding="utf-8")
    generate_stage05_contract(
        request_text=generation_request,
        schema_path=schema_path,
        llm_output_path=llm_output_path,
        output_message_path=generation_last_message_path,
        codex_bin=resolved_codex_bin,
        cwd=PLUGIN_ROOT,
    )

    total_attempts = max(0, int(args.max_repair_attempts))
    for attempt_index in range(total_attempts + 1):
        contract = load_json(llm_output_path)
        validation_errors = validate_stage05_contract(contract, keyframe_prompts)
        if not validation_errors:
            attach_contract_to_keyframe_prompts(
                keyframe_path,
                keyframe_prompts,
                contract,
                llm_output_path=llm_output_path,
            )
            cleanup_failure_artifacts(out_dir, ["stage05_validation_errors.json", "stage05_repair_packet.json"])
            print(f"STAGE05_CODEX_FLOW_COMPLETED: {llm_output_path}")
            return 0
        write_json(out_dir / "stage05_validation_errors.json", {"errors": validation_errors})
        if attempt_index >= total_attempts:
            break
        repair_packet_path = out_dir / "stage05_repair_packet.json"
        repair_last_message_path = out_dir / f"stage05_codex_repair_last_message_attempt_{attempt_index + 1}.txt"
        repair_request_path = out_dir / f"stage05_codex_repair_request_attempt_{attempt_index + 1}.txt"
        repair_packet = build_repair_packet(
            prompt_packet_path=prompt_packet_path,
            current_contract_path=llm_output_path,
            validation_errors=validation_errors,
        )
        write_json(repair_packet_path, repair_packet)
        repair_request = build_repair_request(
            stage_label="Stage 05",
            repair_prompt_path=repair_prompt_path,
            schema_path=schema_path,
            prompt_packet_path=prompt_packet_path,
            repair_packet_path=repair_packet_path,
            current_llm_output_path=llm_output_path,
        )
        repair_request_path.write_text(repair_request, encoding="utf-8")
        generate_stage05_contract(
            request_text=repair_request,
            schema_path=schema_path,
            llm_output_path=llm_output_path,
            output_message_path=repair_last_message_path,
            codex_bin=resolved_codex_bin,
            cwd=PLUGIN_ROOT,
        )

    print(f"STAGE05_CODEX_FLOW_FAILED: {llm_output_path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
