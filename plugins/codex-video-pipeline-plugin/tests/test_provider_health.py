#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "scripts" / "providers"
if str(PROVIDERS) not in sys.path:
    sys.path.insert(0, str(PROVIDERS))

import check_comfyui_server as check_comfyui_server_cli
import check_openai_image_provider as check_openai_image_provider_cli
import check_provider_config as check_provider_config_cli
import check_provider_health as check_provider_health_cli
import provider_config


class _StatsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/system_stats":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"system": {"os": "test"}, "devices": []}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _write_config(tmp_path: Path, *, openai_enabled: bool = False, comfyui_enabled: bool = False, base_url: str = "http://127.0.0.1:8188") -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = openai_enabled
    data["comfyui"]["enabled"] = comfyui_enabled
    data["comfyui"]["base_url"] = base_url
    config_path = tmp_path / "providers.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def _write_repo_config(repo_root: Path, *, openai_enabled: bool = False, comfyui_enabled: bool = False, base_url: str = "http://127.0.0.1:8188") -> Path:
    (repo_root / "config").mkdir(parents=True, exist_ok=True)
    (repo_root / "workflows" / "comfyui").mkdir(parents=True, exist_ok=True)
    return _write_config(repo_root / "config", openai_enabled=openai_enabled, comfyui_enabled=comfyui_enabled, base_url=base_url)


def _write_workflow_mapping(repo_root: Path, music_file: str, seed_node: str = "109", seed_input: str = "value") -> None:
    mapping = {
        "workflows": {
            "music_generation": {
                "file": f"workflows/comfyui/{music_file}",
                "nodes": {
                    "seed": {"node_id": seed_node, "input_name": seed_input},
                },
            },
        },
    }
    (repo_root / "config" / "workflow_node_mapping.yaml").write_text(
        yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def test_validate_provider_config_example_is_valid() -> None:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    errors = provider_config.validate_provider_config(data)
    assert errors == []


def test_check_provider_config_cli_accepts_example(tmp_path: Path, capsys) -> None:
    config_path = _write_config(tmp_path)
    assert check_provider_config_cli.main(["--config", str(config_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["openai_enabled"] is False
    assert payload["comfyui_enabled"] is False


def test_check_openai_image_provider_reports_disabled_when_disabled(tmp_path: Path, capsys) -> None:
    config_path = _write_config(tmp_path, openai_enabled=False)
    assert check_openai_image_provider_cli.main(["--config", str(config_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "disabled"
    assert payload["ready"] is False


def test_check_openai_image_provider_fails_when_enabled_without_api_key(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = _write_config(tmp_path, openai_enabled=True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(provider_config, "AUTH_FILE_CANDIDATES", [])
    assert check_openai_image_provider_cli.main(["--config", str(config_path), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "missing_api_key"
    assert payload["api_key_present"] is False


def test_check_openai_image_provider_succeeds_when_enabled_with_api_key(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = _write_config(tmp_path, openai_enabled=True)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert check_openai_image_provider_cli.main(["--config", str(config_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["api_key_present"] is True
    assert payload["api_key_source"] == "env:OPENAI_API_KEY"


def test_check_openai_image_provider_uses_codex_auth_file_when_env_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = _write_config(tmp_path, openai_enabled=True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    auth_path = tmp_path / "auth-new.json"
    auth_path.write_text(json.dumps({"OPENAI_API_KEY": "auth-file-key"}), encoding="utf-8")
    monkeypatch.setattr(provider_config, "AUTH_FILE_CANDIDATES", [auth_path])
    assert check_openai_image_provider_cli.main(["--config", str(config_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ready"
    assert payload["api_key_present"] is True
    assert payload["api_key_source"].startswith("file:")


def test_check_comfyui_server_reports_disabled_when_disabled(tmp_path: Path, capsys) -> None:
    config_path = _write_config(tmp_path, comfyui_enabled=False)
    assert check_comfyui_server_cli.main(["--config", str(config_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "disabled"


def test_check_comfyui_server_succeeds_against_fake_server(tmp_path: Path, capsys) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StatsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config_path = _write_config(tmp_path, comfyui_enabled=True, base_url=f"http://127.0.0.1:{server.server_port}")
        assert check_comfyui_server_cli.main(["--config", str(config_path), "--json", "--timeout", "2"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "ready"
        assert payload["http_status"] == 200
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_check_provider_health_fails_when_enabled_provider_is_not_ready(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = _write_config(tmp_path, openai_enabled=True, comfyui_enabled=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(provider_config, "AUTH_FILE_CANDIDATES", [])
    assert check_provider_health_cli.main(["--config", str(config_path), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid_config"] is True
    assert payload["openai_image"]["status"] == "missing_api_key"


def test_check_provider_health_reports_stage07_music_ready_for_acestep(tmp_path: Path, capsys) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StatsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        repo_root = tmp_path / "repo"
        config_path = _write_repo_config(repo_root, comfyui_enabled=True, base_url=f"http://127.0.0.1:{server.server_port}")
        _write_workflow_mapping(repo_root, "AceStep_Music_Workflow.json")
        workflow_path = repo_root / "workflows" / "comfyui" / "AceStep_Music_Workflow.json"
        workflow_path.write_text(
            json.dumps(
                {
                    "94": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {"lyrics": "x", "tags": "y"}},
                    "107": {"class_type": "SaveAudioMP3", "inputs": {"audio": ["18", 0]}},
                    "109": {"class_type": "PrimitiveInt", "inputs": {"value": 123}},
                }
            ),
            encoding="utf-8",
        )
        assert check_provider_health_cli.main(["--config", str(config_path), "--json", "--timeout", "2"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["comfyui"]["status"] == "ready"
        assert payload["stage07_music"]["provider_backed_ready"] is True
        assert payload["warnings"] == []
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_check_provider_health_accepts_workspace_relative_plugin_config_path(tmp_path: Path, monkeypatch, capsys) -> None:
    workspace_root = tmp_path / "workspace"
    plugin_root = workspace_root / "plugins" / "codex-video-pipeline-plugin"
    config_path = _write_repo_config(plugin_root, openai_enabled=False, comfyui_enabled=False)
    _write_workflow_mapping(plugin_root, "AceStep_Music_Workflow.json")
    workflow_path = plugin_root / "workflows" / "comfyui" / "AceStep_Music_Workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "94": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {"lyrics": "x", "tags": "y"}},
                "109": {"class_type": "PrimitiveInt", "inputs": {"value": 123}},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(workspace_root)
    relative_config = str(config_path.relative_to(workspace_root)).replace("\\", "/")
    assert check_provider_health_cli.main(["--config", relative_config, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["config_path"] == str(config_path).replace("\\", "/")
    assert payload["warnings"] == []


def test_inspect_workflow_file_collects_node_types(tmp_path: Path) -> None:
    workflow_path = tmp_path / "AceStep_Music_Workflow.json"
    workflow_path.write_text(
        json.dumps(
            {
                "94": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {"lyrics": "x", "tags": "y"}},
                "109": {"class_type": "PrimitiveInt", "inputs": {"value": 123}},
            }
        ),
        encoding="utf-8",
    )
    result = provider_config.inspect_workflow_file(workflow_path)
    assert result["valid"] is True
    assert "TextEncodeAceStepAudio1.5" in result["node_types"]
