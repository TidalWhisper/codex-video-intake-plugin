#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from comfyui_client import ComfyUIError, load_workflow_json


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_workflow_mapping_path(mapping_path: str | Path | None = None, root: str | Path | None = None) -> Path:
    if mapping_path is not None:
        path = Path(mapping_path)
        return path if path.is_absolute() else (Path(root) if root else root_dir()).joinpath(path).resolve()
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


def load_mapped_workflow(mapping_data: dict[str, Any], workflow_name: str, root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Path]:
    entry = get_workflow_mapping(mapping_data, workflow_name)
    base = Path(root) if root else root_dir()
    workflow_path = (base / str(entry["file"])).resolve()
    workflow = load_workflow_json(workflow_path)
    return workflow, entry, workflow_path


def apply_node_inputs(workflow: dict[str, Any], nodes: dict[str, Any], replacements: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(workflow)
    for field_name, value in replacements.items():
        if field_name not in nodes:
            raise ComfyUIError(f"workflow mapping missing node entry for '{field_name}'", kind="mapping_missing")
        node_spec = nodes[field_name]
        if not isinstance(node_spec, dict):
            raise ComfyUIError(f"workflow mapping for '{field_name}' must be an object", kind="mapping_invalid")
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
        inputs[input_name] = value
    return updated
