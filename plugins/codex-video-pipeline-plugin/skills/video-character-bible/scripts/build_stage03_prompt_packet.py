#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import normal_brief, routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def ensure_locked_brief(brief: dict[str, Any]) -> None:
    if brief.get("status") != "locked":
        raise SystemExit("ERROR: brief must have status=locked")
    if brief.get("confirmed_by_user") is not True:
        raise SystemExit("ERROR: brief must have confirmed_by_user=true")
    if brief.get("allowed_next_stage") != "STAGE_01_SCRIPT_GENERATION":
        raise SystemExit("ERROR: brief must allow Stage 01 generation")


def build_packet(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    storyboard_path: Path,
) -> dict[str, Any]:
    normalized = normal_brief(brief)
    storyboard_shots = list(storyboard.get("shots") or [])
    anchors = resolve_upstream_story_anchors(storyboard, script)
    project_dir = Path(str(brief.get("project_dir") or "")).resolve() if brief.get("project_dir") else brief_path.parents[2]
    return {
        "packet_version": "0.1.0",
        "project_id": str(brief.get("project_id") or storyboard.get("project_id") or project_dir.name),
        "project_dir": str(project_dir).replace("\\", "/"),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_script": str(script_path.resolve()).replace("\\", "/"),
        "source_storyboard": str(storyboard_path.resolve()).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creative_goal": "Generate creator-quality Stage 03 character bible JSON using Codex while preserving the locked brief, Stage 01 script, and Stage 02 storyboard.",
        "hard_constraints": {
            "genre": str(normalized.get("genre") or ""),
            "style": str(normalized.get("style") or ""),
            "aspect_ratio": str(normalized.get("aspect_ratio") or ""),
            "voice_mode": str((script.get("script") or {}).get("voice_mode") or normalized.get("voice_mode") or ""),
            "characters_required": normalized.get("characters_required"),
            "final_output": str(normalized.get("final_output") or ""),
        },
        "story_anchors": anchors,
        "upstream_script": {
            "title": str(script.get("title") or ""),
            "theme": str(script.get("theme") or ""),
            "characters": list(script.get("characters") or []),
            "settings": list(script.get("settings") or []),
        },
        "upstream_storyboard": {
            "target_duration_sec": int(storyboard.get("target_duration_sec") or 0),
            "shot_count": int(storyboard.get("shot_count") or len(storyboard_shots)),
            "shots": storyboard_shots,
        },
        "reference_image_policy": {
            "reference_image_required_default": True,
            "character_locked_stage05_requires_ready_reference_images": True,
        },
        "routing": routing_from_brief(brief),
        "schema_refs": {
            "llm_output_schema": "skills/video-character-bible/references/stage03_llm_output.schema.json",
            "generation_prompt": "skills/video-character-bible/references/stage03_codex_generation_prompt.md",
            "repair_prompt": "skills/video-character-bible/references/stage03_codex_repair_prompt.md",
            "repair_packet_schema": "skills/video-character-bible/references/stage03_repair_packet.schema.json",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print("Usage: python build_stage03_prompt_packet.py <locked_brief.json> <script.json> <storyboard.json> <output.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    output_path = Path(argv[4])
    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    ensure_locked_brief(brief)
    packet = build_packet(brief, script, storyboard, brief_path, script_path, storyboard_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE03_PROMPT_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
