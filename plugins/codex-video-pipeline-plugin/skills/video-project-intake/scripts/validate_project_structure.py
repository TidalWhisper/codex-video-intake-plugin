#!/usr/bin/env python3
"""Validate the independent video project folder structure."""
from __future__ import annotations
import sys
from pathlib import Path

REQUIRED = [
    "project_manifest.json",
    "00_intake",
    "01_script",
    "02_storyboard",
    "03_characters",
    "04_keyframes",
    "05_images",
    "06_video_clips",
    "07_audio/voice",
    "07_audio/music",
    "08_assembly",
    "09_qa",
    "logs",
]

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python validate_project_structure.py <project_dir>", file=sys.stderr)
        return 2
    project_dir = Path(argv[1])
    errors = []
    for rel in REQUIRED:
        if not (project_dir / rel).exists():
            errors.append(f"missing: {rel}")
    if errors:
        print("PROJECT STRUCTURE VALIDATION FAILED:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"PROJECT STRUCTURE VALIDATION PASSED: {project_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
