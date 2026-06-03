#!/usr/bin/env python3
"""Build a deterministic Stage 01 repair packet.

This is a first-batch shell interface for the planned Codex-first Stage 01
refactor. It does not perform repair by itself.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


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
    brief: dict[str, Any],
    script: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    failed_checks: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "packet_version": "0.1.0",
        "project_id": str(script.get("project_id") or brief.get("project_id") or ""),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_script": str(script_path.resolve()).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "failed_checks": failed_checks,
        "allowed_edits": derive_allowed_edits(failed_checks),
        "forbidden_edits": [
            "Do not rewrite the entire script unless explicitly allowed.",
            "Do not change duration, genre, style, aspect ratio, voice mode, music profile, or final output.",
            "Do not remove stable subject or scene anchors that already match the locked brief.",
        ],
        "current_draft": script,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(
            "Usage: python build_stage01_repair_packet.py <locked_brief.json> <script.json> <validation_errors.json> <output.json>",
            file=sys.stderr,
        )
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    errors_path = Path(argv[3])
    output_path = Path(argv[4])

    brief = load_json(brief_path)
    script = load_json(script_path)
    errors_data = load_json(errors_path)
    failed_checks = normalize_failed_checks(errors_data)

    packet = build_repair_packet(brief, script, brief_path, script_path, failed_checks)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE01_REPAIR_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
