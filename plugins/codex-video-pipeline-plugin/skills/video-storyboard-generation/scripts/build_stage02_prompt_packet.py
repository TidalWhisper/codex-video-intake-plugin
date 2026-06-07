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
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402


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


def ensure_confirmed_script(script: dict[str, Any]) -> None:
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        raise SystemExit("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION")
    status = str(script.get("status") or "").strip().lower()
    allowed_next_stage = str(script.get("allowed_next_stage") or "").strip()
    if status != "confirmed" or allowed_next_stage != "STAGE_02_STORYBOARD":
        raise SystemExit("ERROR: Stage 02 requires a user-confirmed Stage 01 script")


def build_packet(brief: dict[str, Any], script: dict[str, Any], brief_path: Path, script_path: Path) -> dict[str, Any]:
    normalized = normal_brief(brief)
    duration = int(normalized.get("target_duration_sec") or (script.get("duration_plan") or {}).get("target_duration_sec") or 30)
    sections = (script.get("script") or {}).get("sections") if isinstance(script.get("script"), dict) else []
    beats = (script.get("duration_plan") or {}).get("beats") if isinstance(script.get("duration_plan"), dict) else []
    target_shot_count = max(1, len(beats))
    anchors = resolve_upstream_story_anchors(script)
    project_dir = Path(str(brief.get("project_dir") or "")).resolve() if brief.get("project_dir") else brief_path.parents[2]
    return {
        "packet_version": "0.1.0",
        "project_id": str(brief.get("project_id") or script.get("project_id") or project_dir.name),
        "project_dir": str(project_dir).replace("\\", "/"),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_script": str(script_path.resolve()).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creative_goal": "Generate creator-quality Stage 02 storyboard JSON using Codex while preserving the locked brief and the approved Stage 01 script.",
        "hard_constraints": {
            "genre": str(normalized.get("genre") or ""),
            "style": str(normalized.get("style") or ""),
            "duration_sec": duration,
            "aspect_ratio": str(normalized.get("aspect_ratio") or ""),
            "resolution": str(normalized.get("resolution") or ""),
            "voice_mode": str((script.get("script") or {}).get("voice_mode") or normalized.get("voice_mode") or ""),
            "music_mode": str((script.get("script") or {}).get("music_mode") or normalized.get("music_mode") or ""),
            "music_profile": str((script.get("script") or {}).get("music_profile") or normalized.get("music_profile") or ""),
            "final_output": str(normalized.get("final_output") or ""),
        },
        "story_anchors": anchors,
        "shot_plan": {
            "target_shot_count": target_shot_count,
            "target_duration_sec": duration,
            "target_duration_label": str(normalized.get("target_duration_label") or f"{duration}秒"),
            "must_cover_all_script_sections": True,
        },
        "upstream_script": {
            "title": str(script.get("title") or ""),
            "logline": str(script.get("logline") or ""),
            "theme": str(script.get("theme") or ""),
            "protagonist_state": str(script.get("protagonist_state") or ""),
            "narrative_movement": str(script.get("narrative_movement") or ""),
            "ending_direction": str(script.get("ending_direction") or ""),
            "avoid": list(script.get("avoid") or []),
            "characters": list(script.get("characters") or []),
            "settings": list(script.get("settings") or []),
            "beats": list(beats or []),
            "sections": list(sections or []),
        },
        "routing": routing_from_brief(brief),
        "schema_refs": {
            "llm_output_schema": "skills/video-storyboard-generation/references/stage02_llm_output.schema.json",
            "generation_prompt": "skills/video-storyboard-generation/references/stage02_codex_generation_prompt.md",
            "repair_prompt": "skills/video-storyboard-generation/references/stage02_codex_repair_prompt.md",
            "repair_packet_schema": "skills/video-storyboard-generation/references/stage02_repair_packet.schema.json",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: python build_stage02_prompt_packet.py <locked_brief.json> <script.json> <output.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    output_path = Path(argv[3])
    brief = load_json(brief_path)
    script = load_json(script_path)
    ensure_locked_brief(brief)
    ensure_confirmed_script(script)
    packet = build_packet(brief, script, brief_path, script_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE02_PROMPT_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
