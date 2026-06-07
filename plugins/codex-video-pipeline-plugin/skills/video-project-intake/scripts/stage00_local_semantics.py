#!/usr/bin/env python3
"""Legacy Stage 00 local semantics is permanently disabled for official runtime.

This file intentionally remains importable only to produce a hard failure when a
stale path tries to use it. Batch 2 requires Codex to own Stage 00 semantics.
"""
from __future__ import annotations

from typing import Any

ERROR_MESSAGE = (
    "ERROR: stage00_local_semantics.py is legacy/disabled. "
    "Official Stage 00 must run through Codex structured output via "
    "run_stage00_controller.py -> run_stage00_intake_turn.py / "
    "run_stage00_brief_from_intake.py. Direct local semantic execution is forbidden."
)


def evaluate_intake_turn(state: dict[str, Any], user_reply: str) -> dict[str, Any]:
    raise SystemExit(ERROR_MESSAGE)


def build_brief_llm_output(state: dict[str, Any]) -> dict[str, Any]:
    raise SystemExit(ERROR_MESSAGE)
