#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from provider_config import (
    ConfigError,
    discover_openai_api_key,
    inspect_workflow_file,
    load_provider_config,
    root_dir,
)
from workflow_mapping import load_mapped_workflow, load_workflow_mapping


BASE_EXPECTED_WORKFLOWS = [
    "txt2img_keyframe.workflow_api.json",
    "i2v_ltx.workflow_api.json",
    "indextts2.workflow_api.json",
]
EXPECTED_WORKFLOWS = BASE_EXPECTED_WORKFLOWS

DEFAULT_MUSIC_WORKFLOW_NAME = "music_generation"

NODE_PATTERNS = {
    "ltx_video": ["ltxvimgtovideo", "ltxvimgtovideoadvanced", "ltxvapiimagetovideo", "ltxvaddguide"],
    "indextts2": ["indextts", "referenceaudio", "saveaudio"],
    "music_generation": ["acestep", "heartmula", "audiovideocombine", "musicgen", "inspiremusic"],
}

CUSTOM_NODE_HINTS = {
    "ltx_video": ["ComfyUI-LTXVideo"],
    "indextts2": ["comfyui-easy-indextts2"],
}


def fetch_object_info(base_url: str, timeout_seconds: int = 10) -> tuple[bool, dict[str, Any] | None, str | None]:
    url = f"{base_url.rstrip('/')}/object_info"
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return False, None, str(exc.reason or exc)
    except json.JSONDecodeError as exc:
        return False, None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return False, None, "object_info root must be a JSON object"
    return True, payload, None


def list_matching_nodes(object_info: dict[str, Any], patterns: list[str]) -> list[str]:
    lowered = [pattern.lower() for pattern in patterns]
    matches: list[str] = []
    for key in sorted(object_info.keys()):
        key_lower = key.lower()
        if any(pattern in key_lower for pattern in lowered):
            matches.append(key)
    return matches


def workflow_status(workflow_root: Path) -> dict[str, Any]:
    return workflow_status_for_files(workflow_root, BASE_EXPECTED_WORKFLOWS)


def workflow_status_for_files(workflow_root: Path, expected_workflows: list[str]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    all_present = True
    for name in expected_workflows:
        path = workflow_root / name
        exists = path.exists() and path.is_file() and path.stat().st_size > 0
        files[name] = {
            "path": str(path).replace("\\", "/"),
            "exists": exists,
        }
        if not exists:
            all_present = False
    return {
        "root": str(workflow_root).replace("\\", "/"),
        "all_present": all_present,
        "files": files,
    }


def inspect_configured_music_workflows(
    repo_root: Path,
    local_workflow_root: Path,
    workflow_name: str = DEFAULT_MUSIC_WORKFLOW_NAME,
) -> dict[str, Any]:
    fallback_repo_path = repo_root / "workflows" / "comfyui" / "AceStep_Music_Workflow.json"
    repo_path = fallback_repo_path
    mapping_path = repo_root / "config" / "workflow_node_mapping.yaml"
    mapping_error: str | None = None
    try:
        mapping_data, mapping_path = load_workflow_mapping(root=repo_root)
        _, _, repo_path = load_mapped_workflow(mapping_data, workflow_name, root=repo_root)
    except Exception as exc:
        mapping_error = str(exc)
    local_path = local_workflow_root / repo_path.name
    return {
        "workflow_name": workflow_name,
        "mapping_path": str(mapping_path.resolve()).replace("\\", "/"),
        "mapping_error": mapping_error,
        "workflow_filename": repo_path.name,
        "repo_path": str(repo_path).replace("\\", "/"),
        "local_path": str(local_path).replace("\\", "/"),
        "repo": inspect_workflow_file(repo_path),
        "local": inspect_workflow_file(local_path),
    }


def custom_node_status(custom_nodes_root: Path) -> dict[str, Any]:
    installed = {item.name for item in custom_nodes_root.iterdir()} if custom_nodes_root.exists() and custom_nodes_root.is_dir() else set()
    hints: dict[str, Any] = {}
    for key, names in CUSTOM_NODE_HINTS.items():
        hints[key] = {
            "expected": names,
            "present": [name for name in names if name in installed],
        }
    return {
        "root": str(custom_nodes_root).replace("\\", "/"),
        "exists": custom_nodes_root.exists() and custom_nodes_root.is_dir(),
        "installed_count": len(installed),
        "hints": hints,
    }


def build_next_steps(result: dict[str, Any]) -> list[str]:
    steps: list[str] = []
    fallback_music_allowed = bool(result.get("fallback_music_allowed"))
    if not result["config"]["providers_yaml_exists"]:
        steps.append("Copy config/providers.example.yaml to config/providers.yaml and fill local values.")
    if not result["config"]["workflow_mapping_exists"]:
        steps.append("Copy config/workflow_node_mapping.example.yaml to config/workflow_node_mapping.yaml and fill real node ids.")
    if result["music_workflow"]["mapping_error"] and not fallback_music_allowed:
        steps.append(
            "Fix config/workflow_node_mapping.yaml so the default music_generation entry resolves to a real workflow file."
        )
    if not result["openai"]["api_key_present"]:
        steps.append("Provide an OpenAI-compatible image auth source before running Stage 05 OpenAI image generation.")
    if not result["comfyui"]["paths"]["input_dir_exists"]:
        steps.append("Configure comfyui.input_dir to the local ComfyUI input folder for Stage 06/07 staged assets.")
    if not result["comfyui"]["paths"]["output_dir_exists"]:
        steps.append("Configure comfyui.output_dir to the local ComfyUI output folder so generated files can be collected.")
    if not result["repo_workflows"]["all_present"] and not fallback_music_allowed:
        steps.append("Export API-format workflows into plugins/codex-video-pipeline-plugin/workflows/comfyui/ with the expected filenames.")
    if not result["repo_workflows"]["all_present"] and not result["local_workflows"]["all_present"] and not fallback_music_allowed:
        steps.append("Prepare local exported workflows under the configured ComfyUI workflow folder.")
    if not result["comfyui"]["reachable"]:
        steps.append("Start local ComfyUI on 127.0.0.1:8188 before real smoke tests.")
    else:
        if not result["comfyui"]["node_checks"]["ltx_video"]["matches"]:
            steps.append("Install or enable LTX video nodes in local ComfyUI.")
        if not result["comfyui"]["node_checks"]["indextts2"]["matches"]:
            steps.append("Install or enable IndexTTS2-related nodes in local ComfyUI.")
        if not result["comfyui"]["node_checks"]["music_generation"]["matches"] and not fallback_music_allowed:
            steps.append("Install or confirm at least one audio/music generation node path in local ComfyUI.")
    return steps


def inspect_local_real_e2e_prereqs(
    *,
    repo_root: Path | None = None,
    comfy_base_url: str = "http://127.0.0.1:8188",
    local_workflow_root: Path | None = None,
    custom_nodes_root: Path | None = None,
    comfy_input_root: Path | None = None,
    comfy_output_root: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    repo = repo_root or root_dir()
    env_map = env or os.environ
    config_dir = repo / "config"
    repo_workflow_root = repo / "workflows" / "comfyui"
    local_workflows = local_workflow_root or Path(r"F:\ComfyUI\Codex\workflows")
    custom_nodes = custom_nodes_root or Path(r"F:\ComfyUI\ComfyUI\custom_nodes")
    comfy_python = Path(r"F:\ComfyUI\Codex\comfy-python.cmd")
    comfy_api = Path(r"F:\ComfyUI\Codex\comfyui_api.py")
    comfy_input_dir = comfy_input_root or Path(r"F:\ComfyUI\ComfyUI\input")
    comfy_output_dir = comfy_output_root or Path(r"F:\ComfyUI\ComfyUI\output")
    openai_key_info = discover_openai_api_key(env=env_map)
    provider_data: dict[str, Any] = {}
    try:
        provider_data, _ = load_provider_config(root=repo)
    except ConfigError:
        provider_data = {}

    reachable, object_info, error = fetch_object_info(comfy_base_url)
    node_checks: dict[str, Any] = {}
    for key, patterns in NODE_PATTERNS.items():
        node_checks[key] = {
            "patterns": patterns,
            "matches": list_matching_nodes(object_info or {}, patterns) if object_info else [],
        }
    configured_music_workflow = inspect_configured_music_workflows(repo, local_workflows)
    expected_workflows = BASE_EXPECTED_WORKFLOWS + [configured_music_workflow["workflow_filename"]]
    repo_workflow_status = workflow_status_for_files(repo_workflow_root, expected_workflows)
    local_workflow_status = workflow_status_for_files(local_workflows, expected_workflows)
    repo_music_workflow = configured_music_workflow["repo"]
    local_music_workflow = configured_music_workflow["local"]
    stage07_cfg = provider_data.get("stage07_audio") if isinstance(provider_data.get("stage07_audio"), dict) else {}
    music_provider_name = str(stage07_cfg.get("music_provider") or "")
    fallback_music_allowed = music_provider_name == "local_library_or_comfyui"
    provider_backed_music_available = bool(
        not configured_music_workflow["mapping_error"]
        and repo_music_workflow["valid"]
        and bool(node_checks["music_generation"]["matches"])
    )
    smoke_ready = (
        (config_dir / "providers.yaml").exists()
        and (config_dir / "workflow_node_mapping.yaml").exists()
        and bool(openai_key_info["value"])
        and reachable
        and comfy_input_dir.exists()
        and comfy_input_dir.is_dir()
        and comfy_output_dir.exists()
        and comfy_output_dir.is_dir()
        and (
            repo_workflow_status["all_present"]
            if not fallback_music_allowed
            else all(
                repo_workflow_status["files"][name]["exists"]
                for name in BASE_EXPECTED_WORKFLOWS
            )
        )
        and bool(node_checks["ltx_video"]["matches"])
        and bool(node_checks["indextts2"]["matches"])
        and (fallback_music_allowed or provider_backed_music_available)
    )
    provider_backed_stage07_music_ready = bool(
        smoke_ready
        and provider_backed_music_available
    )

    result = {
        "repo_root": str(repo).replace("\\", "/"),
        "config": {
            "providers_yaml_exists": (config_dir / "providers.yaml").exists(),
            "workflow_mapping_exists": (config_dir / "workflow_node_mapping.yaml").exists(),
            "providers_example_exists": (config_dir / "providers.example.yaml").exists(),
            "workflow_mapping_example_exists": (config_dir / "workflow_node_mapping.example.yaml").exists(),
        },
        "openai": {
            "api_key_present": bool(openai_key_info["value"]),
            "api_key_source": openai_key_info["source"],
        },
        "comfyui": {
            "base_url": comfy_base_url,
            "reachable": reachable,
            "error": error,
            "paths": {
                "input_dir": str(comfy_input_dir).replace("\\", "/"),
                "input_dir_exists": comfy_input_dir.exists() and comfy_input_dir.is_dir(),
                "output_dir": str(comfy_output_dir).replace("\\", "/"),
                "output_dir_exists": comfy_output_dir.exists() and comfy_output_dir.is_dir(),
            },
            "fixed_entrypoints": {
                "comfy_python_cmd": str(comfy_python).replace("\\", "/"),
                "comfy_python_exists": comfy_python.exists(),
                "comfyui_api_py": str(comfy_api).replace("\\", "/"),
                "comfyui_api_exists": comfy_api.exists(),
            },
            "node_checks": node_checks,
        },
        "repo_workflows": repo_workflow_status,
        "local_workflows": local_workflow_status,
        "custom_nodes": custom_node_status(custom_nodes),
        "music_workflow": {
            "workflow_name": configured_music_workflow["workflow_name"],
            "mapping_path": configured_music_workflow["mapping_path"],
            "mapping_error": configured_music_workflow["mapping_error"],
            "workflow_filename": configured_music_workflow["workflow_filename"],
            "configured_repo_path": configured_music_workflow["repo_path"],
            "configured_local_path": configured_music_workflow["local_path"],
            "repo": repo_music_workflow,
            "local": local_music_workflow,
        },
        "fallback_music_allowed": fallback_music_allowed,
        "provider_backed_stage07_music_ready": provider_backed_stage07_music_ready,
        "ready_for_full_provider_backed_stage0509": bool(smoke_ready and provider_backed_stage07_music_ready),
    }
    result["ready_for_real_local_e2e"] = smoke_ready
    result["next_steps"] = build_next_steps(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    parser.add_argument("--comfy-base-url", default="http://127.0.0.1:8188")
    parser.add_argument("--local-workflow-root", default=r"F:\ComfyUI\Codex\workflows")
    parser.add_argument("--custom-nodes-root", default=r"F:\ComfyUI\ComfyUI\custom_nodes")
    parser.add_argument("--comfy-input-root", default=r"F:\ComfyUI\ComfyUI\input")
    parser.add_argument("--comfy-output-root", default=r"F:\ComfyUI\ComfyUI\output")
    args = parser.parse_args(argv)

    result = inspect_local_real_e2e_prereqs(
        comfy_base_url=args.comfy_base_url,
        local_workflow_root=Path(args.local_workflow_root),
        custom_nodes_root=Path(args.custom_nodes_root),
        comfy_input_root=Path(args.comfy_input_root),
        comfy_output_root=Path(args.comfy_output_root),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"READY_FOR_REAL_LOCAL_E2E: {result['ready_for_real_local_e2e']}")
        print(f"COMFYUI_REACHABLE: {result['comfyui']['reachable']}")
        print(f"OPENAI_API_KEY_PRESENT: {result['openai']['api_key_present']}")
        print(f"OPENAI_API_KEY_SOURCE: {result['openai']['api_key_source']}")
        print(f"REPO_WORKFLOWS_READY: {result['repo_workflows']['all_present']}")
        print(f"LOCAL_WORKFLOWS_READY: {result['local_workflows']['all_present']}")
        print(f"STAGE07_MUSIC_PROVIDER_READY: {result['provider_backed_stage07_music_ready']}")
        print(f"FULL_PROVIDER_BACKED_STAGE0509_READY: {result['ready_for_full_provider_backed_stage0509']}")
        for step in result["next_steps"]:
            print(f"NEXT: {step}")
    return 0 if result["ready_for_real_local_e2e"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
