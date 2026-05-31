#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


comfyui_client = load_module("comfyui_client_test_module", PROVIDERS / "comfyui_client.py")
run_comfyui_workflow = load_module("run_comfyui_workflow_test_module", PROVIDERS / "run_comfyui_workflow.py")


class _FakeComfyHandler(BaseHTTPRequestHandler):
    mode = "success"
    requests: list[dict] = []
    history_calls = 0
    prompt_id = "prompt-123"
    output_root: Path | None = None

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/system_stats":
            body = json.dumps({"system": {"os": "test"}, "devices": []}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == f"/history/{type(self).prompt_id}":
            type(self).history_calls += 1
            if type(self).mode == "history_error":
                payload = {
                    type(self).prompt_id: {
                        "status": {
                            "completed": True,
                            "status_str": "error",
                            "messages": [
                                [
                                    "execution_error",
                                    {
                                        "node_id": "41",
                                        "node_type": "MusicPromptNode",
                                        "exception_message": "Music provider error: mock execution failure",
                                    },
                                ]
                            ],
                        },
                        "outputs": {},
                    }
                }
            elif type(self).mode == "poll_then_success" and type(self).history_calls == 1:
                payload = {}
            elif type(self).mode == "mp4_in_images_slot":
                payload = {
                    type(self).prompt_id: {
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {
                            "22": {
                                "images": [
                                    {
                                        "filename": "clip.mp4",
                                        "subfolder": "video",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                    }
                }
            else:
                payload = {
                    type(self).prompt_id: {
                        "status": {"completed": True, "status_str": "success"},
                        "outputs": {
                            "9": {
                                "images": [
                                    {
                                        "filename": "frame.png",
                                        "subfolder": "stage05",
                                        "type": "output",
                                    }
                                ]
                            }
                        },
                    }
                }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/prompt":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).requests.append(payload)
        if type(self).mode == "submit_http_error":
            body = json.dumps({"error": "mock submit failure"}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        node_errors = {"6": {"errors": ["bad node"]}} if type(self).mode == "node_errors" else {}
        body = json.dumps({
            "prompt_id": type(self).prompt_id,
            "number": 7,
            "node_errors": node_errors,
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _start_server(mode: str, *, output_root: Path) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeComfyHandler.mode = mode
    _FakeComfyHandler.requests = []
    _FakeComfyHandler.history_calls = 0
    _FakeComfyHandler.output_root = output_root
    (output_root / "stage05").mkdir(parents=True, exist_ok=True)
    (output_root / "stage05" / "frame.png").write_bytes(b"PNGDATA")
    (output_root / "video").mkdir(parents=True, exist_ok=True)
    (output_root / "video" / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42TEST")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeComfyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _write_config(tmp_path: Path, *, base_url: str, output_root: Path) -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = False
    data["comfyui"]["enabled"] = True
    data["comfyui"]["base_url"] = base_url
    data["comfyui"]["output_dir"] = str(output_root).replace("\\", "/")
    config_path = tmp_path / "providers.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def test_comfyui_client_can_submit_wait_and_collect_outputs(tmp_path: Path) -> None:
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("poll_then_success", output_root=output_root)
    try:
        client = comfyui_client.ComfyUIClient(
            base_url=f"http://127.0.0.1:{server.server_port}",
            timeout_seconds=2,
            output_dir=output_root,
        )
        stats = client.get_system_stats()
        assert stats["system"]["os"] == "test"
        submitted = client.submit_prompt({"6": {"inputs": {"text": "hello"}}})
        assert submitted["prompt_id"] == "prompt-123"
        history_entry = client.wait_for_prompt("prompt-123", poll_interval=0.01, max_wait_seconds=2)
        outputs = client.collect_outputs(history_entry)
        assert len(outputs) == 1
        assert outputs[0]["media_type"] == "image"
        assert outputs[0]["resolved_path"] == str((output_root / "stage05" / "frame.png").resolve()).replace("\\", "/")
        assert _FakeComfyHandler.history_calls >= 2
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_comfyui_client_raises_on_node_errors(tmp_path: Path) -> None:
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("node_errors", output_root=output_root)
    try:
        client = comfyui_client.ComfyUIClient(base_url=f"http://127.0.0.1:{server.server_port}", timeout_seconds=2)
        try:
            client.submit_prompt({"6": {"inputs": {"text": "hello"}}})
        except comfyui_client.ComfyUIError as exc:
            assert exc.kind == "submission_error"
        else:
            raise AssertionError("expected ComfyUIError")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_comfyui_client_summarizes_http_node_validation_errors() -> None:
    summary = comfyui_client.ComfyUIClient._summarize_error_details({
        "error": {
            "type": "prompt_outputs_failed_validation",
            "message": "Prompt outputs failed validation",
        },
        "node_errors": {
            "8": {
                "class_type": "CLIPLoader",
                "errors": [
                    {
                        "message": "Value not in list",
                        "details": "clip_name: 'gemma_2_2b_fp16.safetensors' not in available models",
                    }
                ],
            },
            "1": {
                "class_type": "UNETLoader",
                "errors": [
                    {
                        "message": "Value not in list",
                        "details": "unet_name: 'neta-lumina-v1.0.safetensors' not in available models",
                    }
                ],
            },
        },
    })
    assert "prompt_outputs_failed_validation" in summary
    assert "node 8 (CLIPLoader)" in summary
    assert "gemma_2_2b_fp16.safetensors" in summary
    assert "node 1 (UNETLoader)" in summary
    assert "neta-lumina-v1.0.safetensors" in summary


def test_comfyui_client_raises_on_execution_error(tmp_path: Path) -> None:
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("history_error", output_root=output_root)
    try:
        client = comfyui_client.ComfyUIClient(base_url=f"http://127.0.0.1:{server.server_port}", timeout_seconds=2)
        client.submit_prompt({"6": {"inputs": {"text": "hello"}}})
        try:
            client.wait_for_prompt("prompt-123", poll_interval=0.01, max_wait_seconds=2)
        except comfyui_client.ComfyUIError as exc:
            assert exc.kind == "execution_error"
            assert "MusicPromptNode" in str(exc)
            assert "mock execution failure" in str(exc)
        else:
            raise AssertionError("expected ComfyUIError")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_comfyui_client_recognizes_mp4_saved_in_images_slot(tmp_path: Path) -> None:
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("mp4_in_images_slot", output_root=output_root)
    try:
        client = comfyui_client.ComfyUIClient(
            base_url=f"http://127.0.0.1:{server.server_port}",
            timeout_seconds=2,
            output_dir=output_root,
        )
        client.submit_prompt({"6": {"inputs": {"text": "hello"}}})
        history_entry = client.wait_for_prompt("prompt-123", poll_interval=0.01, max_wait_seconds=2)
        outputs = client.collect_outputs(history_entry)
        assert len(outputs) == 1
        assert outputs[0]["media_type"] == "video"
        assert outputs[0]["resolved_path"] == str((output_root / "video" / "clip.mp4").resolve()).replace("\\", "/")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_workflow_cli_success(tmp_path: Path, capsys) -> None:
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        workflow_path = tmp_path / "workflow.json"
        workflow_path.write_text(json.dumps({"6": {"inputs": {"text": "hello"}}}), encoding="utf-8")
        assert run_comfyui_workflow.main([
            str(workflow_path),
            "--config", str(config_path),
            "--json",
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True
        assert payload["prompt_id"] == "prompt-123"
        assert len(payload["outputs"]) == 1
        assert payload["outputs"][0]["filename"] == "frame.png"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_workflow_cli_fails_for_missing_workflow(tmp_path: Path, capsys) -> None:
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_workflow.main([
        str(tmp_path / "missing.workflow_api.json"),
        "--config", str(config_path),
        "--json",
    ]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["status"] == "workflow_missing"
