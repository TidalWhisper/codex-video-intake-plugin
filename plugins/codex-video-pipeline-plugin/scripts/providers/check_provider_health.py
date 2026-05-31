#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from provider_config import (
    ConfigError,
    check_comfyui_server,
    check_openai_image_provider,
    inspect_workflow_file,
    load_provider_config,
    validate_provider_config,
)
from workflow_mapping import load_mapped_workflow, load_workflow_mapping


def inspect_configured_music_workflow(repo_root: Path, workflow_name: str) -> dict[str, object]:
    try:
        mapping_data, mapping_path = load_workflow_mapping(root=repo_root)
        _, _, workflow_path = load_mapped_workflow(mapping_data, workflow_name, root=repo_root)
    except Exception as exc:
        return {
            "workflow_name": workflow_name,
            "workflow_mapping_path": str((repo_root / "config" / "workflow_node_mapping.yaml").resolve()).replace("\\", "/"),
            "workflow_mapping_error": str(exc),
            "workflow": {
                "path": "",
                "exists": False,
                "valid": False,
                "error": str(exc),
                "node_types": [],
            },
        }
    return {
        "workflow_name": workflow_name,
        "workflow_mapping_path": str(mapping_path).replace("\\", "/"),
        "workflow_mapping_error": None,
        "workflow": inspect_workflow_file(workflow_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--workflow-name", default="music_generation", help="Workflow mapping entry to inspect")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    parser.add_argument("--timeout", type=int, default=None, help="Override ComfyUI timeout for the health check")
    parser.add_argument("--openai-timeout", type=int, default=None, help="Override OpenAI auth probe timeout for the health check")
    args = parser.parse_args(argv)

    try:
        data, path = load_provider_config(config_path=args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate_provider_config(data)
    openai_result = check_openai_image_provider(
        data,
        probe=True,
        timeout_seconds=args.openai_timeout,
    )
    comfyui_result = check_comfyui_server(data, timeout=args.timeout)
    repo_root = path.resolve().parents[1]
    configured_music = inspect_configured_music_workflow(repo_root, args.workflow_name)
    music_workflow = configured_music["workflow"]
    stage07_cfg = data.get("stage07_audio") if isinstance(data.get("stage07_audio"), dict) else {}
    stage07_music_result = {
        "configured_provider": str(stage07_cfg.get("music_provider") or ""),
        "workflow_name": configured_music["workflow_name"],
        "workflow_mapping_path": configured_music["workflow_mapping_path"],
        "workflow_mapping_error": configured_music["workflow_mapping_error"],
        "workflow": music_workflow,
        "provider_backed_ready": bool(
            comfyui_result.get("ready") and music_workflow["valid"]
        ),
        "fallback_possible": str(stage07_cfg.get("music_provider") or "") == "local_library_or_comfyui",
    }
    warnings: list[str] = []
    if configured_music["workflow_mapping_error"]:
        warnings.append(
            f"Configured Stage 07 music workflow mapping '{args.workflow_name}' could not be resolved: {configured_music['workflow_mapping_error']}"
        )
    result = {
        "config_path": str(path).replace("\\", "/"),
        "valid_config": not errors,
        "errors": errors,
        "openai_image": openai_result,
        "comfyui": comfyui_result,
        "stage07_music": stage07_music_result,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"CONFIG_PATH: {result['config_path']}")
        print("CONFIG_STATUS: OK" if result["valid_config"] else "CONFIG_STATUS: INVALID")
        print(f"OPENAI_STATUS: {openai_result['status']}")
        print(f"COMFYUI_STATUS: {comfyui_result['status']}")
        print(f"STAGE07_MUSIC_PROVIDER_READY: {stage07_music_result['provider_backed_ready']}")
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")

    config_ok = not errors
    openai_ok = openai_result["status"] in {"ready", "disabled"}
    comfyui_ok = comfyui_result["status"] in {"ready", "disabled"}
    return 0 if config_ok and openai_ok and comfyui_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
