#!/usr/bin/env python3
"""Build a deterministic Stage 00-B repair packet."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from stage00_intake_common import load_json, load_or_create_state  # noqa: E402


def normalize_failed_checks(data: Any) -> list[dict[str, str]]:
    if isinstance(data, dict) and isinstance(data.get("errors"), list):
        data = data["errors"]
    if not isinstance(data, list):
        raise SystemExit("ERROR: validation errors input must be a list or an object with an errors list")
    normalized: list[dict[str, str]] = []
    for idx, item in enumerate(data):
        if isinstance(item, dict):
            normalized.append({
                "code": str(item.get("code") or f"error_{idx + 1}"),
                "path": str(item.get("path") or ""),
                "message": str(item.get("message") or item.get("detail") or ""),
            })
        else:
            normalized.append({
                "code": f"error_{idx + 1}",
                "path": "",
                "message": str(item),
            })
    return normalized


def derive_allowed_edits(failed_checks: list[dict[str, str]]) -> list[str]:
    paths: list[str] = []
    for item in failed_checks:
        path = str(item.get("path") or "").strip()
        if path and path not in paths:
            paths.append(path)
    return paths or ["field-level fixes only"]


def build_repair_packet(
    state: dict[str, Any],
    draft: dict[str, Any],
    state_path: Path,
    draft_path: Path,
    failed_checks: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "packet_version": "0.1.0",
        "project_id": str(draft.get("project_id") or state.get("project_id") or ""),
        "source_state": str(state_path.resolve()).replace("\\", "/"),
        "source_draft": str(draft_path.resolve()).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "failed_checks": failed_checks,
        "allowed_edits": derive_allowed_edits(failed_checks),
        "forbidden_edits": [
            "Do not rewrite the entire brief in a different concept.",
            "Do not change project_id, project_dir, stage, status, confirmed_by_user, or allowed_next_stage.",
            "Do not change stable normalized values unless a failed validation check explicitly requires it.",
        ],
        "current_draft": draft,
        "current_state_snapshot": {
            "user_answers": dict(state.get("user_answers") or {}),
            "normalized": dict(state.get("normalized") or {}),
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(
            "Usage: python build_stage00_brief_repair_packet.py <intake_state.json> <project_brief.draft.json> <validation_errors.json> <output.json>",
            file=sys.stderr,
        )
        return 2
    state_path = Path(argv[1])
    draft_path = Path(argv[2])
    errors_path = Path(argv[3])
    output_path = Path(argv[4])

    state = load_or_create_state(state_path)
    draft = load_json(draft_path)
    errors_data = load_json(errors_path)
    failed_checks = normalize_failed_checks(errors_data)
    packet = build_repair_packet(state, draft, state_path, draft_path, failed_checks)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE00_BRIEF_REPAIR_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
