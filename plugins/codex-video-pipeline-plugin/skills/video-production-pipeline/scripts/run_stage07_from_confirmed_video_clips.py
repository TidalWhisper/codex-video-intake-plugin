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
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "video-audio" / "scripts"))

from pipeline_core.project_state import load_json_file  # noqa: E402
import new_audio_jobs  # noqa: E402
import run_comfyui_indextts2  # noqa: E402
import run_comfyui_music  # noqa: E402
import sync_audio_manifest  # noqa: E402


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
    parser.add_argument("script_json")
    parser.add_argument("storyboard_json")
    parser.add_argument("character_bible_json")
    parser.add_argument("video_clip_manifest_json")
    parser.add_argument("audio_manifest_json")
    args = parser.parse_args(argv)

    brief_path = Path(args.locked_brief).resolve()
    script_path = Path(args.script_json).resolve()
    storyboard_path = Path(args.storyboard_json).resolve()
    character_path = Path(args.character_bible_json).resolve()
    stage06_manifest_path = Path(args.video_clip_manifest_json).resolve()
    stage07_manifest_path = Path(args.audio_manifest_json).resolve()

    for path, label in [
        (brief_path, "locked brief"),
        (script_path, "Stage 01 script"),
        (storyboard_path, "Stage 02 storyboard"),
        (character_path, "Stage 03 character bible"),
        (stage06_manifest_path, "Stage 06 video clip manifest"),
    ]:
        if not path.exists():
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            return 1

    print("PIPELINE_STAGE07_SUBSTAGE: STAGE07_MANIFEST_SCAFFOLD")
    print(
        "PIPELINE_STAGE07_SUBSTAGE_COMMAND: python skills/video-audio/scripts/new_audio_jobs.py "
        f"{str(brief_path).replace(chr(92), '/')} {str(script_path).replace(chr(92), '/')} "
        f"{str(storyboard_path).replace(chr(92), '/')} {str(character_path).replace(chr(92), '/')} "
        f"{str(stage06_manifest_path).replace(chr(92), '/')} {str(stage07_manifest_path).replace(chr(92), '/')}"
    )
    scaffold_exit_code = new_audio_jobs.main([
        "new_audio_jobs.py",
        str(brief_path),
        str(script_path),
        str(storyboard_path),
        str(character_path),
        str(stage06_manifest_path),
        str(stage07_manifest_path),
    ])
    if scaffold_exit_code != 0:
        return scaffold_exit_code
    if not stage07_manifest_path.exists():
        print(f"ERROR: Stage 07 completed without manifest artifact: {stage07_manifest_path}", file=sys.stderr)
        return 1

    _load_json(stage07_manifest_path)

    print("PIPELINE_STAGE07_SUBSTAGE: STAGE07_VOICE_GENERATION")
    print(
        "PIPELINE_STAGE07_SUBSTAGE_COMMAND: python scripts/providers/run_comfyui_indextts2.py "
        f"{str(stage07_manifest_path).replace(chr(92), '/')}"
    )
    voice_exit_code = run_comfyui_indextts2.main([str(stage07_manifest_path)])

    print("PIPELINE_STAGE07_SUBSTAGE: STAGE07_MUSIC_GENERATION")
    print(
        "PIPELINE_STAGE07_SUBSTAGE_COMMAND: python scripts/providers/run_comfyui_music.py "
        f"{str(stage07_manifest_path).replace(chr(92), '/')}"
    )
    music_exit_code = run_comfyui_music.main([str(stage07_manifest_path)])

    print("PIPELINE_STAGE07_SUBSTAGE: STAGE07_SYNC_MANIFEST")
    print(
        "PIPELINE_STAGE07_SUBSTAGE_COMMAND: python skills/video-audio/scripts/sync_audio_manifest.py "
        f"{str(stage07_manifest_path).replace(chr(92), '/')}"
    )
    sync_exit_code = sync_audio_manifest.main([str(stage07_manifest_path)])
    if sync_exit_code != 0:
        return sync_exit_code

    if voice_exit_code != 0:
        print(f"STAGE07_VOICE_PROVIDER_RESULT_NONZERO: {voice_exit_code}")
    if music_exit_code != 0:
        print(f"STAGE07_MUSIC_PROVIDER_RESULT_NONZERO: {music_exit_code}")
    print(f"STAGE07_MAINLINE_HANDOFF_READY: {stage07_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
