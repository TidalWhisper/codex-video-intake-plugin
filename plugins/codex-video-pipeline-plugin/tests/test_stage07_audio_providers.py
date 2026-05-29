#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "scripts" / "providers"
AUDIO = ROOT / "skills" / "video-audio" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_audio_jobs = load_module("new_audio_jobs_stage07_test", AUDIO / "new_audio_jobs.py")
validate_audio_manifest = load_module("validate_audio_manifest_stage07_test", AUDIO / "validate_audio_manifest.py")
run_comfyui_indextts2 = load_module("run_comfyui_indextts2_stage07_test", PROVIDERS / "run_comfyui_indextts2.py")
run_comfyui_music = load_module("run_comfyui_music_stage07_test", PROVIDERS / "run_comfyui_music.py")
sync_comfyui_music_result = load_module("sync_comfyui_music_result_stage07_test", PROVIDERS / "sync_comfyui_music_result.py")
audio_output_utils = load_module("audio_output_utils_stage07_test", PROVIDERS / "audio_output_utils.py")
heartmula_prompt_builder = load_module("heartmula_prompt_builder_stage07_test", PROVIDERS / "heartmula_prompt_builder.py")
acestep_prompt_builder = load_module("acestep_prompt_builder_stage07_test", PROVIDERS / "acestep_prompt_builder.py")


class _FakeAudioHandler(BaseHTTPRequestHandler):
    mode = "success"
    prompt_prefix = "prompt-audio"
    filename = "audio.wav"
    subfolder = "audio"
    media_slot = "audio"
    requests: list[dict] = []
    active_prompt_id: str | None = None

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
        if self.path == "/queue":
            active_prompt_id = type(self).active_prompt_id or f"{type(self).prompt_prefix}-1"
            queue_running: list[object] = []
            queue_pending: list[object] = []
            if type(self).mode == "queue_running":
                queue_running = [[1, active_prompt_id, {}, {}, ["51"]]]
            elif type(self).mode == "queue_pending":
                queue_pending = [[1, active_prompt_id, {}, {}, ["51"]]]
            body = json.dumps({
                "queue_running": queue_running,
                "queue_pending": queue_pending,
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        active_prompt_id = type(self).active_prompt_id or f"{type(self).prompt_prefix}-1"
        if self.path.startswith(f"/history/{type(self).prompt_prefix}-") or self.path == f"/history/{active_prompt_id}":
            if type(self).mode in {"queue_running", "queue_pending", "cancelled"}:
                body = json.dumps({}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            outputs = {} if type(self).mode in {"missing_output", "execution_error"} else {
                "51": {
                    type(self).media_slot: [{
                        "filename": type(self).filename,
                        "subfolder": type(self).subfolder,
                        "type": "output",
                    }]
                }
            }
            status = {"completed": True, "status_str": "success"}
            if type(self).mode == "execution_error":
                status = {
                    "completed": False,
                    "status_str": "error",
                    "messages": [
                        [
                            "execution_error",
                            {
                                "prompt_id": self.path.rsplit("/", 1)[-1],
                                "node_id": "41",
                                "node_type": "MusicPromptNode",
                                "exception_message": "Music provider error: mock execution failure",
                            },
                        ]
                    ],
                }
            body = json.dumps({
                self.path.rsplit("/", 1)[-1]: {
                    "status": status,
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


def _start_server(mode: str, *, output_root: Path, prompt_prefix: str, filename: str, subfolder: str, media_slot: str = "audio") -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeAudioHandler.mode = mode
    _FakeAudioHandler.prompt_prefix = prompt_prefix
    _FakeAudioHandler.filename = filename
    _FakeAudioHandler.subfolder = subfolder
    _FakeAudioHandler.media_slot = media_slot
    _FakeAudioHandler.requests = []
    _FakeAudioHandler.active_prompt_id = None
    out_dir = output_root / subfolder
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode not in {"missing_file", "queue_running", "queue_pending", "cancelled"}:
        (out_dir / filename).write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt TESTDATA")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeAudioHandler)
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


def _write_mapping_and_workflows(tmp_path: Path) -> Path:
    indextts2_workflow = tmp_path / "indextts2.workflow_api.json"
    indextts2_workflow.write_text(json.dumps({
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
            "indextts2": {
                "file": str(indextts2_workflow).replace("\\", "/"),
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


def _write_heartmula_mapping_and_workflow(tmp_path: Path) -> Path:
    heartmula_workflow = tmp_path / "HeartMuLa_workflow_fixed_importable.json"
    heartmula_workflow.write_text(json.dumps({
        "11": {"inputs": {"audio": ["14", 0], "filename_prefix": "audio/ComfyUI", "audioUI": ""}, "class_type": "SaveAudio"},
        "14": {
            "inputs": {
                "lyrics": "",
                "tags": "",
                "seed": 1,
                "max_audio_length_seconds": 30,
            },
            "class_type": "HeartMuLa_Generate",
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping = {
        "workflows": {
            "music_generation": {
                "file": str(heartmula_workflow).replace("\\", "/"),
                "nodes": {
                    "lyrics": {"node_id": "14", "input_name": "lyrics"},
                    "tags": {"node_id": "14", "input_name": "tags"},
                    "seed": {"node_id": "14", "input_name": "seed"},
                    "max_audio_length_seconds": {"node_id": "14", "input_name": "max_audio_length_seconds"},
                },
            },
        }
    }
    mapping_path = tmp_path / "workflow_node_mapping_heartmula.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return mapping_path


def _write_acestep_mapping_and_workflow(tmp_path: Path) -> Path:
    acestep_workflow = tmp_path / "AceStep_Music_Workflow.json"
    acestep_workflow.write_text(json.dumps({
        "94": {
            "inputs": {
                "tags": "",
                "lyrics": "",
                "seed": ["109", 0],
                "bpm": 95,
                "duration": 120,
                "timesignature": "4",
                "language": "zh",
                "keyscale": "E minor",
                "generate_audio_codes": True,
                "cfg_scale": 2,
                "temperature": 0.85,
                "top_p": 0.9,
                "top_k": 0,
                "min_p": 0,
                "clip": ["105", 0],
            },
            "class_type": "TextEncodeAceStepAudio1.5",
        },
        "98": {
            "inputs": {"seconds": 120, "batch_size": 1},
            "class_type": "EmptyAceStep1.5LatentAudio",
        },
        "105": {
            "inputs": {"clip_name1": "AceStep\\qwen_0.6b_ace15.safetensors", "clip_name2": "AceStep\\qwen_4b_ace15.safetensors", "type": "ace", "device": "default"},
            "class_type": "DualCLIPLoader",
        },
        "109": {
            "inputs": {"value": -629061601594370},
            "class_type": "PrimitiveInt",
        },
        "107": {
            "inputs": {"filename_prefix": "audio/ACE_Step1.5_xl_turbo", "quality": "V0", "audioUI": "", "audio": ["18", 0]},
            "class_type": "SaveAudioMP3",
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping = {
        "workflows": {
            "music_generation_acestep": {
                "file": str(acestep_workflow).replace("\\", "/"),
                "nodes": {
                    "lyrics": {"node_id": "94", "input_name": "lyrics"},
                    "tags": {"node_id": "94", "input_name": "tags"},
                    "seed": {"node_id": "109", "input_name": "value"},
                    "duration_sec": {"node_id": "94", "input_name": "duration"},
                    "latent_seconds": {"node_id": "98", "input_name": "seconds"},
                    "bpm": {"node_id": "94", "input_name": "bpm"},
                    "language": {"node_id": "94", "input_name": "language"},
                    "keyscale": {"node_id": "94", "input_name": "keyscale"},
                    "timesignature": {"node_id": "94", "input_name": "timesignature"},
                },
            },
        },
    }
    mapping_path = tmp_path / "workflow_node_mapping_acestep.yaml"
    mapping_path.write_text(yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return mapping_path


def _prepare_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    clip_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assets_dir = audio_dir / "assets"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, clip_dir, audio_dir]:
        path.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "合成粗剪成片"
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

    clip_manifest = json.loads((TEMPLATES / "video_clip_manifest.example.json").read_text(encoding="utf-8"))
    clip_manifest.update({
        "project_id": project_dir.name,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_storyboard": str(storyboard_path).replace("\\", "/"),
        "status": "confirmed",
        "allowed_next_stage": "STAGE_07_AUDIO",
    })
    clip_manifest["jobs"] = clip_manifest["jobs"][:1]
    clip_manifest["summary"]["shot_count"] = 1
    clip_manifest["summary"]["expected_clip_count"] = 1
    clip_manifest["summary"]["generated_clip_count"] = 1
    clip_manifest["self_check"]["ready_for_audio_stage"] = True
    clip_manifest_path = clip_dir / "video_clip_manifest.json"
    clip_manifest_path.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main([
        "new_audio_jobs.py",
        str(brief_path),
        str(script_path),
        str(storyboard_path),
        str(character_path),
        str(clip_manifest_path),
        str(manifest_path),
    ]) == 0
    (assets_dir / "reference_voice.wav").write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt TESTDATA")
    return manifest_path


def _prepare_scope_blocked_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_scope_blocked"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    clip_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, clip_dir, audio_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
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

    clip_manifest = json.loads((TEMPLATES / "video_clip_manifest.example.json").read_text(encoding="utf-8"))
    clip_manifest.update({
        "project_id": project_dir.name,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_storyboard": str(storyboard_path).replace("\\", "/"),
        "status": "confirmed",
        "allowed_next_stage": "STAGE_07_AUDIO",
    })
    clip_manifest["jobs"] = clip_manifest["jobs"][:1]
    clip_manifest["summary"]["shot_count"] = 1
    clip_manifest["summary"]["expected_clip_count"] = 1
    clip_manifest["summary"]["generated_clip_count"] = 1
    clip_manifest["self_check"]["ready_for_audio_stage"] = True
    clip_manifest_path = clip_dir / "video_clip_manifest.json"
    clip_manifest_path.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main([
        "new_audio_jobs.py",
        str(brief_path),
        str(script_path),
        str(storyboard_path),
        str(character_path),
        str(clip_manifest_path),
        str(manifest_path),
        "--allow-beyond-requested-scope",
    ]) == 0
    return manifest_path


def _music_job(manifest_json: Path) -> dict:
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    return next(job for job in data["jobs"] if job["audio_type"] == "music")


def _set_music_profile(manifest_json: Path, profile: str) -> None:
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    requirements = data.get("requirements") if isinstance(data.get("requirements"), dict) else {}
    requirements["music_profile"] = profile
    data["requirements"] = requirements
    strategy = data.get("music_provider_strategy") if isinstance(data.get("music_provider_strategy"), dict) else {}
    strategy["default_profile"] = profile
    data["music_provider_strategy"] = strategy
    for job in data.get("jobs") or []:
        if isinstance(job, dict) and job.get("audio_type") == "music":
            job["music_profile"] = profile
    manifest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    audio_jobs_path = manifest_json.parent / "audio_jobs.json"
    if audio_jobs_path.exists():
        jobs_payload = json.loads(audio_jobs_path.read_text(encoding="utf-8"))
        for job in jobs_payload.get("jobs") or []:
            if isinstance(job, dict) and job.get("audio_type") == "music":
                job["music_profile"] = profile
        audio_jobs_path.write_text(json.dumps(jobs_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_request_manifest_for_prompt(
    manifest_json: Path,
    *,
    prompt_id: str,
    workflow_name: str = "music_generation",
    workflow_path: str = "workflow.json",
) -> Path:
    job = _music_job(manifest_json)
    requests_path = manifest_json.parent / "music_requests.json"
    payload = {
        "provider": "comfyui_music",
        "workflow_name": workflow_name,
        "workflow_mapping_path": "test_mapping.yaml",
        "workflow_path": workflow_path,
        "generated_at": "2026-05-28T10:30:00+08:00",
        "requests": [
            {
                **run_comfyui_music.request_record(job, workflow_name, Path(workflow_path)),
                "prompt_id": prompt_id,
                "status": "running",
                "requested_at": "2026-05-28T10:31:00+08:00",
            }
        ],
    }
    requests_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return requests_path


def test_run_comfyui_indextts2_dry_run_writes_request_manifest_only(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_voice_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_indextts2.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 0
    request_manifest = json.loads((manifest_json.parent / "indextts2_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["provider"] == "indextts2"
    assert len(request_manifest["requests"]) == 1
    assert request_manifest["requests"][0]["status"] == "planned"


def test_run_comfyui_indextts2_blocks_when_requested_scope_stops_earlier(tmp_path: Path) -> None:
    manifest_json = _prepare_scope_blocked_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_voice_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_indextts2.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 1
    assert run_comfyui_indextts2.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
        "--allow-beyond-requested-scope",
    ]) == 0


def test_run_comfyui_music_dry_run_writes_request_manifest_only(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_music.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 0
    request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["provider"] == "comfyui_music"
    assert len(request_manifest["requests"]) == 1
    assert request_manifest["requests"][0]["status"] == "planned"
    assert request_manifest["requests"][0]["music_profile"] == "underscore"


def test_run_comfyui_music_blocks_when_requested_scope_stops_earlier(tmp_path: Path) -> None:
    manifest_json = _prepare_scope_blocked_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_music.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 1
    assert run_comfyui_music.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
        "--allow-beyond-requested-scope",
    ]) == 0


def test_stage07_voice_and_music_success_passes_final_validator(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)

    voice_output_root = tmp_path / "comfy_voice_output"
    voice_server, voice_thread = _start_server(
        "success",
        output_root=voice_output_root,
        prompt_prefix="prompt-voice",
        filename="voice.wav",
        subfolder="voice",
    )
    try:
        voice_config = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{voice_server.server_port}",
            output_root=voice_output_root,
        )
        assert run_comfyui_indextts2.main([
            str(manifest_json),
            "--config", str(voice_config),
            "--mapping", str(mapping_path),
            "--speaker-reference", "assets/reference_voice.wav",
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        voice_requests = list(_FakeAudioHandler.requests)
    finally:
        voice_server.shutdown()
        voice_thread.join(timeout=5)
        voice_server.server_close()

    music_output_root = tmp_path / "comfy_music_output"
    music_server, music_thread = _start_server(
        "success",
        output_root=music_output_root,
        prompt_prefix="prompt-music",
        filename="music.wav",
        subfolder="music",
    )
    try:
        music_config = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{music_server.server_port}",
            output_root=music_output_root,
        )
        assert run_comfyui_music.main([
            str(manifest_json),
            "--config", str(music_config),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        music_requests = list(_FakeAudioHandler.requests)
    finally:
        music_server.shutdown()
        music_thread.join(timeout=5)
        music_server.server_close()

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(data, manifest_json, mode="final")
    assert ok, errors
    assert warnings == []
    assert data["summary"]["generated_audio_count"] == 2
    assert data["self_check"]["ready_for_assembly_stage"] is True
    assert data["allowed_next_stage"] == "STAGE_08_ASSEMBLY"
    assert any(job["provider"] == "indextts2" for job in data["jobs"])
    assert any(job["provider"] == "comfyui_music" for job in data["jobs"])

    voice_payload = voice_requests[0]["prompt"]
    assert voice_payload["31"]["inputs"]["text"] == "有些告别，不一定要说出口。"
    assert voice_payload["32"]["inputs"]["audio"].endswith("reference_voice.wav")
    assert "安静" in voice_payload["33"]["inputs"]["emotion"]

    music_payload = music_requests[0]["prompt"]
    assert "轻柔钢琴与海浪环境声" in music_payload["41"]["inputs"]["text"]
    assert music_payload["42"]["inputs"]["duration"] == 30.0
    assert isinstance(music_payload["43"]["inputs"]["seed"], int)


def test_audio_output_utils_can_normalize_flac_source_to_real_wav(tmp_path: Path) -> None:
    ffmpeg = audio_output_utils.find_ffmpeg()
    if not ffmpeg:
        raise AssertionError("ffmpeg is required for audio normalization test")
    wav_source = tmp_path / "source.wav"
    wav_source.write_bytes(
        b"RIFF$\x00\x00\x00WAVEfmt "
        b"\x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xAC\x00\x00\x88\x58\x01\x00"
        b"\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    flac_source = tmp_path / "source.flac"
    target_wav = tmp_path / "target.wav"
    result = subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav_source), "-c:a", "flac", str(flac_source)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    materialized = audio_output_utils.materialize_audio_output(
        {"resolved_path": str(flac_source), "filename": flac_source.name},
        target_wav,
    )
    header = target_wav.read_bytes()[:12]
    assert header[:4] == b"RIFF"
    assert header[8:12] == b"WAVE"
    assert materialized["mode"] == "transcoded"
    assert materialized["target_container"] == "wav"


def test_run_comfyui_indextts2_failure_records_errors(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_voice_output"
    server, thread = _start_server(
        "missing_output",
        output_root=output_root,
        prompt_prefix="prompt-voice",
        filename="voice.wav",
        subfolder="voice",
    )
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_indextts2.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        voice_jobs = [job for job in data["jobs"] if job["audio_type"] in {"voiceover", "dialogue"}]
        assert len(voice_jobs) == 1
        assert voice_jobs[0]["status"] == "failed"
        assert voice_jobs[0]["errors"]
        request_manifest = json.loads((manifest_json.parent / "indextts2_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "failed"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_indextts2_reuses_existing_audio_when_cached_history_has_no_outputs(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_voice_output"
    existing_voice = manifest_json.parent / "voice" / "S001_voiceover.wav"
    existing_voice.parent.mkdir(parents=True, exist_ok=True)
    existing_voice.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xAC\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    server, thread = _start_server(
        "missing_output",
        output_root=output_root,
        prompt_prefix="prompt-voice",
        filename="voice.wav",
        subfolder="voice",
    )
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_indextts2.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        voice_jobs = [job for job in data["jobs"] if job["audio_type"] in {"voiceover", "dialogue"}]
        assert voice_jobs[0]["status"] == "succeeded"
        request_manifest = json.loads((manifest_json.parent / "indextts2_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "succeeded"
        assert request_manifest["requests"][0]["materialized_output"]["mode"] == "reused_existing"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_music_failure_records_errors(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "missing_output",
        output_root=output_root,
        prompt_prefix="prompt-music",
        filename="music.wav",
        subfolder="music",
    )
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_music.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        music_jobs = [job for job in data["jobs"] if job["audio_type"] == "music"]
        assert len(music_jobs) == 1
        assert music_jobs[0]["status"] == "failed"
        assert music_jobs[0]["errors"]
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "failed"
        assert "ComfyUI music workflow did not produce any audio outputs" in request_manifest["requests"][0]["error_message"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_music_execution_error_records_node_details(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "execution_error",
        output_root=output_root,
        prompt_prefix="prompt-music",
        filename="music.wav",
        subfolder="music",
    )
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_music.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 1
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert "MusicPromptNode" in request_manifest["requests"][0]["error_message"]
        assert "mock execution failure" in request_manifest["requests"][0]["error_message"]
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        music_jobs = [job for job in data["jobs"] if job["audio_type"] == "music"]
        assert "MusicPromptNode" in music_jobs[0]["errors"][0]["message"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_heartmula_prompt_builder_creates_global_tags_and_lyrics(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
    prompt = heartmula_prompt_builder.build_heartmula_prompt(manifest_json, music_job)
    assert prompt["global_tags"].startswith("Global Tags: ")
    assert prompt["global_tags"].endswith("/")
    assert "Mandopop" in prompt["global_tags"]
    assert "Lyrics:" in prompt["lyrics"]
    assert "[Intro:" in prompt["lyrics"]
    assert "[Pre-Chorus:" in prompt["lyrics"]
    assert "[Bridge:" in prompt["lyrics"]


def test_acestep_prompt_builder_returns_workflow_fields(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
    prompt = acestep_prompt_builder.build_acestep_prompt(manifest_json, music_job)
    assert prompt["profile"] == "underscore"
    assert "[genre:" in prompt["tags"]
    assert "mandopop" in prompt["tags"].lower()
    assert "no vocals" in prompt["tags"].lower()
    assert "[verse" in prompt["lyrics"]
    assert "[chorus" in prompt["lyrics"]
    assert prompt["language"] == "zh"
    assert isinstance(prompt["bpm"], int)
    assert isinstance(prompt["keyscale"], str)
    assert prompt["timesignature"] == "4"


def test_acestep_prompt_builder_supports_song_profile(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    _set_music_profile(manifest_json, "song")
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
    prompt = acestep_prompt_builder.build_acestep_prompt(manifest_json, music_job, profile="song")
    assert prompt["profile"] == "song"
    assert "female vocal" in prompt["tags"].lower()
    assert "intimate lead vocal" in prompt["lyrics"].lower()


def test_acestep_prompt_builder_supports_instrumental_profile(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    _set_music_profile(manifest_json, "instrumental")
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
    prompt = acestep_prompt_builder.build_acestep_prompt(manifest_json, music_job)
    assert prompt["profile"] == "instrumental"
    assert "no vocals" in prompt["tags"].lower()
    assert "纯器乐" in prompt["lyrics"]


def test_run_comfyui_music_heartmula_workflow_submits_tags_and_lyrics(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_heartmula_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "success",
        output_root=output_root,
        prompt_prefix="prompt-music",
        filename="music.wav",
        subfolder="music",
    )
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_port}",
            output_root=output_root,
        )
        assert run_comfyui_music.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        music_payload = _FakeAudioHandler.requests[0]["prompt"]
        heart_input = music_payload["14"]["inputs"]
        assert heart_input["tags"].startswith("Global Tags: ")
        assert heart_input["tags"].endswith("/")
        assert "Lyrics:" in heart_input["lyrics"]
        assert "[Intro:" in heart_input["lyrics"]
        assert heart_input["max_audio_length_seconds"] == 30
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["heartmula_prompt"]["global_tags"].startswith("Global Tags: ")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_music_acestep_workflow_submits_duration_and_seed(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    _set_music_profile(manifest_json, "song")
    mapping_path = _write_acestep_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "success",
        output_root=output_root,
        prompt_prefix="prompt-music",
        filename="music.wav",
        subfolder="music",
    )
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_port}",
            output_root=output_root,
        )
        assert run_comfyui_music.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--workflow-name", "music_generation_acestep",
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        music_payload = _FakeAudioHandler.requests[0]["prompt"]
        ace_input = music_payload["94"]["inputs"]
        assert "[genre:" in ace_input["tags"]
        assert "female vocal" in ace_input["tags"].lower()
        assert "[chorus" in ace_input["lyrics"]
        assert ace_input["duration"] == 30.0
        assert music_payload["98"]["inputs"]["seconds"] == 30.0
        assert isinstance(ace_input["bpm"], int)
        assert ace_input["language"] == "zh"
        assert isinstance(ace_input["keyscale"], str)
        assert ace_input["timesignature"] == "4"
        assert isinstance(music_payload["109"]["inputs"]["value"], int)
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["workflow_name"] == "music_generation_acestep"
        assert request_manifest["requests"][0]["workflow_name"] == "music_generation_acestep"
        assert request_manifest["requests"][0]["music_profile"] == "song"
        assert request_manifest["requests"][0]["acestep_prompt"]["profile"] == "song"
        assert "[genre:" in request_manifest["requests"][0]["acestep_prompt"]["tags"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_music_dry_run_with_heartmula_mapping_records_built_prompt(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_heartmula_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_music.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--dry-run",
    ]) == 0
    request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["requests"][0]["status"] == "planned"
    assert request_manifest["requests"][0]["music_prompt"] == "轻柔钢琴与海浪环境声"


def test_run_comfyui_music_timeout_marks_running_instead_of_failed(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflows(tmp_path)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "queue_running",
        output_root=output_root,
        prompt_prefix="prompt-music",
        filename="music.wav",
        subfolder="music",
    )
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_port}",
            output_root=output_root,
        )
        assert run_comfyui_music.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "0.05",
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
        assert music_job["status"] == "running"
        assert music_job["errors"] == []
        assert data["self_check"]["ready_for_assembly_stage"] is False
        assert data["allowed_next_stage"] is None
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "running"
        assert request_manifest["requests"][0]["error_message"] is None
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_sync_comfyui_music_result_marks_queue_running(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    prompt_id = "prompt-music-sync-running"
    _FakeAudioHandler.active_prompt_id = prompt_id
    _write_request_manifest_for_prompt(manifest_json, prompt_id=prompt_id)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "queue_running",
        output_root=output_root,
        prompt_prefix="prompt-music-sync",
        filename="music.wav",
        subfolder="music",
    )
    _FakeAudioHandler.active_prompt_id = prompt_id
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_port}",
            output_root=output_root,
        )
        assert sync_comfyui_music_result.main([
            str(manifest_json),
            "--config", str(config_path),
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
        assert music_job["status"] == "running"
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "running"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_sync_comfyui_music_result_history_success_materializes_audio(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    prompt_id = "prompt-music-success-1"
    _write_request_manifest_for_prompt(manifest_json, prompt_id=prompt_id)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "success",
        output_root=output_root,
        prompt_prefix="prompt-music-success",
        filename="music.wav",
        subfolder="music",
    )
    _FakeAudioHandler.active_prompt_id = prompt_id
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_port}",
            output_root=output_root,
        )
        assert sync_comfyui_music_result.main([
            str(manifest_json),
            "--config", str(config_path),
        ]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
        assert music_job["status"] == "succeeded"
        assert music_job["evidence"]["file_exists"] is True
        assert music_job["evidence"]["detected_container"] == "wav"
        assert music_job["evidence"]["source_container"] == "wav"
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "succeeded"
        assert request_manifest["requests"][0]["materialized_output"]["target_container"] == "wav"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_sync_comfyui_music_result_marks_user_cancelled(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    prompt_id = "prompt-music-cancelled-1"
    _write_request_manifest_for_prompt(manifest_json, prompt_id=prompt_id)
    output_root = tmp_path / "comfy_music_output"
    server, thread = _start_server(
        "cancelled",
        output_root=output_root,
        prompt_prefix="prompt-music-cancelled",
        filename="music.wav",
        subfolder="music",
    )
    _FakeAudioHandler.active_prompt_id = prompt_id
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_port}",
            output_root=output_root,
        )
        assert sync_comfyui_music_result.main([
            str(manifest_json),
            "--config", str(config_path),
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        music_job = next(job for job in data["jobs"] if job["audio_type"] == "music")
        assert music_job["status"] == "cancelled"
        assert "Cancelled by user" in music_job["errors"][0]["message"]
        assert data["self_check"]["ready_for_assembly_stage"] is False
        request_manifest = json.loads((manifest_json.parent / "music_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "cancelled"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
