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
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_comfy_test", IMAGES / "new_keyframe_image_jobs.py")
validate_keyframe_image_manifest = load_module("validate_keyframe_image_manifest_comfy_test", IMAGES / "validate_keyframe_image_manifest.py")
run_comfyui_txt2img = load_module("run_comfyui_txt2img_test", PROVIDERS / "run_comfyui_txt2img.py")
workflow_mapping = load_module("workflow_mapping_test", PROVIDERS / "workflow_mapping.py")


class _FakeComfyTxt2ImgHandler(BaseHTTPRequestHandler):
    mode = "success"
    prompt_id = "prompt-stage05"
    requests: list[dict] = []
    output_root: Path | None = None

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
            "number": 11,
            "node_errors": {},
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
            outputs = {} if type(self).mode == "missing_output" else {
                "9": {
                    "images": [{
                        "filename": "comfy_output.png",
                        "subfolder": "txt2img",
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
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def _start_server(mode: str, *, output_root: Path) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeComfyTxt2ImgHandler.mode = mode
    _FakeComfyTxt2ImgHandler.requests = []
    _FakeComfyTxt2ImgHandler.output_root = output_root
    out_dir = output_root / "txt2img"
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode != "missing_file":
        (out_dir / "comfy_output.png").write_bytes(b"PNGDATA")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeComfyTxt2ImgHandler)
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


def _write_mapping_and_workflow(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    workflow_names = [
        "txt2img_keyframe",
        "txt2img_keyframe_realistic",
        "txt2img_keyframe_anime",
        "txt2img_keyframe_guofeng",
        "txt2img_keyframe_stylized",
    ]
    workflow_paths: dict[str, Path] = {}
    mapping_workflows: dict[str, dict] = {}
    for workflow_name in workflow_names:
        workflow_path = tmp_path / f"{workflow_name}.workflow_api.json"
        workflow_path.write_text(json.dumps({
            "6": {"inputs": {"text": ""}, "class_type": "CLIPTextEncode"},
            "7": {"inputs": {"text": ""}, "class_type": "CLIPTextEncode"},
            "3": {"inputs": {"seed": 1}, "class_type": "KSampler"},
            "5": {"inputs": {"width": 512, "height": 512}, "class_type": "EmptyLatentImage"},
            "9": {"inputs": {}, "class_type": "SaveImage"},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        workflow_paths[workflow_name] = workflow_path
        mapping_workflows[workflow_name] = {
            "file": str(workflow_path).replace("\\", "/"),
            "nodes": {
                "positive_prompt": {"node_id": "6", "input_name": "text"},
                "negative_prompt": {"node_id": "7", "input_name": "text"},
                "seed": {"node_id": "3", "input_name": "seed"},
                "width": {"node_id": "5", "input_name": "width"},
                "height": {"node_id": "5", "input_name": "height"},
            },
        }
    mapping = {"workflows": mapping_workflows}
    mapping_path = tmp_path / "workflow_node_mapping.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return mapping_path, workflow_paths


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


def test_workflow_mapping_applies_node_inputs(tmp_path: Path) -> None:
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    mapping_data, _ = workflow_mapping.load_workflow_mapping(mapping_path)
    workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "txt2img_keyframe")
    updated = workflow_mapping.apply_node_inputs(workflow, entry["nodes"], {
        "positive_prompt": "hello",
        "negative_prompt": "bad",
        "seed": 123,
        "width": 1024,
        "height": 1536,
    })
    assert updated["6"]["inputs"]["text"] == "hello"
    assert updated["7"]["inputs"]["text"] == "bad"
    assert updated["3"]["inputs"]["seed"] == 123
    assert updated["5"]["inputs"]["width"] == 1024
    assert updated["5"]["inputs"]["height"] == 1536


def test_infer_style_family_detects_minimal_four_routes() -> None:
    cases = [
        (
            {"normalized": {"style": "电影感写实", "genre": "治愈"}},
            {"shot_prompts": [{"style_prompt": "realistic cinematic film still"}]},
            "realistic",
        ),
        (
            {"normalized": {"style": "日系动画", "genre": "治愈"}},
            {"shot_prompts": [{"style_prompt": "anime key visual, clean cel shading"}]},
            "anime",
        ),
        (
            {"normalized": {"style": "国风水墨", "genre": "治愈"}},
            {"shot_prompts": [{"style_prompt": "guofeng ink wash illustration, poetic composition"}]},
            "guofeng",
        ),
        (
            {"normalized": {"style": "风格化概念艺术", "genre": "治愈"}},
            {"shot_prompts": [{"style_prompt": "stylized concept art, bold shape design"}]},
            "stylized",
        ),
    ]
    for brief, prompts, expected in cases:
        assert new_keyframe_image_jobs.infer_style_family(brief, prompts) == expected


def test_run_comfyui_txt2img_dry_run_writes_request_manifest_only(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, workflow_paths = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_txt2img.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 0
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert manifest["style_family"] == "realistic"
    assert manifest["comfyui_workflow_router"]["realistic"] == "txt2img_keyframe_realistic"
    assert all(job["style_family"] == "realistic" for job in manifest["jobs"])
    assert all(job["comfyui_workflow_name"] == "txt2img_keyframe_realistic" for job in manifest["jobs"])
    request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["workflow_name"] == "auto_style_family"
    assert request_manifest["workflow_path"] == str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")
    assert request_manifest["workflow_paths"] == [str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")]
    assert len(request_manifest["requests"]) == 2
    assert all(item["status"] == "planned" for item in request_manifest["requests"])
    assert all(item["style_family"] == "realistic" for item in request_manifest["requests"])
    assert all(item["workflow_name"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
    assert not any((manifest_json.parent / "keyframes").glob("*.png"))


def test_run_comfyui_txt2img_blocks_when_requested_scope_stops_earlier(tmp_path: Path) -> None:
    manifest_json = _prepare_scope_blocked_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_txt2img.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 1
    assert run_comfyui_txt2img.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
        "--allow-beyond-requested-scope",
    ]) == 0


def test_run_comfyui_txt2img_success_updates_manifest_and_passes_validator(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, workflow_paths = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_txt2img.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
        assert ok, errors
        assert warnings == []
        assert all(job["provider"] == "comfyui_txt2img" for job in data["jobs"])
        assert all(job["notes"].startswith("workflow=txt2img_keyframe_realistic;") for job in data["jobs"])
        request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["workflow_name"] == "auto_style_family"
        assert request_manifest["workflow_path"] == str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")
        assert all(item["status"] == "succeeded" for item in request_manifest["requests"])
        assert all(item["workflow_name"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
        workflow_payload = _FakeComfyTxt2ImgHandler.requests[0]["prompt"]
        assert "Avoid:" in workflow_payload["6"]["inputs"]["text"]
        assert workflow_payload["5"]["inputs"]["width"] == 1024
        assert workflow_payload["5"]["inputs"]["height"] == 1536
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_txt2img_failure_records_errors(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, workflow_paths = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("missing_output", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_txt2img.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        assert all(job["status"] == "failed" for job in data["jobs"])
        assert all(job["errors"] for job in data["jobs"])
        request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["workflow_path"] == str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")
        assert all(item["status"] == "failed" for item in request_manifest["requests"])
        assert all(item["workflow_name"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
