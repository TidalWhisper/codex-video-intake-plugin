#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from check_local_real_e2e_prereqs import EXPECTED_WORKFLOWS
from provider_config import discover_openai_api_key, root_dir


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise RuntimeError(f"YAML root must be an object: {path}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def copy_if_missing(src: Path, dst: Path, *, write: bool) -> dict[str, Any]:
    action = {
        "source": str(src).replace("\\", "/"),
        "target": str(dst).replace("\\", "/"),
        "written": False,
        "skipped": False,
        "reason": None,
    }
    if dst.exists():
        action["skipped"] = True
        action["reason"] = "target_exists"
        return action
    if not write:
        action["reason"] = "dry_run"
        return action
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    action["written"] = True
    return action


def bootstrap_local_real_e2e_setup(
    *,
    repo_root: Path | None = None,
    local_workflow_root: Path | None = None,
    env: dict[str, str] | None = None,
    write: bool = False,
) -> dict[str, Any]:
    repo = repo_root or root_dir()
    env_map = env or os.environ
    config_dir = repo / "config"
    workflow_dir = repo / "workflows" / "comfyui"
    providers_example = config_dir / "providers.example.yaml"
    providers_yaml = config_dir / "providers.yaml"
    mapping_example = config_dir / "workflow_node_mapping.example.yaml"
    mapping_yaml = config_dir / "workflow_node_mapping.yaml"
    local_workflows = local_workflow_root or Path(r"F:\ComfyUI\Codex\workflows")
    comfy_input_dir = Path(r"F:\ComfyUI\ComfyUI\input")
    comfy_output_dir = Path(r"F:\ComfyUI\ComfyUI\output")

    actions: list[dict[str, Any]] = []

    providers_data = load_yaml(providers_example)
    openai_key_info = discover_openai_api_key(env=env_map)
    openai_key_present = bool(openai_key_info["value"])
    providers_data.setdefault("openai_image", {})
    providers_data["openai_image"]["enabled"] = openai_key_present
    providers_data["openai_image"]["base_url"] = str(providers_data["openai_image"].get("base_url") or "https://api.openai.com/v1")
    providers_data.setdefault("comfyui", {})
    providers_data["comfyui"]["enabled"] = True
    providers_data["comfyui"]["base_url"] = "http://127.0.0.1:8188"
    providers_data["comfyui"]["input_dir"] = str(comfy_input_dir).replace("\\", "/") if comfy_input_dir.exists() else ""
    providers_data["comfyui"]["output_dir"] = str(comfy_output_dir).replace("\\", "/") if comfy_output_dir.exists() else ""
    stage05 = providers_data.setdefault("stage05_keyframe_images", {})
    stage05["provider_priority"] = ["comfyui_txt2img"]

    if write:
        write_yaml(providers_yaml, providers_data)
        actions.append({
            "type": "write_yaml",
            "target": str(providers_yaml).replace("\\", "/"),
            "written": True,
        })
    else:
        actions.append({
            "type": "write_yaml",
            "target": str(providers_yaml).replace("\\", "/"),
            "written": False,
            "reason": "dry_run",
        })

    actions.append(copy_if_missing(mapping_example, mapping_yaml, write=write))

    copied_workflows: list[dict[str, Any]] = []
    for name in EXPECTED_WORKFLOWS:
        src = local_workflows / name
        dst = workflow_dir / name
        item = {
            "source": str(src).replace("\\", "/"),
            "target": str(dst).replace("\\", "/"),
            "exists_in_local": src.exists() and src.is_file() and src.stat().st_size > 0,
            "written": False,
            "reason": None,
        }
        if item["exists_in_local"]:
            if write:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                item["written"] = True
            else:
                item["reason"] = "dry_run"
        else:
            item["reason"] = "missing_in_local_workflow_root"
        copied_workflows.append(item)

    return {
        "repo_root": str(repo).replace("\\", "/"),
        "write_mode": write,
        "openai_api_key_present": openai_key_present,
        "openai_api_key_source": openai_key_info["source"],
        "actions": actions,
        "workflow_copies": copied_workflows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Actually write config files and copy workflows")
    parser.add_argument("--local-workflow-root", default=r"F:\ComfyUI\Codex\workflows")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = bootstrap_local_real_e2e_setup(
        local_workflow_root=Path(args.local_workflow_root),
        write=args.write,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"WRITE_MODE: {result['write_mode']}")
        print(f"OPENAI_API_KEY_PRESENT: {result['openai_api_key_present']}")
        print(f"OPENAI_API_KEY_SOURCE: {result['openai_api_key_source']}")
        for action in result["actions"]:
            target = action.get("target")
            written = action.get("written")
            reason = action.get("reason")
            print(f"ACTION: target={target} written={written} reason={reason}")
        for item in result["workflow_copies"]:
            print(
                "WORKFLOW_COPY:"
                f" source={item['source']}"
                f" target={item['target']}"
                f" exists_in_local={item['exists_in_local']}"
                f" written={item['written']}"
                f" reason={item['reason']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
