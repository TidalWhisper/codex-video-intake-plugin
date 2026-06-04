#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUESTION_KEYS = [
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

QUESTION_KEY_TO_INDEX = {key: index + 1 for index, key in enumerate(QUESTION_KEYS)}
QUESTION_INDEX_TO_KEY = {index + 1: key for index, key in enumerate(QUESTION_KEYS)}
HEADING_TO_KEY = {
    "Opening": "idea",
    "Question 2: target_duration": "target_duration",
    "Question 3: genre": "genre",
    "Question 4: style": "style",
    "Question 5: visual_spec": "visual_spec",
    "Question 6: characters": "characters",
    "Question 7: voice": "voice",
    "Question 8: music": "music",
    "Question 9: final_output": "final_output",
    "Final Confirmation": "final_confirmation",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def references_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "references"


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def parse_question_blocks() -> dict[str, str]:
    source = load_text(references_dir() / "stage00_question_blocks.md")
    pattern = re.compile(r"## (?P<title>.+?)\n\n```text\n(?P<block>.*?)\n```", re.S)
    blocks: dict[str, str] = {}
    for match in pattern.finditer(source):
        title = match.group("title").strip()
        key = HEADING_TO_KEY.get(title)
        if not key:
            continue
        blocks[key] = match.group("block").strip()
    missing = [key for key in list(QUESTION_KEYS) + ["final_confirmation"] if key not in blocks]
    if missing:
        raise SystemExit(
            "ERROR: stage00_question_blocks.md is missing canonical blocks for: "
            + ", ".join(missing)
        )
    return blocks


def canonical_question_block(question_key: str) -> str:
    blocks = parse_question_blocks()
    if question_key not in blocks:
        raise SystemExit(f"ERROR: unknown Stage 00 question key: {question_key}")
    return blocks[question_key]


def infer_project_context(state_path: Path) -> tuple[str, str]:
    resolved = state_path.resolve()
    if resolved.parent.name in {"00_intake", "intake"}:
        project_dir = resolved.parent.parent
    else:
        project_dir = resolved.parent
    project_id = project_dir.name or "video_intake_project"
    return project_id, str(project_dir).replace("\\", "/")


def build_initial_state(state_path: Path) -> dict[str, Any]:
    project_id, project_dir = infer_project_context(state_path)
    return {
        "schema_version": "0.4.0",
        "stage": "STAGE_00_INTAKE",
        "status": "collecting",
        "project_id": project_id,
        "project_dir": project_dir,
        "current_question": 1,
        "current_question_key": "idea",
        "answers": {},
        "user_answers": {},
        "normalized": {},
        "missing_required_fields": list(QUESTION_KEYS),
        "required_fields_complete": False,
        "next_question_key": "idea",
        "next_prompt_text": canonical_question_block("idea"),
        "ready_for_brief_generation": False,
        "last_user_reply": "",
        "updated_at": utc_now(),
    }


def load_or_create_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return build_initial_state(state_path)
    data = load_json(state_path)
    defaults = build_initial_state(state_path)
    merged = dict(defaults)
    merged.update(data)
    merged["answers"] = data.get("answers") if isinstance(data.get("answers"), dict) else defaults["answers"]
    merged["user_answers"] = data.get("user_answers") if isinstance(data.get("user_answers"), dict) else defaults["user_answers"]
    merged["normalized"] = data.get("normalized") if isinstance(data.get("normalized"), dict) else defaults["normalized"]
    if not isinstance(merged.get("missing_required_fields"), list):
        merged["missing_required_fields"] = list(QUESTION_KEYS)
    return merged


def ensure_draft_ready_state(state: dict[str, Any]) -> None:
    status = str(state.get("status") or "")
    if status != "draft_ready":
        raise SystemExit("ERROR: Stage 00 intake state must be draft_ready before running Stage 00-B")
    if state.get("ready_for_brief_generation") is not True:
        raise SystemExit("ERROR: Stage 00 intake state must set ready_for_brief_generation=true before running Stage 00-B")
    if state.get("required_fields_complete") is not True:
        raise SystemExit("ERROR: Stage 00 intake state must set required_fields_complete=true before running Stage 00-B")
    if state.get("missing_required_fields"):
        raise SystemExit("ERROR: Stage 00 intake state must have empty missing_required_fields before running Stage 00-B")


def empty_brief_normalized() -> dict[str, Any]:
    return {
        "idea": "",
        "target_duration_sec": "",
        "target_duration_label": "",
        "genre": "",
        "style": "",
        "aspect_ratio": "",
        "aspect_ratio_label": "",
        "resolution": "",
        "resolution_label": "",
        "characters_mode": "",
        "characters_required": "",
        "voice_mode": "",
        "voice_required": "",
        "music_mode": "",
        "music_profile": "",
        "music_required": "",
        "final_output": "",
    }
