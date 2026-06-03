#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PIPELINE_SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
STAGE03_SCRIPT_DIR = PLUGIN_ROOT / "skills" / "video-character-bible" / "scripts"
sys.path.insert(0, str(STAGE03_SCRIPT_DIR))

from run_stage03_codex_flow import main as run_stage03_codex_flow_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return run_stage03_codex_flow_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
