#!/usr/bin/env python3
from __future__ import annotations

import base64
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
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_openai_test", IMAGES / "new_keyframe_image_jobs.py")
validate_keyframe_image_manifest = load_module("validate_keyframe_image_manifest_openai_test", IMAGES / "validate_keyframe_image_manifest.py")
openai_image_client = load_module("openai_image_client_test", PROVIDERS / "openai_image_client.py")
run_openai_gpt_image2 = load_module("run_openai_gpt_image2_test", PROVIDERS / "run_openai_gpt_image2.py")


def png_bytes(width: int = 8, height: int = 8) -> bytes:
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    color = bytes((120, 180, 220))
    raw = b"".join(b"\x00" + color * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


class _FakeOpenAIHandler(BaseHTTPRequestHandler):
    mode = "success"
    requests: list[dict] = []
    image_b64 = base64.b64encode(png_bytes()).decode("ascii")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/images/generations":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).requests.append(payload)
        if type(self).mode == "failure":
            body = json.dumps({"error": {"message": "mock image generation failure"}}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = json.dumps({
            "created": 1770000000,
            "output_format": payload.get("output_format", "png"),
            "quality": payload.get("quality", "high"),
            "size": payload.get("size", "1024x1536"),
            "data": [{
                "b64_json": type(self).image_b64,
                "revised_prompt": "mock revised prompt",
            }],
            "usage": {
                "input_tokens": 12,
                "output_tokens": 34,
                "total_tokens": 46,
            },
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _start_openai_server(mode: str) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeOpenAIHandler.mode = mode
    _FakeOpenAIHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOpenAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _write_config(tmp_path: Path, *, base_url: str) -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = True
    data["openai_image"]["base_url"] = base_url
    data["comfyui"]["enabled"] = False
    config_path = tmp_path / "providers.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def _prepare_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "schema_version": "0.6.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0
    return manifest_json


def _prepare_scope_blocked_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_scope_blocked"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "schema_version": "0.6.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "剧本 + 分镜 + 关键帧提示词"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0
    return manifest_json


def test_image_size_for_aspect_ratio_maps_common_shapes() -> None:
    assert openai_image_client.image_size_for_aspect_ratio("9:16") == "1024x1536"
    assert openai_image_client.image_size_for_aspect_ratio("16:9") == "1536x1024"
    assert openai_image_client.image_size_for_aspect_ratio("1:1") == "1024x1024"


def test_run_openai_gpt_image2_dry_run_writes_request_manifest_only(tmp_path: Path, monkeypatch) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    server, thread = _start_openai_server("success")
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert run_openai_gpt_image2.main([str(manifest_json), "--config", str(config_path), "--dry-run"]) == 0
        request_manifest = json.loads((manifest_json.parent / "openai_image_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["provider"] == "openai_gpt_image2"
        assert len(request_manifest["requests"]) == 2
        assert all(item["status"] == "planned" for item in request_manifest["requests"])
        assert not any((manifest_json.parent / "keyframes").glob("*.png"))
        assert _FakeOpenAIHandler.requests == []
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_openai_gpt_image2_blocks_when_requested_scope_stops_earlier(tmp_path: Path, monkeypatch) -> None:
    manifest_json = _prepare_scope_blocked_manifest(tmp_path)
    server, thread = _start_openai_server("success")
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert run_openai_gpt_image2.main([str(manifest_json), "--config", str(config_path), "--dry-run"]) == 1
        assert run_openai_gpt_image2.main([str(manifest_json), "--config", str(config_path), "--dry-run", "--allow-beyond-requested-scope"]) == 0
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_openai_gpt_image2_single_job_generates_selected_image(tmp_path: Path, monkeypatch) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    server, thread = _start_openai_server("success")
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert run_openai_gpt_image2.main([str(manifest_json), "--config", str(config_path), "--image-id", "IMG_S001_START"]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        jobs = {job["image_id"]: job for job in data["jobs"]}
        assert jobs["IMG_S001_START"]["status"] == "succeeded"
        assert jobs["IMG_S001_END"]["status"] == "pending"
        assert data["summary"]["generated_image_count"] == 1
        assert len(_FakeOpenAIHandler.requests) == 1
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_openai_gpt_image2_batch_success_updates_manifest_and_passes_validator(tmp_path: Path, monkeypatch) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    server, thread = _start_openai_server("success")
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert run_openai_gpt_image2.main([str(manifest_json), "--config", str(config_path)]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
        assert ok, errors
        assert warnings == []
        assert data["summary"]["generated_image_count"] == 2
        assert data["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"
        assert all(job["provider"] == "openai_gpt_image2" for job in data["jobs"])
        request_manifest = json.loads((manifest_json.parent / "openai_image_requests.json").read_text(encoding="utf-8"))
        assert all(item["status"] == "succeeded" for item in request_manifest["requests"])
        assert "Avoid:" in _FakeOpenAIHandler.requests[0]["prompt"]
        assert "Consistency:" in _FakeOpenAIHandler.requests[0]["prompt"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_openai_gpt_image2_batch_failure_records_errors_without_fake_success(tmp_path: Path, monkeypatch) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    server, thread = _start_openai_server("failure")
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert run_openai_gpt_image2.main([str(manifest_json), "--config", str(config_path)]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        assert all(job["status"] == "failed" for job in data["jobs"])
        assert all(job["errors"] for job in data["jobs"])
        assert data["summary"]["generated_image_count"] == 0
        ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
        assert not ok
        assert any("status must be succeeded" in error for error in errors)
        request_manifest = json.loads((manifest_json.parent / "openai_image_requests.json").read_text(encoding="utf-8"))
        assert all(item["status"] == "failed" for item in request_manifest["requests"])
        assert all(not Path(job["evidence"]["file_path"]).exists() for job in data["jobs"])
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
