#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "scripts" / "providers"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bootstrap_local_real_e2e_setup = load_module("bootstrap_local_real_e2e_setup_test", PROVIDERS / "bootstrap_local_real_e2e_setup.py")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _prepare_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    config_dir = repo_root / "config"
    workflow_dir = repo_root / "workflows" / "comfyui"
    config_dir.mkdir(parents=True)
    workflow_dir.mkdir(parents=True)
    _write_text(
        config_dir / "providers.example.yaml",
        "project_root: ./video_projects\nopenai_image:\n  enabled: false\n  provider_name: openai_gpt_image2\n  model: gpt-image-2\n  base_url: https://api.openai.com/v1\n  api_key_env: OPENAI_API_KEY\n  output_format: png\n  quality: high\n  background: auto\n  timeout_seconds: 180\n  retry_count: 2\ncomfyui:\n  enabled: false\n  base_url: http://127.0.0.1:8188\n  timeout_seconds: 600\n  retry_count: 1\n  input_dir: ''\n  output_dir: ''\nstage05_keyframe_images:\n  provider_priority:\n    - openai_gpt_image2\n    - comfyui_txt2img\n  fallback_on_failure: true\nstage06_video_clips:\n  provider_priority:\n    - comfyui_ltx_i2v\n  clip_duration_sec_min: 5\n  clip_duration_sec_max: 15\n  fps: 24\nstage07_audio:\n  voice_provider: comfyui_indextts2\n  music_provider: comfyui_music\n",
    )
    _write_text(config_dir / "workflow_node_mapping.example.yaml", "workflows: {}\n")
    local_workflow_root = tmp_path / "local_workflows"
    local_workflow_root.mkdir()
    return repo_root, local_workflow_root


def test_bootstrap_local_real_e2e_setup_dry_run(tmp_path: Path, monkeypatch) -> None:
    repo_root, local_workflow_root = _prepare_repo(tmp_path)
    monkeypatch.setattr(bootstrap_local_real_e2e_setup, "discover_openai_api_key", lambda env_name="OPENAI_API_KEY", env=None: {"value": "", "source": "missing"})
    result = bootstrap_local_real_e2e_setup.bootstrap_local_real_e2e_setup(
        repo_root=repo_root,
        local_workflow_root=local_workflow_root,
        env={},
        write=False,
    )
    assert result["write_mode"] is False
    assert result["openai_api_key_present"] is False
    assert result["openai_api_key_source"] == "missing"
    assert not (repo_root / "config" / "providers.yaml").exists()
    assert result["actions"][0]["written"] is False


def test_bootstrap_local_real_e2e_setup_write_mode_creates_files_and_copies_workflows(tmp_path: Path, monkeypatch) -> None:
    repo_root, local_workflow_root = _prepare_repo(tmp_path)
    for name in bootstrap_local_real_e2e_setup.EXPECTED_WORKFLOWS:
        _write_text(local_workflow_root / name, "{}")
    monkeypatch.setattr(bootstrap_local_real_e2e_setup, "discover_openai_api_key", lambda env_name="OPENAI_API_KEY", env=None: {"value": "test-key", "source": "env:OPENAI_API_KEY"})
    result = bootstrap_local_real_e2e_setup.bootstrap_local_real_e2e_setup(
        repo_root=repo_root,
        local_workflow_root=local_workflow_root,
        env={"OPENAI_API_KEY": "test-key"},
        write=True,
    )
    providers_yaml = repo_root / "config" / "providers.yaml"
    assert providers_yaml.exists()
    providers_text = providers_yaml.read_text(encoding="utf-8")
    assert "enabled: true" in providers_text
    assert "http://127.0.0.1:8188" in providers_text
    assert "input_dir:" in providers_text
    assert "output_dir:" in providers_text
    assert (repo_root / "config" / "workflow_node_mapping.yaml").exists()
    for name in bootstrap_local_real_e2e_setup.EXPECTED_WORKFLOWS:
        assert (repo_root / "workflows" / "comfyui" / name).exists()
    assert any(item["written"] for item in result["workflow_copies"])


def test_bootstrap_local_real_e2e_setup_cli_json(tmp_path: Path, monkeypatch, capsys) -> None:
    repo_root, local_workflow_root = _prepare_repo(tmp_path)
    monkeypatch.setattr(bootstrap_local_real_e2e_setup, "root_dir", lambda: repo_root)
    monkeypatch.setattr(bootstrap_local_real_e2e_setup, "discover_openai_api_key", lambda env_name="OPENAI_API_KEY", env=None: {"value": "", "source": "missing"})
    assert bootstrap_local_real_e2e_setup.main(["--json", "--local-workflow-root", str(local_workflow_root)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["write_mode"] is False
