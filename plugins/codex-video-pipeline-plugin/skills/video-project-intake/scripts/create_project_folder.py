#!/usr/bin/env python3
"""Create an independent video project folder for the Codex video pipeline.

Usage:
  python create_project_folder.py --root video_projects --title "落日海滩女孩"
  python create_project_folder.py --project-id video_20260528_103000_sunset_girl
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_DIRS = [
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


def slugify(text: str, max_len: int = 24) -> str:
    """Create a safe short slug.

    The first implementation preserved any ASCII number found inside Chinese
    text, so a title like "一位20岁出头的女孩..." produced a weak slug such as
    "20". This version only uses an ASCII slug when it contains at least one
    alphabetic token; otherwise it falls back to the stable, readable
    "project" suffix. Codex can still pass an explicit --project-id when it
    wants a semantic English slug such as sunset_beach_girl.
    """
    raw = text.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", raw)
    slug = re.sub(r"_+", "_", slug).strip("_")

    # Avoid unhelpful numeric-only slugs created from ages/durations in Chinese
    # prompts, e.g. "20" from "一位20岁出头的女孩...".
    if not slug or not re.search(r"[a-z]", slug):
        return "project"

    slug = slug[:max_len].strip("_")
    if not slug or not re.search(r"[a-z]", slug):
        return "project"
    return slug


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="video_projects", help="Root folder for all generated video projects")
    parser.add_argument("--title", default="", help="Optional title or idea used to derive a short slug")
    parser.add_argument("--project-id", default="", help="Optional explicit project id")
    args = parser.parse_args()

    now = datetime.now()
    project_id = args.project_id.strip()
    if not project_id:
        project_id = f"video_{now.strftime('%Y%m%d_%H%M%S')}_{slugify(args.title)}"

    root = Path(args.root)
    project_dir = root / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    for rel in REQUIRED_DIRS:
        d = project_dir / rel
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    manifest = {
        "schema_version": "0.3.0",
        "project_id": project_id,
        "project_dir": str(project_dir).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "current_stage": "STAGE_00_INTAKE",
        "status": "created",
        "brief_locked": False,
        "script_confirmed": False,
        "requested_output_scope": "",
        "requested_output_label": "",
        "requested_terminal_stage": "",
        "compiled_requirements": {},
        "quality_contract": {},
        "allowed_next_stage": None,
        "folders": {rel: str((project_dir / rel)).replace("\\", "/") for rel in REQUIRED_DIRS},
    }
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(str(project_dir).replace("\\", "/"))
    print(f"MANIFEST: {manifest_path}".replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
