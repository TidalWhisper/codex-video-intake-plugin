#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.util
import json
import struct
import sys
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType, SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "scripts" / "providers"
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
VIDEO = ROOT / "skills" / "video-video-clips" / "scripts"
AUDIO = ROOT / "skills" / "video-audio" / "scripts"
ASSEMBLY = ROOT / "skills" / "video-assembly" / "scripts"
QA = ROOT / "skills" / "video-qa-delivery" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_e2e_test", IMAGES / "new_keyframe_image_jobs.py")
validate_keyframe_image_manifest = load_module("validate_keyframe_image_manifest_e2e_test", IMAGES / "validate_keyframe_image_manifest.py")
run_openai_gpt_image2 = load_module("run_openai_gpt_image2_e2e_test", PROVIDERS / "run_openai_gpt_image2.py")

new_video_clip_jobs = load_module("new_video_clip_jobs_e2e_test", VIDEO / "new_video_clip_jobs.py")
validate_video_clip_manifest = load_module("validate_video_clip_manifest_e2e_test", VIDEO / "validate_video_clip_manifest.py")
run_comfyui_ltx_i2v = load_module("run_comfyui_ltx_i2v_e2e_test", PROVIDERS / "run_comfyui_ltx_i2v.py")

new_audio_jobs = load_module("new_audio_jobs_e2e_test", AUDIO / "new_audio_jobs.py")
validate_audio_manifest = load_module("validate_audio_manifest_e2e_test", AUDIO / "validate_audio_manifest.py")
run_comfyui_indextts2 = load_module("run_comfyui_indextts2_e2e_test", PROVIDERS / "run_comfyui_indextts2.py")
run_comfyui_music = load_module("run_comfyui_music_e2e_test", PROVIDERS / "run_comfyui_music.py")

new_assembly_manifest = load_module("new_assembly_manifest_e2e_test", ASSEMBLY / "new_assembly_manifest.py")
validate_assembly_manifest = load_module("validate_assembly_manifest_e2e_test", ASSEMBLY / "validate_assembly_manifest.py")
assemble_with_ffmpeg = load_module("assemble_with_ffmpeg_e2e_test", ASSEMBLY / "assemble_with_ffmpeg.py")

new_qa_manifest = load_module("new_qa_manifest_e2e_test", QA / "new_qa_manifest.py")
validate_qa_manifest = load_module("validate_qa_manifest_e2e_test", QA / "validate_qa_manifest.py")
package_delivery = load_module("package_delivery_e2e_test", QA / "package_delivery.py")


def png_bytes(width: int = 8, height: int = 8) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    color = bytes((120, 180, 220))
    raw = b"".join(b"\x00" + color * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


class _FakeOpenAIHandler(BaseHTTPRequestHandler):
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


class _FakeComfyHandler(BaseHTTPRequestHandler):
    prompt_prefix = "prompt"
    filename = "output.bin"
    subfolder = "output"
    media_slot = "files"
    requests: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/prompt":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        type(self).requests.append(payload)
        prompt_id = f"{type(self).prompt_prefix}-{len(type(self).requests)}"
        body = json.dumps({
            "prompt_id": prompt_id,
            "number": len(type(self).requests),
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
        if self.path.startswith(f"/history/{type(self).prompt_prefix}-"):
            prompt_id = self.path.rsplit("/", 1)[-1]
            body = json.dumps({
                prompt_id: {
                    "status": {"completed": True, "status_str": "success"},
                    "outputs": {
                        "99": {
                            type(self).media_slot: [{
                                "filename": type(self).filename,
                                "subfolder": type(self).subfolder,
                                "type": "output",
                            }]
                        }
                    },
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


def _start_openai_server() -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeOpenAIHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeOpenAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _start_comfy_server(*, prompt_prefix: str, filename: str, subfolder: str, media_slot: str, output_root: Path, payload: bytes) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeComfyHandler.prompt_prefix = prompt_prefix
    _FakeComfyHandler.filename = filename
    _FakeComfyHandler.subfolder = subfolder
    _FakeComfyHandler.media_slot = media_slot
    _FakeComfyHandler.requests = []
    out_dir = output_root / subfolder
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_bytes(payload)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeComfyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _write_openai_config(tmp_path: Path, *, base_url: str) -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = True
    data["openai_image"]["base_url"] = base_url
    data["comfyui"]["enabled"] = False
    config_path = tmp_path / "providers.openai.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def _write_comfy_config(tmp_path: Path, *, base_url: str, output_root: Path) -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = False
    data["comfyui"]["enabled"] = True
    data["comfyui"]["base_url"] = base_url
    input_root = tmp_path / "comfy_input"
    input_root.mkdir(parents=True, exist_ok=True)
    data["comfyui"]["input_dir"] = str(input_root).replace("\\", "/")
    data["comfyui"]["output_dir"] = str(output_root).replace("\\", "/")
    config_path = tmp_path / f"providers.{output_root.name}.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def _write_workflow_mapping(tmp_path: Path) -> Path:
    ltx_workflow = tmp_path / "i2v_ltx.workflow_api.json"
    ltx_workflow.write_text(json.dumps({
        "11": {"inputs": {"image": ""}, "class_type": "LoadImage"},
        "12": {"inputs": {"image": ""}, "class_type": "LoadImage"},
        "13": {"inputs": {"text": ""}, "class_type": "CLIPTextEncode"},
        "14": {"inputs": {"seed": 1, "frames": 120, "fps": 24}, "class_type": "LTXVideo"},
        "15": {"inputs": {}, "class_type": "SaveVideo"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    indextts_workflow = tmp_path / "indextts2.workflow_api.json"
    indextts_workflow.write_text(json.dumps({
        "31": {"inputs": {"text": ""}, "class_type": "TextNode"},
        "32": {"inputs": {"audio": ""}, "class_type": "LoadAudio"},
        "33": {"inputs": {"emotion": ""}, "class_type": "EmotionNode"},
        "39": {"inputs": {}, "class_type": "SaveAudio"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    music_workflow = tmp_path / "local_music_prompt.workflow_api.json"
    music_workflow.write_text(json.dumps({
        "41": {"inputs": {"text": ""}, "class_type": "PromptNode"},
        "42": {"inputs": {"duration": 1.0}, "class_type": "DurationNode"},
        "43": {"inputs": {"seed": 1}, "class_type": "SeedNode"},
        "49": {"inputs": {}, "class_type": "SaveAudio"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping = {
        "workflows": {
            "i2v_ltx": {
                "file": str(ltx_workflow).replace("\\", "/"),
                "nodes": {
                    "start_image": {"node_id": "11", "input_name": "image"},
                    "end_image": {"node_id": "12", "input_name": "image"},
                    "motion_prompt": {"node_id": "13", "input_name": "text"},
                    "seed": {"node_id": "14", "input_name": "seed"},
                    "frame_count": {"node_id": "14", "input_name": "frames"},
                    "fps": {"node_id": "14", "input_name": "fps"},
                },
            },
            "indextts2": {
                "file": str(indextts_workflow).replace("\\", "/"),
                "nodes": {
                    "text": {"node_id": "31", "input_name": "text"},
                    "speaker_reference": {"node_id": "32", "input_name": "audio"},
                    "emotion": {"node_id": "33", "input_name": "emotion"},
                },
            },
            "music_generation": {
                "file": str(music_workflow).replace("\\", "/"),
                "nodes": {
                    "prompt": {"node_id": "41", "input_name": "text"},
                    "duration_sec": {"node_id": "42", "input_name": "duration"},
                    "seed": {"node_id": "43", "input_name": "seed"},
                },
            },
        }
    }
    mapping_path = tmp_path / "workflow_node_mapping.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return mapping_path


def _prepare_project(tmp_path: Path) -> dict[str, Path]:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assets_dir = audio_dir / "assets"
    assembly_dir = project_dir / "08_assembly"
    qa_dir = project_dir / "09_qa"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir, images_dir, video_dir, audio_dir, assembly_dir, qa_dir]:
        path.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "schema_version": "1.0.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "输出完整素材工程包，方便人工剪辑"
    brief_path = intake_dir / "project_brief.locked.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(brief_path).replace("\\", "/")
    script_path = script_dir / "script.json"
    script_path.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(brief_path).replace("\\", "/")
    storyboard["source_script"] = str(script_path).replace("\\", "/")
    storyboard["shots"] = storyboard["shots"][:1]
    storyboard["shot_count"] = 1
    storyboard_path = storyboard_dir / "storyboard.json"
    storyboard_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    characters = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    characters["project_id"] = project_dir.name
    characters["source_brief"] = str(brief_path).replace("\\", "/")
    characters["source_script"] = str(script_path).replace("\\", "/")
    characters["source_storyboard"] = str(storyboard_path).replace("\\", "/")
    character_path = character_dir / "character_bible.json"
    character_path.write_text(json.dumps(characters, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(brief_path).replace("\\", "/")
    keyframe["source_script"] = str(script_path).replace("\\", "/")
    keyframe["source_storyboard"] = str(storyboard_path).replace("\\", "/")
    keyframe["source_character_bible"] = str(character_path).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["transition_prompts"] = []
    keyframe_path = keyframe_dir / "keyframe_prompts.json"
    keyframe_path.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")
    (assets_dir / "reference_voice.wav").write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt TESTDATA")

    return {
        "project_dir": project_dir,
        "brief": brief_path,
        "script": script_path,
        "storyboard": storyboard_path,
        "character": character_path,
        "keyframe": keyframe_path,
        "images_dir": images_dir,
        "video_dir": video_dir,
        "audio_dir": audio_dir,
        "reference_voice": assets_dir / "reference_voice.wav",
        "assembly_dir": assembly_dir,
        "qa_dir": qa_dir,
    }


def test_provider_backed_stage05_to_stage09_e2e(tmp_path: Path, monkeypatch) -> None:
    paths = _prepare_project(tmp_path)
    mapping_path = _write_workflow_mapping(tmp_path)

    image_manifest_json = paths["images_dir"] / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(paths["brief"]),
        str(paths["keyframe"]),
        str(image_manifest_json),
    ]) == 0

    openai_server, openai_thread = _start_openai_server()
    try:
        openai_config = _write_openai_config(tmp_path, base_url=f"http://127.0.0.1:{openai_server.server_port}/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        assert run_openai_gpt_image2.main([str(image_manifest_json), "--config", str(openai_config)]) == 0
    finally:
        openai_server.shutdown()
        openai_thread.join(timeout=5)
        openai_server.server_close()

    image_data = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_image_manifest.validate(image_data, image_manifest_json, mode="final")
    assert ok, errors
    assert warnings == []
    assert image_data["summary"]["generated_image_count"] == 2
    assert all(job["provider"] == "openai_gpt_image2" for job in image_data["jobs"])

    clip_manifest_json = paths["video_dir"] / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(paths["brief"]),
        str(paths["storyboard"]),
        str(paths["keyframe"]),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0

    video_output_root = tmp_path / "comfy_video_output"
    video_server, video_thread = _start_comfy_server(
        prompt_prefix="prompt-video",
        filename="clip.mp4",
        subfolder="i2v",
        media_slot="videos",
        output_root=video_output_root,
        payload=b"\x00\x00\x00\x18ftypmp42VIDEOCLIP" + (b"0" * 512),
    )
    try:
        video_config = _write_comfy_config(tmp_path, base_url=f"http://127.0.0.1:{video_server.server_port}", output_root=video_output_root)
        assert run_comfyui_ltx_i2v.main([
            str(clip_manifest_json),
            "--config", str(video_config),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
    finally:
        video_server.shutdown()
        video_thread.join(timeout=5)
        video_server.server_close()

    clip_data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_video_clip_manifest.validate(clip_data, clip_manifest_json, mode="final")
    assert ok, errors
    assert warnings == []
    assert clip_data["summary"]["generated_clip_count"] == 1
    assert clip_data["jobs"][0]["provider"] == "comfyui_ltx_i2v"

    audio_manifest_json = paths["audio_dir"] / "audio_manifest.json"
    assert new_audio_jobs.main([
        "new_audio_jobs.py",
        str(paths["brief"]),
        str(paths["script"]),
        str(paths["storyboard"]),
        str(paths["character"]),
        str(clip_manifest_json),
        str(audio_manifest_json),
    ]) == 0

    voice_output_root = tmp_path / "comfy_voice_output"
    voice_server, voice_thread = _start_comfy_server(
        prompt_prefix="prompt-voice",
        filename="voice.wav",
        subfolder="voice",
        media_slot="audio",
        output_root=voice_output_root,
        payload=b"RIFFVOICEWAVE",
    )
    try:
        voice_config = _write_comfy_config(tmp_path, base_url=f"http://127.0.0.1:{voice_server.server_port}", output_root=voice_output_root)
        assert run_comfyui_indextts2.main([
            str(audio_manifest_json),
            "--config", str(voice_config),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
    finally:
        voice_server.shutdown()
        voice_thread.join(timeout=5)
        voice_server.server_close()

    music_output_root = tmp_path / "comfy_music_output"
    music_server, music_thread = _start_comfy_server(
        prompt_prefix="prompt-music",
        filename="music.wav",
        subfolder="music",
        media_slot="audio",
        output_root=music_output_root,
        payload=b"RIFFMUSICWAVE",
    )
    try:
        music_config = _write_comfy_config(tmp_path, base_url=f"http://127.0.0.1:{music_server.server_port}", output_root=music_output_root)
        assert run_comfyui_music.main([
            str(audio_manifest_json),
            "--config", str(music_config),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
    finally:
        music_server.shutdown()
        music_thread.join(timeout=5)
        music_server.server_close()

    audio_data = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(audio_data, audio_manifest_json, mode="final")
    assert ok, errors
    assert warnings == []
    assert audio_data["summary"]["generated_audio_count"] == 2

    assembly_manifest_json = paths["assembly_dir"] / "assembly_manifest.json"
    assert new_assembly_manifest.main([
        "new_assembly_manifest.py",
        str(paths["brief"]),
        str(paths["storyboard"]),
        str(clip_manifest_json),
        str(audio_manifest_json),
        str(assembly_manifest_json),
    ]) == 0

    def fake_ffmpeg_run(cmd: list[str], text: bool, stdout: int, stderr: int) -> SimpleNamespace:
        output_path = Path(cmd[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42ROUGHCUT" + (b"1" * 160))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(assemble_with_ffmpeg.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(assemble_with_ffmpeg.subprocess, "run", fake_ffmpeg_run)
    assert assemble_with_ffmpeg.main([str(assembly_manifest_json)]) == 0

    assembly_data = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(assembly_data, assembly_manifest_json, mode="final")
    assert ok, errors
    assert warnings == []
    assert assembly_data["allowed_next_stage"] == "STAGE_09_QA"

    qa_manifest_json = paths["qa_dir"] / "qa_manifest.json"
    assert new_qa_manifest.main([
        "new_qa_manifest.py",
        str(paths["brief"]),
        str(assembly_manifest_json),
        str(qa_manifest_json),
    ]) == 0
    assert package_delivery.main([
        "package_delivery.py",
        str(qa_manifest_json),
        "--content-aligned",
        "--content-alignment-note",
        "End-to-end QA confirmed the delivered rough cut matches the text description and storyboard.",
    ]) == 0

    qa_data = json.loads(qa_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_qa_manifest.validate(qa_data, qa_manifest_json, mode="final")
    assert ok, errors
    assert warnings == []
    assert qa_data["allowed_next_stage"] == "PROJECT_DELIVERED"
    assert qa_data["delivery_package"]["ready"] is True
    assert any(item["role"] == "final_video" for item in qa_data["delivery_package"]["files"])
    assert (paths["qa_dir"] / "final_delivery" / "rough_cut.mp4").exists()
