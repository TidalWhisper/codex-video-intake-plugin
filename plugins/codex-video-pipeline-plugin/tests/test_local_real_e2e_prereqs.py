#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import yaml


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "scripts" / "providers"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


check_local_real_e2e_prereqs = load_module("check_local_real_e2e_prereqs_test", PROVIDERS / "check_local_real_e2e_prereqs.py")


def _touch(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_mapping(config_dir: Path, music_file: str = "AceStep_Music_Workflow.json") -> None:
    payload = {
        "workflows": {
            "music_generation": {
                "file": f"workflows/comfyui/{music_file}",
                "nodes": {
                    "seed": {"node_id": "109", "input_name": "value"},
                },
            },
        },
    }
    _touch(
        config_dir / "workflow_node_mapping.yaml",
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
    )


def _providers_payload() -> dict[str, object]:
    return yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))


def test_inspect_local_real_e2e_prereqs_reports_missing_items(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "config").mkdir(parents=True)
    (repo_root / "workflows" / "comfyui").mkdir(parents=True)
    local_workflow_root = tmp_path / "local_workflows"
    local_workflow_root.mkdir()
    custom_nodes_root = tmp_path / "custom_nodes"
    custom_nodes_root.mkdir()
    comfy_input_root = tmp_path / "comfy_input"
    comfy_output_root = tmp_path / "comfy_output"

    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "fetch_object_info",
        lambda base_url, timeout_seconds=10: (False, None, "connection refused"),
    )
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "discover_openai_api_key",
        lambda env_name="OPENAI_API_KEY", env=None: {"value": "", "source": "missing"},
    )
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "load_provider_config",
        lambda root=None, config_path=None: ({}, repo_root / "config" / "providers.yaml"),
    )
    result = check_local_real_e2e_prereqs.inspect_local_real_e2e_prereqs(
        repo_root=repo_root,
        local_workflow_root=local_workflow_root,
        custom_nodes_root=custom_nodes_root,
        comfy_input_root=comfy_input_root,
        comfy_output_root=comfy_output_root,
        env={},
    )
    assert result["ready_for_real_local_e2e"] is False
    assert result["config"]["providers_yaml_exists"] is False
    assert result["comfyui"]["reachable"] is False
    assert result["openai"]["api_key_source"] == "missing"
    assert result["next_steps"]


def test_inspect_local_real_e2e_prereqs_reports_ready_with_local_music_fallback(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    config_dir = repo_root / "config"
    repo_workflow_root = repo_root / "workflows" / "comfyui"
    local_workflow_root = tmp_path / "local_workflows"
    custom_nodes_root = tmp_path / "custom_nodes"
    comfy_input_root = tmp_path / "comfy_input"
    comfy_output_root = tmp_path / "comfy_output"
    config_dir.mkdir(parents=True)
    repo_workflow_root.mkdir(parents=True)
    local_workflow_root.mkdir()
    custom_nodes_root.mkdir()
    comfy_input_root.mkdir()
    comfy_output_root.mkdir()

    providers = _providers_payload()
    providers["stage07_audio"]["music_provider"] = "local_library_or_comfyui"
    (config_dir / "providers.yaml").write_text(yaml.safe_dump(providers, sort_keys=False, allow_unicode=True), encoding="utf-8")
    _write_mapping(config_dir)
    _touch(config_dir / "providers.example.yaml")
    _touch(config_dir / "workflow_node_mapping.example.yaml")
    for name in check_local_real_e2e_prereqs.EXPECTED_WORKFLOWS:
        _touch(repo_workflow_root / name, "{}")
        _touch(local_workflow_root / name, "{}")
    (custom_nodes_root / "ComfyUI-LTXVideo").mkdir()
    (custom_nodes_root / "comfyui-easy-indextts2").mkdir()

    object_info = {
        "LTXVImgToVideo": {},
        "ReferenceTimbreAudio": {},
        "SaveAudio": {},
    }
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "fetch_object_info",
        lambda base_url, timeout_seconds=10: (True, object_info, None),
    )
    auth_path = tmp_path / "auth-new.json"
    auth_path.write_text(json.dumps({"OPENAI_API_KEY": "test-key"}), encoding="utf-8")
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "discover_openai_api_key",
        lambda env_name="OPENAI_API_KEY", env=None: {"value": "test-key", "source": f"file:{auth_path}"},
    )
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "load_provider_config",
        lambda root=None, config_path=None: (providers, repo_root / "config" / "providers.yaml"),
    )
    result = check_local_real_e2e_prereqs.inspect_local_real_e2e_prereqs(
        repo_root=repo_root,
        local_workflow_root=local_workflow_root,
        custom_nodes_root=custom_nodes_root,
        comfy_input_root=comfy_input_root,
        comfy_output_root=comfy_output_root,
        env={},
    )
    assert result["ready_for_real_local_e2e"] is True
    assert result["repo_workflows"]["all_present"] is False
    assert result["provider_backed_stage07_music_ready"] is False
    assert result["ready_for_full_provider_backed_stage0509"] is False
    assert result["next_steps"] == []


def test_inspect_local_real_e2e_prereqs_reports_provider_backed_music_when_acestep_is_ready(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    config_dir = repo_root / "config"
    repo_workflow_root = repo_root / "workflows" / "comfyui"
    local_workflow_root = tmp_path / "local_workflows"
    custom_nodes_root = tmp_path / "custom_nodes"
    comfy_input_root = tmp_path / "comfy_input"
    comfy_output_root = tmp_path / "comfy_output"
    config_dir.mkdir(parents=True)
    repo_workflow_root.mkdir(parents=True)
    local_workflow_root.mkdir()
    custom_nodes_root.mkdir()
    comfy_input_root.mkdir()
    comfy_output_root.mkdir()

    providers = _providers_payload()
    (config_dir / "providers.yaml").write_text(yaml.safe_dump(providers, sort_keys=False, allow_unicode=True), encoding="utf-8")
    _write_mapping(config_dir)
    _touch(config_dir / "providers.example.yaml")
    _touch(config_dir / "workflow_node_mapping.example.yaml")
    for name in check_local_real_e2e_prereqs.EXPECTED_WORKFLOWS:
        _touch(repo_workflow_root / name, "{}")
        _touch(local_workflow_root / name, "{}")
    acestep_payload = json.dumps(
        {
            "94": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {"lyrics": "", "tags": ""}},
            "109": {"class_type": "PrimitiveInt", "inputs": {"value": 1}},
        }
    )
    _touch(repo_workflow_root / "AceStep_Music_Workflow.json", acestep_payload)
    _touch(local_workflow_root / "AceStep_Music_Workflow.json", acestep_payload)
    (custom_nodes_root / "ComfyUI-LTXVideo").mkdir()
    (custom_nodes_root / "comfyui-easy-indextts2").mkdir()

    object_info = {
        "LTXVImgToVideo": {},
        "ReferenceTimbreAudio": {},
        "TextEncodeAceStepAudio1.5": {},
        "SaveAudio": {},
    }
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "fetch_object_info",
        lambda base_url, timeout_seconds=10: (True, object_info, None),
    )
    auth_path = tmp_path / "auth-new.json"
    auth_path.write_text(json.dumps({"OPENAI_API_KEY": "test-key"}), encoding="utf-8")
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "discover_openai_api_key",
        lambda env_name="OPENAI_API_KEY", env=None: {"value": "test-key", "source": f"file:{auth_path}"},
    )
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "load_provider_config",
        lambda root=None, config_path=None: (providers, repo_root / "config" / "providers.yaml"),
    )
    result = check_local_real_e2e_prereqs.inspect_local_real_e2e_prereqs(
        repo_root=repo_root,
        local_workflow_root=local_workflow_root,
        custom_nodes_root=custom_nodes_root,
        comfy_input_root=comfy_input_root,
        comfy_output_root=comfy_output_root,
        env={},
    )
    assert result["ready_for_real_local_e2e"] is True
    assert result["provider_backed_stage07_music_ready"] is True
    assert result["ready_for_full_provider_backed_stage0509"] is True


def test_check_local_real_e2e_prereqs_cli_json(tmp_path: Path, monkeypatch, capsys) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "config").mkdir(parents=True)
    (repo_root / "workflows" / "comfyui").mkdir(parents=True)
    monkeypatch.setattr(check_local_real_e2e_prereqs, "root_dir", lambda: repo_root)
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "fetch_object_info",
        lambda base_url, timeout_seconds=10: (False, None, "connection refused"),
    )
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "discover_openai_api_key",
        lambda env_name="OPENAI_API_KEY", env=None: {"value": "", "source": "missing"},
    )
    monkeypatch.setattr(
        check_local_real_e2e_prereqs,
        "load_provider_config",
        lambda root=None, config_path=None: ({}, repo_root / "config" / "providers.yaml"),
    )
    assert check_local_real_e2e_prereqs.main([
        "--json",
        "--local-workflow-root", str(tmp_path / "wf"),
        "--custom-nodes-root", str(tmp_path / "nodes"),
        "--comfy-input-root", str(tmp_path / "input"),
        "--comfy-output-root", str(tmp_path / "output"),
    ]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ready_for_real_local_e2e"] is False
