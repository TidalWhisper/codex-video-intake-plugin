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
INTAKE = ROOT / "skills" / "video-project-intake" / "scripts"
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
VIDEO = ROOT / "skills" / "video-video-clips" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_ltx_test", IMAGES / "new_keyframe_image_jobs.py")
generate_placeholder_keyframe_images = load_module("generate_placeholder_keyframe_images_ltx_test", IMAGES / "generate_placeholder_keyframe_images.py")
new_video_clip_jobs = load_module("new_video_clip_jobs_ltx_test", VIDEO / "new_video_clip_jobs.py")
validate_video_clip_manifest = load_module("validate_video_clip_manifest_ltx_test", VIDEO / "validate_video_clip_manifest.py")
run_comfyui_ltx_i2v = load_module("run_comfyui_ltx_i2v_test", PROVIDERS / "run_comfyui_ltx_i2v.py")


class _FakeLtxHandler(BaseHTTPRequestHandler):
    mode = "success"
    prompt_id = "prompt-ltx"
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/prompt":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).requests.append(payload)
        body = json.dumps({
            "prompt_id": type(self).prompt_id,
            "number": 21,
            "node_errors": {},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == f"/history/{type(self).prompt_id}":
            outputs = {} if type(self).mode == "missing_output" else {
                "15": {
                    "videos": [{
                        "filename": "ltx_clip.mp4",
                        "subfolder": "i2v",
                        "type": "output",
                    }]
                }
            }
            body = json.dumps({
                type(self).prompt_id: {
                    "status": {"completed": True, "status_str": "success"},
                    "outputs": outputs,
                }
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/system_stats":
            body = json.dumps({"system": {"os": "test"}, "devices": []}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def _start_server(mode: str, *, output_root: Path) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeLtxHandler.mode = mode
    _FakeLtxHandler.requests = []
    out_dir = output_root / "i2v"
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode != "missing_file":
        (out_dir / "ltx_clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42LTXTEST")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLtxHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _write_config(tmp_path: Path, *, base_url: str, output_root: Path) -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = False
    data["comfyui"]["enabled"] = True
    data["comfyui"]["base_url"] = base_url
    input_root = tmp_path / "comfy_input"
    input_root.mkdir(parents=True, exist_ok=True)
    data["comfyui"]["input_dir"] = str(input_root).replace("\\", "/")
    data["comfyui"]["output_dir"] = str(output_root).replace("\\", "/")
    config_path = tmp_path / "providers.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def _write_mapping_and_workflow(tmp_path: Path) -> Path:
    workflow_path = tmp_path / "i2v_ltx.workflow_api.json"
    workflow_path.write_text(json.dumps({
        "11": {"inputs": {"image": ""}, "class_type": "LoadImage"},
        "12": {"inputs": {"image": ""}, "class_type": "LoadImage"},
        "13": {"inputs": {"text": ""}, "class_type": "CLIPTextEncode"},
        "14": {"inputs": {"seed": 1, "frames": 120, "fps": 24}, "class_type": "LTXVideo"},
        "15": {"inputs": {}, "class_type": "SaveVideo"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping = {
        "workflows": {
            "i2v_ltx": {
                "file": str(workflow_path).replace("\\", "/"),
                "nodes": {
                    "start_image": {"node_id": "11", "input_name": "image"},
                    "end_image": {"node_id": "12", "input_name": "image"},
                    "motion_prompt": {"node_id": "13", "input_name": "text"},
                    "seed": {"node_id": "14", "input_name": "seed"},
                    "frame_count": {"node_id": "14", "input_name": "frames"},
                    "fps": {"node_id": "14", "input_name": "fps"},
                },
            }
        }
    }
    mapping_path = tmp_path / "workflow_node_mapping.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return mapping_path


def _prepare_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for path in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "schema_version": "0.7.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["shots"] = storyboard["shots"][:1]
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["status"] = "confirmed"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json)
    ]) == 0
    return clip_manifest_json


def _prepare_scope_blocked_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_scope_blocked"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for path in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "schema_version": "0.7.0",
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

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["shots"] = storyboard["shots"][:1]
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json), "--allow-beyond-requested-scope"
    ]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["status"] = "confirmed"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json), "--allow-beyond-requested-scope"
    ]) == 0
    return clip_manifest_json


def test_run_comfyui_ltx_i2v_dry_run_writes_request_manifest_only(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_ltx_i2v.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 0
    request_manifest = json.loads((manifest_json.parent / "comfyui_ltx_i2v_requests.json").read_text(encoding="utf-8"))
    assert len(request_manifest["requests"]) == 1
    assert request_manifest["requests"][0]["status"] == "planned"


def test_run_comfyui_ltx_i2v_blocks_when_requested_scope_stops_earlier(tmp_path: Path) -> None:
    manifest_json = _prepare_scope_blocked_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_ltx_i2v.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 1
    assert run_comfyui_ltx_i2v.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
        "--allow-beyond-requested-scope",
    ]) == 0


def test_run_comfyui_ltx_i2v_success_updates_manifest_and_passes_validator(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_ltx_i2v.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        ok, errors, warnings = validate_video_clip_manifest.validate(data, manifest_json, mode="final")
        assert ok, errors
        assert warnings == []
        assert data["jobs"][0]["provider"] == "comfyui_ltx_i2v"
        request_manifest = json.loads((manifest_json.parent / "comfyui_ltx_i2v_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "succeeded"
        assert request_manifest["requests"][0]["fps"] == 25
        assert request_manifest["requests"][0]["duration_sec"] == 6
        workflow_payload = _FakeLtxHandler.requests[0]["prompt"]
        assert workflow_payload["14"]["inputs"]["fps"] == 25
        assert workflow_payload["14"]["inputs"]["frames"] > 0
        assert workflow_payload["11"]["inputs"]["image"].endswith(".png")
        assert workflow_payload["12"]["inputs"]["image"].endswith(".png")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_ltx_i2v_failure_records_errors(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("missing_output", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_ltx_i2v.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        assert data["jobs"][0]["status"] == "failed"
        assert data["jobs"][0]["errors"]
        request_manifest = json.loads((manifest_json.parent / "comfyui_ltx_i2v_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "failed"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
