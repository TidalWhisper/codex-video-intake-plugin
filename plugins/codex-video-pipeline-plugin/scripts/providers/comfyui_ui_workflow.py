#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from comfyui_client import ComfyUIError


def resolve_workflow_format(entry: dict[str, Any]) -> str:
    workflow_format = str(entry.get("workflow_format") or "api_workflow").strip()
    return workflow_format or "api_workflow"


def _ui_nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        raise ComfyUIError("UI workflow root must contain a 'nodes' list", kind="workflow_invalid")
    return nodes


def _find_ui_node(nodes: list[dict[str, Any]], node_id: str | int, *, field_name: str) -> dict[str, Any]:
    target = str(node_id).strip()
    for node in nodes:
        if str(node.get("id")) == target:
            return node
    raise ComfyUIError(
        f"UI workflow node '{target}' for '{field_name}' was not found in workflow JSON",
        kind="workflow_invalid",
    )


def _ensure_widget_values(node: dict[str, Any], *, field_name: str) -> list[Any]:
    widget_values = node.get("widgets_values")
    if not isinstance(widget_values, list):
        raise ComfyUIError(
            f"UI workflow node '{node.get('id')}' for '{field_name}' does not expose widget values",
            kind="workflow_invalid",
        )
    return widget_values


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


def _copy_widget_value_from_choice(
    ui_nodes: list[dict[str, Any]],
    node_spec: dict[str, Any],
    choice_value: Any,
    *,
    field_name: str,
) -> Any:
    choices = node_spec.get("choices")
    if not isinstance(choices, dict) or not choices:
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' must define a non-empty choices object",
            kind="mapping_invalid",
        )
    choice_key = str(choice_value or node_spec.get("default_choice") or "").strip()
    if not choice_key:
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' did not receive a choice and has no default_choice",
            kind="mapping_invalid",
        )
    choice_spec = choices.get(choice_key)
    if not isinstance(choice_spec, dict):
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' received unknown choice '{choice_key}'",
            kind="mapping_invalid",
        )
    source_node_id = choice_spec.get("node_id")
    if source_node_id is None:
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' choice '{choice_key}' must include node_id",
            kind="mapping_invalid",
        )
    source_widget_index = int(choice_spec.get("widget_index") or 0)
    source_node = _find_ui_node(ui_nodes, source_node_id, field_name=field_name)
    source_widget_values = _ensure_widget_values(source_node, field_name=field_name)
    if source_widget_index < 0 or source_widget_index >= len(source_widget_values):
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' choice '{choice_key}' references widget index {source_widget_index}, "
            f"but node '{source_node_id}' only exposes {len(source_widget_values)} widget values",
            kind="workflow_invalid",
        )
    return copy.deepcopy(source_widget_values[source_widget_index])


def _normalized_choice_node_ids(value: Any, *, field_name: str, choice_key: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, int)):
        text = str(value).strip()
        return [text] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if not isinstance(item, (str, int)):
                raise ComfyUIError(
                    f"UI workflow mapping for '{field_name}' choice '{choice_key}' must use scalar node ids",
                    kind="mapping_invalid",
                )
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    raise ComfyUIError(
        f"UI workflow mapping for '{field_name}' choice '{choice_key}' must define node ids as a scalar or list",
        kind="mapping_invalid",
    )


def _set_modes_from_choice(
    ui_nodes: list[dict[str, Any]],
    node_spec: dict[str, Any],
    choice_value: Any,
    *,
    field_name: str,
) -> None:
    choices = node_spec.get("choices")
    if not isinstance(choices, dict) or not choices:
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' must define a non-empty choices object",
            kind="mapping_invalid",
        )
    choice_key = str(choice_value or node_spec.get("default_choice") or "").strip()
    if not choice_key:
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' did not receive a choice and has no default_choice",
            kind="mapping_invalid",
        )
    choice_spec = choices.get(choice_key)
    if not isinstance(choice_spec, dict):
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' received unknown choice '{choice_key}'",
            kind="mapping_invalid",
        )
    enable_mode = int(node_spec.get("enable_mode") or 0)
    disable_mode = int(node_spec.get("disable_mode") or 2)
    all_choice_node_ids = _normalized_choice_node_ids(
        node_spec.get("all_choice_node_ids"),
        field_name=field_name,
        choice_key=choice_key,
    )
    if not all_choice_node_ids:
        seen_ids: list[str] = []
        for key, item in choices.items():
            if not isinstance(item, dict):
                raise ComfyUIError(
                    f"UI workflow mapping for '{field_name}' choice '{key}' must be an object",
                    kind="mapping_invalid",
                )
            node_ids = _normalized_choice_node_ids(
                item.get("enable_node_ids", item.get("node_id")),
                field_name=field_name,
                choice_key=key,
            )
            for node_id in node_ids:
                if node_id not in seen_ids:
                    seen_ids.append(node_id)
        all_choice_node_ids = seen_ids
    enable_node_ids = _normalized_choice_node_ids(
        choice_spec.get("enable_node_ids", choice_spec.get("node_id")),
        field_name=field_name,
        choice_key=choice_key,
    )
    if not enable_node_ids:
        raise ComfyUIError(
            f"UI workflow mapping for '{field_name}' choice '{choice_key}' must include node_id or enable_node_ids",
            kind="mapping_invalid",
        )
    for node_id in all_choice_node_ids:
        target_node = _find_ui_node(ui_nodes, node_id, field_name=field_name)
        target_node["mode"] = disable_mode
    for node_id in enable_node_ids:
        target_node = _find_ui_node(ui_nodes, node_id, field_name=field_name)
        target_node["mode"] = enable_mode


def apply_ui_node_inputs(workflow: dict[str, Any], nodes: dict[str, Any], replacements: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(workflow)
    ui_nodes = _ui_nodes(updated)
    for field_name, value in replacements.items():
        for node_spec in _normalized_node_specs(nodes, field_name):
            node_id = node_spec.get("node_id")
            if node_id is None:
                raise ComfyUIError(
                    f"UI workflow mapping for '{field_name}' must include node_id",
                    kind="mapping_invalid",
                )
            control = str(node_spec.get("control") or "widget_value").strip()
            target_node = _find_ui_node(ui_nodes, node_id, field_name=field_name)
            if control == "choice_set_mode":
                _set_modes_from_choice(
                    ui_nodes,
                    node_spec,
                    value,
                    field_name=field_name,
                )
                continue
            widget_index = int(node_spec.get("widget_index") or 0)
            widget_values = _ensure_widget_values(target_node, field_name=field_name)
            if widget_index < 0 or widget_index >= len(widget_values):
                raise ComfyUIError(
                    f"UI workflow mapping for '{field_name}' references widget index {widget_index}, "
                    f"but node '{node_id}' only exposes {len(widget_values)} widget values",
                    kind="workflow_invalid",
                )
            if control == "widget_value":
                widget_values[widget_index] = value
                continue
            if control == "choice_copy_widget_value":
                widget_values[widget_index] = _copy_widget_value_from_choice(
                    ui_nodes,
                    node_spec,
                    value,
                    field_name=field_name,
                )
                continue
            raise ComfyUIError(
                f"UI workflow mapping for '{field_name}' uses unsupported control '{control}'",
                kind="mapping_invalid",
            )
    return updated


def convert_ui_workflow_to_prompt(
    workflow: dict[str, Any],
    *,
    base_url: str,
    script_path: str | Path | None = None,
    node_modules_dir: str | Path | None = None,
) -> dict[str, Any]:
    resolved_script_path = Path(script_path).resolve() if script_path else (Path(__file__).resolve().parent / "convert_comfyui_ui_graph_playwright.mjs")
    if not resolved_script_path.exists():
        raise ComfyUIError(
            f"UI workflow conversion script not found: {resolved_script_path}",
            kind="workflow_invalid",
        )
    env = os.environ.copy()
    if node_modules_dir:
        env["PLAYWRIGHT_NODE_MODULES_DIR"] = str(Path(node_modules_dir).resolve())
    with tempfile.TemporaryDirectory(prefix="comfyui-ui-graph-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        workflow_path = tmp_root / "workflow.json"
        output_path = tmp_root / "converted.json"
        workflow_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
        completed = subprocess.run(
            [
                "node",
                str(resolved_script_path),
                "--workflow",
                str(workflow_path),
                "--output",
                str(output_path),
                "--url",
                str(base_url).rstrip("/"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout or f"exit code {completed.returncode}"
            raise ComfyUIError(
                f"UI workflow conversion failed: {detail}",
                kind="workflow_invalid",
                details={
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": completed.returncode,
                },
            )
        if not output_path.exists():
            raise ComfyUIError(
                f"UI workflow conversion did not produce output JSON: {output_path}",
                kind="workflow_invalid",
            )
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ComfyUIError(
                f"UI workflow conversion output was not valid JSON: {output_path}",
                kind="workflow_invalid",
            ) from exc
    if not isinstance(data, dict):
        raise ComfyUIError(
            "UI workflow conversion result root must be a JSON object",
            kind="workflow_invalid",
            details=data,
        )
    output = data.get("output")
    if not isinstance(output, dict) or not output:
        raise ComfyUIError(
            "UI workflow conversion result did not include a non-empty output prompt",
            kind="workflow_invalid",
            details=data,
        )
    workflow_metadata = data.get("workflow") if isinstance(data.get("workflow"), dict) else workflow
    return {
        "prompt": output,
        "extra_data": {
            "extra_pnginfo": {
                "workflow": workflow_metadata,
            }
        },
    }
