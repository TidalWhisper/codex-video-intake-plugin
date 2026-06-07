#!/usr/bin/env python3
"""Build a deterministic Stage 01 prompt packet from a locked brief.

This module is part of the active Stage 01 formal runtime. Its job is to
compile hard constraints and anchor data from the locked brief for Codex/LLM
generation. It must not author creative prose itself.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import (  # noqa: E402
    count_duration_beats,
    normal_brief,
    routing_from_brief,
    split_duration,
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def ensure_locked_brief(brief: dict[str, Any]) -> None:
    if brief.get("status") != "locked":
        raise SystemExit("ERROR: brief must have status=locked")
    if brief.get("confirmed_by_user") is not True:
        raise SystemExit("ERROR: brief must have confirmed_by_user=true")
    if brief.get("allowed_next_stage") != "STAGE_01_SCRIPT_GENERATION":
        raise SystemExit("ERROR: brief must allow Stage 01 generation")


def _ordered_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


def list_must_keep_phrases(brief: dict[str, Any]) -> list[str]:
    normalized = normal_brief(brief)
    user_answers = brief.get("user_answers") if isinstance(brief.get("user_answers"), dict) else {}
    return _ordered_unique([
        str(normalized.get("idea") or "").strip(),
        str(user_answers.get("characters_note") or "").strip(),
        str(normalized.get("genre") or "").strip(),
        str(normalized.get("style") or "").strip(),
        str(normalized.get("voice_mode") or "").strip(),
        str(normalized.get("music_profile") or "").strip(),
        str(normalized.get("final_output") or "").strip(),
    ])


def list_must_avoid(brief: dict[str, Any]) -> list[str]:
    normalized = normal_brief(brief)
    items = [
        "Do not change duration, genre, style, aspect ratio, voice mode, music profile, or final output.",
        "Do not output storyboard shot lists in Stage 01.",
    ]
    if "不需要配音" in str(normalized.get("voice_mode") or ""):
        items.append("Do not add narration or dialogue.")
    if str(normalized.get("genre") or "") == "音乐MV":
        items.append("Do not rewrite the project into a dialogue-driven short drama.")
    return items


def build_packet(brief: dict[str, Any], brief_path: Path) -> dict[str, Any]:
    normalized = normal_brief(brief)
    user_answers = brief.get("user_answers") if isinstance(brief.get("user_answers"), dict) else {}
    duration = int(normalized.get("target_duration_sec") or 30)
    beat_count = count_duration_beats(duration)
    beat_lengths = split_duration(duration, beat_count)
    project_dir = Path(str(brief.get("project_dir") or "")).resolve() if brief.get("project_dir") else brief_path.parents[2]
    story_premise = str(normalized.get("idea") or "").strip()
    character_note = str(user_answers.get("characters_note") or "").strip()
    return {
        "packet_version": "0.1.0",
        "project_id": str(brief.get("project_id") or project_dir.name),
        "project_dir": str(project_dir).replace("\\", "/"),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creative_goal": "Generate creator-quality Stage 01 structured script content using Codex, while preserving all locked-brief constraints.",
        "story_premise": story_premise,
        "hard_constraints": {
            "genre": str(normalized.get("genre") or ""),
            "style": str(normalized.get("style") or ""),
            "duration_sec": duration,
            "duration_label": str(normalized.get("target_duration_label") or f"{duration}秒"),
            "aspect_ratio": str(normalized.get("aspect_ratio") or ""),
            "aspect_ratio_label": str(normalized.get("aspect_ratio_label") or ""),
            "resolution": str(normalized.get("resolution") or ""),
            "voice_mode": str(normalized.get("voice_mode") or ""),
            "music_mode": str(normalized.get("music_mode") or ""),
            "music_profile": str(normalized.get("music_profile") or ""),
            "final_output": str(normalized.get("final_output") or ""),
        },
        "anchors": {
            "locked_idea_text": story_premise,
            "character_note": character_note,
            "raw_identity_clues": _ordered_unique([story_premise, character_note]),
            "must_keep_phrases": list_must_keep_phrases(brief),
            "must_avoid": list_must_avoid(brief),
        },
        "beat_plan": {
            "beat_count": beat_count,
            "beat_lengths_sec": beat_lengths,
        },
        "routing": routing_from_brief(brief),
        "schema_refs": {
            "llm_output_schema": "skills/video-script-generation/references/stage01_llm_output.schema.json",
            "generation_prompt": "skills/video-script-generation/references/stage01_codex_generation_prompt.md",
            "repair_prompt": "skills/video-script-generation/references/stage01_codex_repair_prompt.md",
            "repair_packet_schema": "skills/video-script-generation/references/stage01_repair_packet.schema.json",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python build_stage01_prompt_packet.py <locked_brief.json> <output.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    output_path = Path(argv[2])
    brief = load_json(brief_path)
    ensure_locked_brief(brief)
    packet = build_packet(brief, brief_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE01_PROMPT_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
