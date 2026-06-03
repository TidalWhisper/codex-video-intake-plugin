#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.project_state import load_json_file  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


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


def build_repair_packet(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    character_bible: dict[str, Any],
    keyframe_prompts: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    storyboard_path: Path,
    character_path: Path,
    keyframe_path: Path,
    failed_checks: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "packet_version": "0.1.0",
        "project_id": str(keyframe_prompts.get("project_id") or character_bible.get("project_id") or storyboard.get("project_id") or script.get("project_id") or brief.get("project_id") or ""),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_script": str(script_path.resolve()).replace("\\", "/"),
        "source_storyboard": str(storyboard_path.resolve()).replace("\\", "/"),
        "source_character_bible": str(character_path.resolve()).replace("\\", "/"),
        "source_keyframe_prompts": str(keyframe_path.resolve()).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "failed_checks": failed_checks,
        "allowed_edits": [item.get("path") or "field-level fixes only" for item in failed_checks] or ["field-level fixes only"],
        "forbidden_edits": [
            "Do not rewrite the approved story, shot order, or character identity.",
            "Do not change duration, aspect ratio, style direction, or continuity mode.",
            "Do not remove already-correct reference image readiness fields unless validation requires it.",
        ],
        "current_draft": keyframe_prompts,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 8:
        print(
            "Usage: python build_stage04_repair_packet.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json> <keyframe_prompts.json> <validation_errors.json> <output.json>",
            file=sys.stderr,
        )
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    character_path = Path(argv[4])
    keyframe_path = Path(argv[5])
    errors_path = Path(argv[6])
    output_path = Path(argv[7])

    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    character_bible = load_json(character_path)
    keyframe_prompts = load_json(keyframe_path)
    errors_data = load_json(errors_path)
    failed_checks = normalize_failed_checks(errors_data)

    packet = build_repair_packet(
        brief,
        script,
        storyboard,
        character_bible,
        keyframe_prompts,
        brief_path,
        script_path,
        storyboard_path,
        character_path,
        keyframe_path,
        failed_checks,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE04_REPAIR_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
