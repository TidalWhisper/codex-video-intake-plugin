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
stage06_risk_profiles = load_module("stage06_risk_profiles_ltx_test", ROOT / "scripts" / "pipeline_core" / "stage06_risk_profiles.py")
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
        (out_dir / "ltx_clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42LTXTEST" + (b"0" * 512))
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
        "1": {"inputs": {"reserved": 0.6, "auto_max_reserved": 0.0, "clean_gpu_before": True, "seed": 1}, "class_type": "ReservedVRAMSetter"},
        "11": {"inputs": {"image": ""}, "class_type": "LoadImage"},
        "12": {"inputs": {"image": ""}, "class_type": "LoadImage"},
        "16": {"inputs": {"image_paths": ""}, "class_type": "MultiImageLoader"},
        "13": {"inputs": {"global_prompt": "", "local_prompts": "", "segment_lengths": "", "epsilon": 0.001}, "class_type": "PromptRelayEncode"},
        "14": {"inputs": {"seed": 1, "frames": 120, "fps": 24, "start_guide_frame": 0, "mid_guide_frame": 60, "end_guide_frame": 119, "start_guide_strength": 0.9, "mid_guide_strength": 1.0, "end_guide_strength": 0.96, "num_guide_images": 2}, "class_type": "LTXVideo"},
        "15": {"inputs": {"filename_prefix": "i2v/ltx_clip", "format": "mp4", "codec": "h264"}, "class_type": "SaveVideo"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping = {
        "workflows": {
            "i2v_ltx": {
                "file": str(workflow_path).replace("\\", "/"),
                "capabilities": {
                    "route_family": "first_last_frame_two_stage",
                    "supports_route_hints": ["single_subject_motion", "interaction_handoff"],
                    "supports_subject_count_range": {"min": 1, "max": 2},
                    "requires_additional_guides_for_route_hints": {
                        "interaction_handoff": {
                            "required_count": 3,
                            "fallback_action": "add_mid_keyframe_or_split_shot",
                        }
                    },
                },
                "nodes": {
                    "start_image": {"node_id": "11", "input_name": "image"},
                    "end_image": {"node_id": "12", "input_name": "image"},
                    "guide_image_paths": {"node_id": "16", "input_name": "image_paths"},
                    "global_prompt": {"node_id": "13", "input_name": "global_prompt"},
                    "local_prompts": {"node_id": "13", "input_name": "local_prompts"},
                    "segment_lengths": {"node_id": "13", "input_name": "segment_lengths"},
                    "prompt_relay_epsilon": {"node_id": "13", "input_name": "epsilon"},
                    "seed": {"node_id": "14", "input_name": "seed"},
                    "frame_count": {"node_id": "14", "input_name": "frames"},
                    "fps": {"node_id": "14", "input_name": "fps"},
                    "start_guide_frame": {"node_id": "14", "input_name": "start_guide_frame"},
                    "mid_guide_frame": {"node_id": "14", "input_name": "mid_guide_frame"},
                    "end_guide_frame": {"node_id": "14", "input_name": "end_guide_frame"},
                    "start_guide_strength": {"node_id": "14", "input_name": "start_guide_strength"},
                    "mid_guide_strength": {"node_id": "14", "input_name": "mid_guide_strength"},
                    "end_guide_strength": {"node_id": "14", "input_name": "end_guide_strength"},
                    "num_guide_images": {"node_id": "14", "input_name": "num_guide_images"},
                    "vram_reserved_gb": {"node_id": "1", "input_name": "reserved"},
                    "vram_auto_max_reserved_gb": {"node_id": "1", "input_name": "auto_max_reserved"},
                    "clean_gpu_before": {"node_id": "1", "input_name": "clean_gpu_before"},
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


def _prepare_interaction_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_interaction_handoff"
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
    storyboard["shots"] = [{
        "shot_id": "S001",
        "start": "00:00",
        "end": "00:04",
        "duration_sec": 4,
        "scene": "雨夜便利店门口",
        "location": "便利店门口",
        "weather": "雨夜",
        "key_prop": "最后一把伞",
        "camera": "wide shot",
        "composition": "两个人在便利店门口完成最后一把伞的交接，机位稳定，保持双人同框。",
        "composition_focus": "双人交接动作与雨夜便利店门口环境必须同时清晰可读。",
        "action": "20岁出头的女孩把最后一把伞留给陌生人",
        "emotion": "克制善意",
        "production_note": "这是一个双人交接镜头，需要保持共享雨伞和握持关系稳定。",
    }]
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["shot_prompts"] = [{
        "shot_id": "S001",
        "duration_sec": 4,
        "characters": ["CHAR_001"],
        "scene_summary": "地点：便利店门口 / 天气：雨夜 / 动作：20岁出头的女孩把最后一把伞留给陌生人 / 道具：最后一把伞 / 情绪：克制善意",
        "intent_summary": "双人交接镜头，女孩把最后一把伞留给陌生人。",
        "motion_prompt": "A restrained umbrella handoff between the girl and a stranger under one umbrella.",
        "camera_prompt": "wide shot",
        "style_prompt": "写实电影感 克制善意 visual treatment",
        "consistency_prompt": "Keep the rainy convenience store entrance and shared umbrella relationship stable.",
        "negative_prompt": "extra limbs, extra people, wrong prop count",
        "performance_prompt": "restrained umbrella handoff with readable grip change",
        "dialogue_delivery_prompt": "Deliver any spoken line quietly.",
    }]
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


def _apply_interaction_handoff_profile(manifest_json: Path) -> None:
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    job = data["jobs"][0]
    job["duration_sec"] = 4.0
    job["route_hint"] = "interaction_handoff"
    job["generation_risk_profile"] = "high_interaction_semantic_delta"
    job["camera_lock_required"] = True
    job["expected_subject_count"] = 2
    job["expected_key_prop_count"] = 1
    job["recommended_max_duration_sec"] = 2.5
    job["motion_prompt"] = "20岁出头的女孩把最后一把伞留给陌生人，镜头只完成一次清晰的交接动作。"
    job["performance_prompt"] = "Restrained umbrella handoff timing with readable grip change."
    job["camera_prompt"] = "wide shot"
    job["negative_prompt"] = "extra limbs, extra people, wrong prop count, foreground occlusion"
    job["story_anchor_bundle"] = {
        "location": "便利店门口",
        "weather": "雨夜",
        "key_prop": "最后一把伞",
        "emotion": "克制善意",
        "action": "20岁出头的女孩把最后一把伞留给陌生人",
    }
    job["prompt_constraints"] = [
        "Lock the camera on a stable frontal axis; no orbit, whip, or handheld sway.",
        "Keep exactly two readable subjects in frame from start to finish.",
        "Keep exactly one shared 最后一把伞 in frame.",
        "Preserve a clear giver-receiver handoff relationship with readable hand contact.",
    ]
    manifest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_stage06_risk_profile_detects_interaction_handoff() -> None:
    profile = stage06_risk_profiles.classify_stage06_generation(
        {
            "scene_summary": "地点：便利店门口 / 天气：雨夜 / 动作：20岁出头的女孩把最后一把伞留给陌生人 / 道具：最后一把伞 / 情绪：克制善意",
            "intent_summary": "雨夜里把最后一把伞留给陌生人。",
            "motion_prompt": "A restrained umbrella handoff between the girl and a stranger.",
        },
        {
            "action": "20岁出头的女孩把最后一把伞留给陌生人",
            "composition": "两人都在便利店门口画面内，保持共享雨伞关系。",
        },
        {
            "location": "便利店门口",
            "weather": "雨夜",
            "key_prop": "最后一把伞",
            "emotion": "克制善意",
            "action": "20岁出头的女孩把最后一把伞留给陌生人",
        },
    )
    assert profile["route_hint"] == "interaction_handoff"
    assert profile["generation_risk_profile"] == "high_interaction_semantic_delta"
    assert profile["camera_lock_required"] is True
    assert profile["expected_subject_count"] == 2
    assert profile["recommended_max_duration_sec"] == 2.5
    assert any("exactly two readable subjects" in item for item in profile["prompt_constraints"])


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


def test_new_keyframe_image_jobs_scaffolds_mid_for_interaction_handoff(tmp_path: Path) -> None:
    manifest_json = _prepare_interaction_manifest(tmp_path)
    clip_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    image_manifest_json = Path(clip_manifest["source_keyframe_image_manifest"])
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))

    assert image_manifest["shot_frame_requirements"]["S001"] == ["start", "mid", "end"]
    assert [job["frame_role"] for job in image_manifest["jobs"]] == ["start", "mid", "end"]
    mid_job = next(job for job in image_manifest["jobs"] if job["frame_role"] == "mid")
    assert mid_job["image_id"] == "IMG_S001_MID"
    assert mid_job["stage06_route_hint"] == "interaction_handoff"
    assert mid_job["stage06_requires_mid_guide"] is True
    assert "readable handoff contact" in mid_job["prompt"]
    assert "Character identity anchor:" in mid_job["consistency_prompt"]


def test_new_video_clip_jobs_blocks_high_risk_interaction_without_mid_guide(tmp_path: Path) -> None:
    manifest_json = _prepare_interaction_manifest(tmp_path)
    initial_data = json.loads(manifest_json.read_text(encoding="utf-8"))
    image_manifest_json = Path(initial_data["source_keyframe_image_manifest"])
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["jobs"] = [job for job in image_manifest["jobs"] if job.get("frame_role") != "mid"]
    image_manifest["summary"]["expected_image_count"] = len(image_manifest["jobs"])
    image_manifest["summary"]["generated_image_count"] = len(image_manifest["jobs"])
    image_manifest["summary"]["required_mid_image_count"] = 0
    image_manifest["shot_frame_requirements"]["S001"] = ["start", "mid", "end"]
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        initial_data["source_brief"],
        initial_data["source_storyboard"],
        initial_data["source_keyframe_prompts"],
        str(image_manifest_json),
        str(manifest_json),
    ]) == 0

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["status"] == "blocked"
    assert data["summary"]["blocked_clip_count"] == 1
    assert data["quality_signals"]["workflow_capability_safe_for_all_jobs"] is False
    job = data["jobs"][0]
    assert job["status"] == "blocked"
    assert job["route_hint"] == "interaction_handoff"
    assert job["requires_mid_guide"] is True
    assert job["required_additional_guides"] == ["mid"]
    assert any("add_mid_keyframe_or_split_shot" in item for item in job["blocking_reasons"])


def test_new_video_clip_jobs_blocks_when_mid_job_exists_but_mid_file_is_missing(tmp_path: Path) -> None:
    manifest_json = _prepare_interaction_manifest(tmp_path)
    initial_data = json.loads(manifest_json.read_text(encoding="utf-8"))
    image_manifest_json = Path(initial_data["source_keyframe_image_manifest"])
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    mid_job = next(job for job in image_manifest["jobs"] if job.get("frame_role") == "mid")
    mid_path = Path(mid_job["output_path"])
    if mid_path.exists():
        mid_path.unlink()
    mid_job["evidence"]["file_exists"] = False
    mid_job["evidence"]["file_size_bytes"] = 0
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        initial_data["source_brief"],
        initial_data["source_storyboard"],
        initial_data["source_keyframe_prompts"],
        str(image_manifest_json),
        str(manifest_json),
    ]) == 0

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    job = data["jobs"][0]
    assert job["source_keyframes"]["mid"] == ""
    assert any("add_mid_keyframe_or_split_shot" in item for item in job["blocking_reasons"])


def test_new_video_clip_jobs_can_replan_from_in_progress_stage05_when_override_is_enabled(tmp_path: Path) -> None:
    manifest_json = _prepare_interaction_manifest(tmp_path)
    initial_data = json.loads(manifest_json.read_text(encoding="utf-8"))
    image_manifest_json = Path(initial_data["source_keyframe_image_manifest"])
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    image_manifest["status"] = "in_progress"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        initial_data["source_brief"],
        initial_data["source_storyboard"],
        initial_data["source_keyframe_prompts"],
        str(image_manifest_json),
        str(manifest_json),
        "--allow-stage05-in-progress",
    ]) == 0

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["planning_overrides"]["allow_stage05_in_progress"] is True
    assert any("Stage 06 planning was explicitly allowed while Stage 05 remains in_progress" in item for item in data["self_check"]["notes"])
    assert data["jobs"][0]["route_hint"] == "interaction_handoff"


def test_new_video_clip_jobs_allows_interaction_handoff_once_mid_guide_is_available(tmp_path: Path) -> None:
    manifest_json = _prepare_interaction_manifest(tmp_path)
    data = json.loads(manifest_json.read_text(encoding="utf-8"))

    assert data["status"] == "draft"
    assert data["summary"]["blocked_clip_count"] == 0
    job = data["jobs"][0]
    assert job["source_keyframes"]["mid"].endswith("S001_mid.png")
    assert job["route_hint"] == "interaction_handoff"
    assert job["requires_mid_guide"] is True
    assert job["required_additional_guides"] == ["mid"]
    assert job["blocking_reasons"] == []
    assert job["status"] == "pending"


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


def test_run_comfyui_ltx_i2v_refuses_blocked_job(tmp_path: Path) -> None:
    manifest_json = _prepare_interaction_manifest(tmp_path)
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    data["status"] = "blocked"
    data["summary"]["blocked_clip_count"] = 1
    data["quality_signals"]["workflow_capability_safe_for_all_jobs"] = False
    data["jobs"][0]["status"] = "blocked"
    data["jobs"][0]["blocking_reasons"] = ["route 'interaction_handoff' requires at least 3 guide keyframes on this workflow; current shot only has start/end. Next action: add_mid_keyframe_or_split_shot"]
    manifest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping_path = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    assert run_comfyui_ltx_i2v.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--clip-id", "CLIP_S001",
    ]) == 1
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["jobs"][0]["status"] == "blocked"
    assert data["jobs"][0]["errors"]
    request_manifest = json.loads((manifest_json.parent / "comfyui_ltx_i2v_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["requests"][0]["status"] == "blocked"
    assert "add_mid_keyframe_or_split_shot" in request_manifest["requests"][0]["error_message"]


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
        assert request_manifest["requests"][0]["fps"] == 24
        assert request_manifest["requests"][0]["duration_sec"] >= 1
        assert "|" in request_manifest["requests"][0]["prompt_relay_local_prompts"]
        assert _FakeLtxHandler.requests[0]["client_id"].startswith("codex-stage06-")
        workflow_payload = _FakeLtxHandler.requests[0]["prompt"]
        assert workflow_payload["14"]["inputs"]["fps"] == 24
        assert workflow_payload["14"]["inputs"]["frames"] > 0
        assert workflow_payload["14"]["inputs"]["end_guide_frame"] < workflow_payload["14"]["inputs"]["frames"]
        assert workflow_payload["14"]["inputs"]["num_guide_images"] == 2
        assert workflow_payload["11"]["inputs"]["image"].endswith(".png")
        assert workflow_payload["12"]["inputs"]["image"].endswith(".png")
        assert workflow_payload["13"]["inputs"]["global_prompt"]
        assert "|" in workflow_payload["13"]["inputs"]["local_prompts"]
        assert workflow_payload["1"]["inputs"]["reserved"] == 1.2
        assert workflow_payload["1"]["inputs"]["clean_gpu_before"] is True
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_ltx_i2v_applies_interaction_handoff_clamp_and_constraints(tmp_path: Path) -> None:
    manifest_json = _prepare_interaction_manifest(tmp_path)
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
        request_manifest = json.loads((manifest_json.parent / "comfyui_ltx_i2v_requests.json").read_text(encoding="utf-8"))
        request = request_manifest["requests"][0]
        assert request["route_hint"] == "interaction_handoff"
        assert request["camera_lock_required"] is True
        assert request["expected_subject_count"] == 2
        assert request["requested_duration_sec"] == 4.0
        assert request["duration_sec"] == 2.5
        assert request["duration_was_clamped"] is True
        assert request["guide_image_count_planned"] == 3
        assert request["prompt_relay_segment_lengths"] == "40,17"
        assert "exactly two readable subjects" in request["prompt_relay_local_prompts"]
        assert "exactly one subject" not in request["prompt_relay_local_prompts"]
        workflow_payload = _FakeLtxHandler.requests[0]["prompt"]
        assert workflow_payload["14"]["inputs"]["frames"] < 97
        assert workflow_payload["14"]["inputs"]["num_guide_images"] == 3
        assert workflow_payload["14"]["inputs"]["mid_guide_frame"] > 0
        assert workflow_payload["14"]["inputs"]["start_guide_strength"] == 0.98
        assert workflow_payload["14"]["inputs"]["mid_guide_strength"] == 1.0
        assert workflow_payload["14"]["inputs"]["end_guide_strength"] == 0.9
        assert len(workflow_payload["16"]["inputs"]["image_paths"].splitlines()) == 3
        assert "Keep exactly two readable subjects in frame from start to finish." in workflow_payload["13"]["inputs"]["local_prompts"]
        assert request["staged_mid_image"].endswith(".png")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_ltx_i2v_uses_saved_video_fallback_when_history_outputs_are_empty(tmp_path: Path) -> None:
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
        ]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        assert data["jobs"][0]["status"] == "succeeded"
        assert data["jobs"][0]["errors"] == []
        request_manifest = json.loads((manifest_json.parent / "comfyui_ltx_i2v_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "succeeded"
        assert request_manifest["requests"][0]["selected_output"]["filename"] == "ltx_clip.mp4"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_ltx_i2v_failure_records_errors(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("missing_file", output_root=output_root)
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


def test_run_comfyui_ltx_i2v_timeout_marks_job_running_instead_of_failed(tmp_path: Path, monkeypatch) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)

        def _timeout(*args, **kwargs):
            raise run_comfyui_ltx_i2v.ComfyUIError(
                f"Timed out waiting for ComfyUI prompt {_FakeLtxHandler.prompt_id}",
                kind="timeout",
            )

        monkeypatch.setattr(run_comfyui_ltx_i2v.ComfyUIClient, "wait_for_prompt", _timeout)
        monkeypatch.setattr(run_comfyui_ltx_i2v.ComfyUIClient, "get_history", lambda self, prompt_id: {})
        monkeypatch.setattr(
            run_comfyui_ltx_i2v.ComfyUIClient,
            "get_queue",
            lambda self: {"queue_running": [[1, _FakeLtxHandler.prompt_id, {}]], "queue_pending": []},
        )

        assert run_comfyui_ltx_i2v.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 1

        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        assert data["status"] == "in_progress"
        assert data["jobs"][0]["status"] == "running"
        assert data["jobs"][0]["errors"] == []
        request_manifest = json.loads((manifest_json.parent / "comfyui_ltx_i2v_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "running"
        assert request_manifest["requests"][0]["prompt_id"] == _FakeLtxHandler.prompt_id
        assert request_manifest["requests"][0]["completed_at"] is None
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
