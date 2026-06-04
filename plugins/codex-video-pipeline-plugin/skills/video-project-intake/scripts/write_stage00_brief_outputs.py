#!/usr/bin/env python3
"""Write official Stage 00 draft brief outputs from Codex structured output."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from build_stage00_brief_repair_packet import build_repair_packet  # noqa: E402
from stage00_intake_common import empty_brief_normalized, ensure_draft_ready_state, load_json, load_or_create_state, utc_now  # noqa: E402
import validate_project_brief as validate_project_brief_module  # noqa: E402
from pipeline_core.codex_flow import structured_validation_errors  # noqa: E402

REQUIRED_KEYS = [
    "source",
    "user_answers",
    "normalized",
    "required_fields_complete",
    "missing_required_fields",
    "brief_confirmation_summary",
]

SUMMARY_KEYS = [
    "idea",
    "target_duration",
    "genre",
    "style",
    "visual_spec",
    "characters",
    "voice",
    "music",
    "final_output",
]


def ensure_shape(data: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        raise SystemExit(f"ERROR: missing required keys in Stage 00 brief llm output: {', '.join(missing)}")
    summary = data.get("brief_confirmation_summary")
    if not isinstance(summary, dict):
        raise SystemExit("ERROR: brief_confirmation_summary must be an object")
    missing_summary = [key for key in SUMMARY_KEYS if key not in summary]
    if missing_summary:
        raise SystemExit(
            "ERROR: Stage 00 brief llm output is missing summary keys: "
            + ", ".join(missing_summary)
        )


def build_draft_payload(state: dict[str, Any], llm_output: dict[str, Any]) -> dict[str, Any]:
    normalized = empty_brief_normalized()
    normalized.update(dict(llm_output.get("normalized") or {}))
    return {
        "schema_version": "0.3.0",
        "project_id": str(state.get("project_id") or ""),
        "project_dir": str(state.get("project_dir") or ""),
        "stage": "STAGE_00_INTAKE",
        "status": "draft",
        "confirmed_by_user": False,
        "required_fields_complete": bool(llm_output.get("required_fields_complete")),
        "missing_required_fields": list(llm_output.get("missing_required_fields") or []),
        "source": str(llm_output.get("source") or "Created from user-supplied Stage 00 intake answers."),
        "user_answers": dict(llm_output.get("user_answers") or {}),
        "normalized": normalized,
        "allowed_next_stage": None,
        "created_at": utc_now(),
    }


def render_confirmation_summary(summary: dict[str, Any], project_dir: str) -> str:
    lines = [
        "9 项信息已收集完成。",
        "",
        f"项目文件夹：{project_dir}",
        "",
        "请确认项目 Brief：",
        f"1. 故事想法：{summary.get('idea')}",
        f"2. 目标视频时长：{summary.get('target_duration')}",
        f"3. 视频题材：{summary.get('genre')}",
        f"4. 视频风格：{summary.get('style')}",
        f"5. 画面规格：{summary.get('visual_spec')}",
        f"6. 固定主角/人物：{summary.get('characters')}",
        f"7. 配音：{summary.get('voice')}",
        f"8. 背景音乐：{summary.get('music')}",
        f"9. 最终输出：{summary.get('final_output')}",
    ]
    return "\n".join(lines) + "\n"


def write_stage00_brief_outputs(
    state: dict[str, Any],
    llm_output: dict[str, Any],
    state_path: Path,
    llm_output_path: Path,
    draft_json_path: Path,
) -> dict[str, Any]:
    ensure_draft_ready_state(state)
    ensure_shape(llm_output)
    draft_payload = build_draft_payload(state, llm_output)
    intake_dir = draft_json_path.parent
    intake_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = intake_dir / "stage00_brief_llm_output.json"
    raw_output_path.write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    draft_json_path.write_text(json.dumps(draft_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = dict(llm_output.get("brief_confirmation_summary") or {})
    summary_json_path = intake_dir / "stage00_brief_confirmation_summary.json"
    summary_md_path = intake_dir / "stage00_brief_confirmation_summary.md"
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text(
        render_confirmation_summary(summary, str(state.get("project_dir") or "")),
        encoding="utf-8",
    )

    ok, errors, warnings = validate_project_brief_module.validate(draft_payload, draft_json_path)
    if not ok:
        validation_errors = structured_validation_errors(errors)
        validation_errors_path = intake_dir / "stage00_brief_validation_errors.json"
        validation_errors_path.write_text(json.dumps({"errors": validation_errors}, ensure_ascii=False, indent=2), encoding="utf-8")
        repair_packet = build_repair_packet(state, draft_payload, state_path, draft_json_path, validation_errors)
        repair_packet_path = intake_dir / "stage00_brief_repair_packet.json"
        repair_packet_path.write_text(json.dumps(repair_packet, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"STAGE00_BRIEF_VALIDATION_FAILED: {draft_json_path}", file=sys.stderr)
        print(f"STAGE00_BRIEF_REPAIR_PACKET_CREATED: {repair_packet_path}", file=sys.stderr)
        raise SystemExit(1)

    for warning in warnings:
        print(f"WARNING: {warning}")
    return draft_payload


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "Usage: python write_stage00_brief_outputs.py <intake_state.json> <stage00_brief_llm_output.json> <project_brief.draft.json>",
            file=sys.stderr,
        )
        return 2

    state_path = Path(argv[1])
    llm_output_path = Path(argv[2])
    draft_json_path = Path(argv[3])
    state = load_or_create_state(state_path)
    llm_output = load_json(llm_output_path)
    try:
        write_stage00_brief_outputs(state, llm_output, state_path, llm_output_path, draft_json_path)
    except SystemExit as exc:
        return int(str(exc)) if str(exc).isdigit() else 1
    print(f"STAGE00_BRIEF_OUTPUTS_WRITTEN: {draft_json_path.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
