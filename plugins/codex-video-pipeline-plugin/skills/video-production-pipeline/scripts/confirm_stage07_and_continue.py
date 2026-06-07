#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "skills" / "video-audio" / "scripts"))

from pipeline_core.project_state import load_json_file, write_json_file  # noqa: E402
import continue_pipeline  # noqa: E402
import validate_audio_manifest  # noqa: E402


def _load(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python confirm_stage07_and_continue.py <project_dir>", file=sys.stderr)
        return 2

    project_dir = Path(args[0]).resolve()
    manifest_path = project_dir / "project_manifest.json"
    stage07_manifest_path = project_dir / "07_audio" / "audio_manifest.json"

    if not manifest_path.exists():
        print(f"ERROR: project manifest not found: {manifest_path}", file=sys.stderr)
        return 1
    if not stage07_manifest_path.exists():
        print(f"ERROR: Stage 07 audio manifest not found: {stage07_manifest_path}", file=sys.stderr)
        return 1

    stage07_data = _load(stage07_manifest_path)
    ok, errors, _warnings = validate_audio_manifest.validate(stage07_data, stage07_manifest_path, mode="final")
    if not ok:
        print("ERROR: Stage 07 audio manifest failed final validation before confirmation:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    stage07_data["status"] = "confirmed"
    stage07_data["formal_promotion_status"] = "confirmed"
    stage07_data["confirmed_by_user"] = True
    stage07_data["allowed_next_stage"] = "STAGE_08_ASSEMBLY"
    write_json_file(stage07_manifest_path, stage07_data)

    manifest_data = _load(manifest_path)
    manifest_data["current_stage"] = "STAGE_07_AUDIO_CONFIRMED"
    manifest_data["brief_locked"] = True
    manifest_data["script_confirmed"] = True
    manifest_data["storyboard_confirmed"] = True
    manifest_data["character_bible_confirmed"] = True
    manifest_data["keyframe_prompts_confirmed"] = True
    manifest_data["keyframe_images_confirmed"] = True
    manifest_data["video_clips_confirmed"] = True
    manifest_data["audio_confirmed"] = True
    manifest_data["allowed_next_stage"] = "STAGE_08_ASSEMBLY"
    write_json_file(manifest_path, manifest_data)

    print(f"STAGE07_CONFIRMED: {project_dir}")
    return continue_pipeline.main(["--project-dir", str(project_dir)])


if __name__ == "__main__":
    raise SystemExit(main())
