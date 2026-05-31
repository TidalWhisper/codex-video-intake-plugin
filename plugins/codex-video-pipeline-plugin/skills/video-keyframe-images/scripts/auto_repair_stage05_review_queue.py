#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import rerun_top_prompt_patches  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    return int(rerun_top_prompt_patches.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
