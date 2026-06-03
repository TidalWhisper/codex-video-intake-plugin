#!/usr/bin/env python3
"""Pipeline-owned Stage 01 entry wrapper.

This keeps the official `$video-production-pipeline` Stage 01 handoff on a
stable script path while delegating the actual Codex-first generation logic to
the Stage 01 skill implementation.
"""
from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
STAGE01_SCRIPT_DIR = PLUGIN_ROOT / "skills" / "video-script-generation" / "scripts"
sys.path.insert(0, str(STAGE01_SCRIPT_DIR))

from run_stage01_codex_flow import main as run_stage01_codex_flow_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return run_stage01_codex_flow_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
