#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from comfyui_client import ComfyUIError, load_workflow_json

KNOWN_PLUGIN_ROOT_CHILDREN = {
    "video_projects",
    "templates",
    "config",
    "workflows",
    "skills",
    "scripts",
    "tests",
    "docs",
    "prompts",
}

KNOWN_REFERENCE_GUIDANCE_FIELDS = {
    "reference_image",
    "reference_images",
    "reference_image_path",
    "reference_image_paths",
    "reference_image_name",
    "reference_image_names",
    "reference_latent",
    "reference_latents",
    "init_image",
    "init_image_path",
    "image_input",
}


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _plugin_root_candidates(root: str | Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()
    for base in [Path(root).resolve()] if root else []:
        key = str(base).lower()
        if key not in seen:
            candidates.append(base)
            seen.add(key)
    cwd = Path.cwd().resolve()
    for anchor in [cwd, *cwd.parents]:
        if anchor.name != "codex-video-pipeline-plugin":
            continue
        key = str(anchor).lower()
        if key not in seen:
            candidates.append(anchor)
            seen.add(key)
    default_root = root_dir().resolve()
    key = str(default_root).lower()
    if key not in seen:
        candidates.append(default_root)
    return candidates


def _resolve_relative_path(path: Path, *, root: str | Path | None = None) -> Path:
    if path.exists():
        return path.resolve()
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    plugin_roots = _plugin_root_candidates(root=root)
    special_roots: list[Path] = []
    if path.parts:
        first = path.parts[0].lower()
        for plugin_root in plugin_roots:
            repo_root = plugin_root.parent.parent.resolve() if plugin_root.parent.name == "plugins" else None
            if first == "plugins" and repo_root is not None:
                special_roots.append(repo_root)
            elif first in KNOWN_PLUGIN_ROOT_CHILDREN:
                special_roots.append(plugin_root)
    for anchor in [*special_roots, *plugin_roots]:
        candidate = (anchor / path).resolve()
        if candidate.exists():
            return candidate
    return (plugin_roots[0] / path).resolve()


def resolve_workflow_mapping_path(mapping_path: str | Path | None = None, root: str | Path | None = None) -> Path:
    if mapping_path is not None:
        path = Path(mapping_path)
        return path.resolve() if path.is_absolute() else _resolve_relative_path(path, root=root)
    base = Path(root) if root else root_dir()
    return (base / "config" / "workflow_node_mapping.yaml").resolve()


def load_workflow_mapping(mapping_path: str | Path | None = None, root: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    path = resolve_workflow_mapping_path(mapping_path=mapping_path, root=root)
    if not path.exists():
        raise ComfyUIError(
            f"workflow node mapping not found: {path}. Copy config/workflow_node_mapping.example.yaml to config/workflow_node_mapping.yaml and edit locally.",
            kind="mapping_missing",
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ComfyUIError(f"workflow node mapping is not valid YAML: {path}", kind="mapping_invalid") from exc
    if not isinstance(data, dict):
        raise ComfyUIError(f"workflow node mapping root must be an object: {path}", kind="mapping_invalid")
    return data, path


def get_workflow_mapping(data: dict[str, Any], workflow_name: str) -> dict[str, Any]:
    workflows = data.get("workflows")
    if not isinstance(workflows, dict):
        raise ComfyUIError("workflow node mapping must contain a top-level 'workflows' object", kind="mapping_invalid")
    entry = workflows.get(workflow_name)
    if not isinstance(entry, dict):
        raise ComfyUIError(f"workflow mapping missing entry for '{workflow_name}'", kind="mapping_missing")
    workflow_file = entry.get("file")
    nodes = entry.get("nodes")
    if not isinstance(workflow_file, str) or not workflow_file.strip():
        raise ComfyUIError(f"workflow mapping '{workflow_name}' must define a non-empty file path", kind="mapping_invalid")
    if not isinstance(nodes, dict) or not nodes:
        raise ComfyUIError(f"workflow mapping '{workflow_name}' must define a non-empty nodes object", kind="mapping_invalid")
    return entry


def resolve_workflow_capabilities(entry: dict[str, Any]) -> dict[str, Any]:
    nodes = entry.get("nodes") if isinstance(entry.get("nodes"), dict) else {}
    capabilities = entry.get("capabilities") if isinstance(entry.get("capabilities"), dict) else {}

    supports_reference_images = capabilities.get("supports_reference_images")
    if not isinstance(supports_reference_images, bool):
        supports_reference_images = any(field_name in KNOWN_REFERENCE_GUIDANCE_FIELDS for field_name in nodes.keys())

    supported_control_modes = capabilities.get("supported_control_modes")
    if not isinstance(supported_control_modes, list) or not all(isinstance(item, str) and item.strip() for item in supported_control_modes):
        supported_control_modes = ["prompt_only"]
        if supports_reference_images:
            supported_control_modes.append("reference_guided")
    else:
        seen: set[str] = set()
        normalized_modes: list[str] = []
        for item in supported_control_modes:
            mode = str(item).strip()
            if not mode or mode in seen:
                continue
            normalized_modes.append(mode)
            seen.add(mode)
        supported_control_modes = normalized_modes or (
            ["prompt_only", "reference_guided"] if supports_reference_images else ["prompt_only"]
        )

    return {
        "supports_reference_images": bool(supports_reference_images),
        "supported_control_modes": supported_control_modes,
    }


def load_mapped_workflow(mapping_data: dict[str, Any], workflow_name: str, root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Path]:
    entry = get_workflow_mapping(mapping_data, workflow_name)
    base = Path(root) if root else root_dir()
    workflow_path = (base / str(entry["file"])).resolve()
    workflow = load_workflow_json(workflow_path)
    return workflow, entry, workflow_path


def _normalized_node_specs(nodes: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
    if field_name not in nodes:
        raise ComfyUIError(f"workflow mapping missing node entry for '{field_name}'", kind="mapping_missing")
    node_spec = nodes[field_name]
    if isinstance(node_spec, dict):
        return [node_spec]
    if isinstance(node_spec, list) and node_spec and all(isinstance(item, dict) for item in node_spec):
        return node_spec
    raise ComfyUIError(
        f"workflow mapping for '{field_name}' must be an object or non-empty list of objects",
        kind="mapping_invalid",
    )


def apply_node_inputs(workflow: dict[str, Any], nodes: dict[str, Any], replacements: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(workflow)
    for field_name, value in replacements.items():
        for node_spec in _normalized_node_specs(nodes, field_name):
            node_id = node_spec.get("node_id")
            input_name = node_spec.get("input_name")
            if not isinstance(node_id, str) or not node_id.strip():
                raise ComfyUIError(f"workflow mapping for '{field_name}' must include node_id", kind="mapping_invalid")
            if not isinstance(input_name, str) or not input_name.strip():
                raise ComfyUIError(f"workflow mapping for '{field_name}' must include input_name", kind="mapping_invalid")
            node = updated.get(node_id)
            if not isinstance(node, dict):
                raise ComfyUIError(f"workflow node '{node_id}' for '{field_name}' was not found in workflow JSON", kind="workflow_invalid")
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                raise ComfyUIError(f"workflow node '{node_id}' for '{field_name}' does not have an inputs object", kind="workflow_invalid")
            if input_name not in inputs:
                raise ComfyUIError(
                    f"workflow node '{node_id}' for '{field_name}' does not expose input '{input_name}'",
                    kind="workflow_invalid",
                )
            inputs[input_name] = value
    return updated
