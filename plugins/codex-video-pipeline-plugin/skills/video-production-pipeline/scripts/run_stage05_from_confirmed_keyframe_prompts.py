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
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "video-keyframe-images" / "scripts"))

from pipeline_core.project_state import load_json_file, update_project_manifest_for_stage  # noqa: E402
import new_keyframe_image_jobs  # noqa: E402
import run_stage05_codex_flow  # noqa: E402
import run_stage05_reference_bootstrap  # noqa: E402
import run_comfyui_txt2img  # noqa: E402
import sync_keyframe_image_manifest  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def _run_stage05_mainline(manifest_path: Path) -> int:
    manifest = _load_json(manifest_path)
    reference_bootstrap = manifest.get("reference_bootstrap") if isinstance(manifest.get("reference_bootstrap"), dict) else {}
    bootstrap_required = bool(reference_bootstrap.get("required"))
    bootstrap_ready = bool(reference_bootstrap.get("ready"))
    if bootstrap_required and not bootstrap_ready:
        print("PIPELINE_STAGE05_SUBSTAGE: STAGE05_A_REFERENCE_BOOTSTRAP")
        print(
            "PIPELINE_STAGE05_SUBSTAGE_COMMAND: python skills/video-keyframe-images/scripts/run_stage05_reference_bootstrap.py "
            f"{str(manifest_path).replace(chr(92), '/')}"
        )
        exit_code = run_stage05_reference_bootstrap.main([str(manifest_path)])
        if exit_code != 0:
            return exit_code
        manifest = _load_json(manifest_path)

    print("PIPELINE_STAGE05_SUBSTAGE: STAGE05_B_KEYFRAME_GENERATION")
    print(
        "PIPELINE_STAGE05_SUBSTAGE_COMMAND: python scripts/providers/run_comfyui_txt2img.py "
        f"{str(manifest_path).replace(chr(92), '/')}"
    )
    provider_exit_code = run_comfyui_txt2img.main([str(manifest_path)])

    print("PIPELINE_STAGE05_SUBSTAGE: STAGE05_SYNC_MANIFEST")
    print(
        "PIPELINE_STAGE05_SUBSTAGE_COMMAND: python skills/video-keyframe-images/scripts/sync_keyframe_image_manifest.py "
        f"{str(manifest_path).replace(chr(92), '/')}"
    )
    sync_exit_code = sync_keyframe_image_manifest.main([str(manifest_path)])
    if sync_exit_code != 0:
        return sync_exit_code

    if provider_exit_code != 0:
        print(f"STAGE05_PROVIDER_RESULT_NONZERO: {provider_exit_code}")
    print(f"STAGE05_MAINLINE_HANDOFF_READY: {manifest_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("locked_brief")
    parser.add_argument("keyframe_prompts_json")
    parser.add_argument("keyframe_image_manifest_json")
    args = parser.parse_args(argv)

    brief_path = Path(args.locked_brief).resolve()
    keyframe_path = Path(args.keyframe_prompts_json).resolve()
    manifest_path = Path(args.keyframe_image_manifest_json).resolve()

    if not brief_path.exists():
        print(f"ERROR: locked brief not found: {brief_path}", file=sys.stderr)
        return 1
    if not keyframe_path.exists():
        print(f"ERROR: Stage 04 keyframe prompts not found: {keyframe_path}", file=sys.stderr)
        return 1

    print("PIPELINE_STAGE05_SUBSTAGE: STAGE05_CODEX_SEMANTIC_CONTRACT")
    print(
        "PIPELINE_STAGE05_SUBSTAGE_COMMAND: python skills/video-keyframe-images/scripts/run_stage05_codex_flow.py "
        f"{str(brief_path).replace(chr(92), '/')} {str(keyframe_path).replace(chr(92), '/')}"
    )
    codex_flow_exit_code = run_stage05_codex_flow.main([
        str(brief_path),
        str(keyframe_path),
    ])
    if codex_flow_exit_code != 0:
        return codex_flow_exit_code

    refreshed_keyframe_prompts = _load_json(keyframe_path)
    if not isinstance(refreshed_keyframe_prompts.get("stage05_semantic_contract"), dict):
        print(
            f"ERROR: Stage 05 Codex flow completed without stage05_semantic_contract in {keyframe_path}",
            file=sys.stderr,
        )
        return 1

    print("PIPELINE_STAGE05_SUBSTAGE: STAGE05_MANIFEST_SCAFFOLD")
    print(
        "PIPELINE_STAGE05_SUBSTAGE_COMMAND: python skills/video-keyframe-images/scripts/new_keyframe_image_jobs.py "
        f"{str(brief_path).replace(chr(92), '/')} {str(keyframe_path).replace(chr(92), '/')} {str(manifest_path).replace(chr(92), '/')}"
    )
    scaffold_exit_code = new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(brief_path),
        str(keyframe_path),
        str(manifest_path),
    ])
    if scaffold_exit_code != 0:
        return scaffold_exit_code
    if not manifest_path.exists():
        print(f"ERROR: Stage 05 completed without manifest artifact: {manifest_path}", file=sys.stderr)
        return 1
    update_project_manifest_for_stage(
        manifest_path,
        current_stage="STAGE_05_KEYFRAME_IMAGES_GENERATION",
        allowed_next_stage="STAGE_05_KEYFRAME_IMAGES",
        flags={"keyframe_images_confirmed": False},
        status="active",
    )

    return _run_stage05_mainline(manifest_path)


if __name__ == "__main__":
    raise SystemExit(main())
