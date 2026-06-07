#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "video-video-clips" / "scripts"))

from pipeline_core.project_state import load_json_file  # noqa: E402
import new_video_clip_jobs  # noqa: E402
import run_comfyui_ltx_i2v  # noqa: E402
import sync_video_clip_manifest  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("locked_brief")
    parser.add_argument("storyboard_json")
    parser.add_argument("keyframe_prompts_json")
    parser.add_argument("keyframe_image_manifest_json")
    parser.add_argument("video_clip_manifest_json")
    args = parser.parse_args(argv)

    brief_path = Path(args.locked_brief).resolve()
    storyboard_path = Path(args.storyboard_json).resolve()
    keyframe_path = Path(args.keyframe_prompts_json).resolve()
    stage05_manifest_path = Path(args.keyframe_image_manifest_json).resolve()
    stage06_manifest_path = Path(args.video_clip_manifest_json).resolve()

    for path, label in [
        (brief_path, "locked brief"),
        (storyboard_path, "Stage 02 storyboard"),
        (keyframe_path, "Stage 04 keyframe prompts"),
        (stage05_manifest_path, "Stage 05 keyframe image manifest"),
    ]:
        if not path.exists():
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            return 1

    print("PIPELINE_STAGE06_SUBSTAGE: STAGE06_MANIFEST_SCAFFOLD")
    print(
        "PIPELINE_STAGE06_SUBSTAGE_COMMAND: python skills/video-video-clips/scripts/new_video_clip_jobs.py "
        f"{str(brief_path).replace(chr(92), '/')} {str(storyboard_path).replace(chr(92), '/')} "
        f"{str(keyframe_path).replace(chr(92), '/')} {str(stage05_manifest_path).replace(chr(92), '/')} "
        f"{str(stage06_manifest_path).replace(chr(92), '/')}"
    )
    scaffold_exit_code = new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(brief_path),
        str(storyboard_path),
        str(keyframe_path),
        str(stage05_manifest_path),
        str(stage06_manifest_path),
    ])
    if scaffold_exit_code != 0:
        return scaffold_exit_code
    if not stage06_manifest_path.exists():
        print(f"ERROR: Stage 06 completed without manifest artifact: {stage06_manifest_path}", file=sys.stderr)
        return 1

    _load_json(stage06_manifest_path)

    print("PIPELINE_STAGE06_SUBSTAGE: STAGE06_CLIP_GENERATION")
    print(
        "PIPELINE_STAGE06_SUBSTAGE_COMMAND: python scripts/providers/run_comfyui_ltx_i2v.py "
        f"{str(stage06_manifest_path).replace(chr(92), '/')}"
    )
    provider_exit_code = run_comfyui_ltx_i2v.main([str(stage06_manifest_path)])

    print("PIPELINE_STAGE06_SUBSTAGE: STAGE06_SYNC_MANIFEST")
    print(
        "PIPELINE_STAGE06_SUBSTAGE_COMMAND: python skills/video-video-clips/scripts/sync_video_clip_manifest.py "
        f"{str(stage06_manifest_path).replace(chr(92), '/')}"
    )
    sync_exit_code = sync_video_clip_manifest.main([str(stage06_manifest_path)])
    if sync_exit_code != 0:
        return sync_exit_code

    if provider_exit_code != 0:
        print(f"STAGE06_PROVIDER_RESULT_NONZERO: {provider_exit_code}")
    print(f"STAGE06_MAINLINE_HANDOFF_READY: {stage06_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
