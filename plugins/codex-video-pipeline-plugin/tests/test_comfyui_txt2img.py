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
comfyui_ui_workflow = load_module("comfyui_ui_workflow_test", PROVIDERS / "comfyui_ui_workflow.py")
build_stage05_zimage_photo_bridge = load_module(
    "build_stage05_zimage_photo_bridge_test",
    PROVIDERS / "build_stage05_zimage_photo_bridge.py",
)
build_stage05_zimage_image_b_bridge = load_module(
    "build_stage05_zimage_image_b_bridge_test",
    PROVIDERS / "build_stage05_zimage_image_b_bridge.py",
)


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


def _write_config(tmp_path: Path, *, base_url: str, output_root: Path, input_root: Path | None = None) -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = False
    data["comfyui"]["enabled"] = True
    data["comfyui"]["base_url"] = base_url
    if input_root is not None:
        data["comfyui"]["input_dir"] = str(input_root).replace("\\", "/")
    data["comfyui"]["output_dir"] = str(output_root).replace("\\", "/")
    config_path = tmp_path / "providers.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def _write_mapping_and_workflow(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    workflow_names = [
        "txt2img_keyframe",
        "txt2img_keyframe_realistic",
        "txt2img_keyframe_realistic_zimage_photo_bridge",
        "stage05_realistic_cinematic_amazing_z_photo_original",
        "txt2img_keyframe_shortdrama_qwen_edit_reference",
        "txt2img_keyframe_shortdrama_qwen_edit_dual_reference",
        "txt2img_keyframe_stylized_zimage_image_b_bridge",
        "txt2img_keyframe_game_cg_clean_plate",
        "txt2img_keyframe_anime",
        "txt2img_keyframe_anime_cn_newguofeng",
        "txt2img_keyframe_guofeng",
        "txt2img_keyframe_guofeng_ink",
        "txt2img_keyframe_stylized",
        "txt2img_keyframe_stylized_concept",
    ]
    mapping_alias_to_workflow = {
        "txt2img_keyframe": "txt2img_keyframe",
        "txt2img_keyframe_realistic": "txt2img_keyframe_realistic",
        "txt2img_keyframe_anime": "txt2img_keyframe_anime",
        "txt2img_keyframe_guofeng": "txt2img_keyframe_guofeng",
        "txt2img_keyframe_stylized": "txt2img_keyframe_stylized",
        "stage05_realistic_cinematic": "txt2img_keyframe_realistic_zimage_photo_bridge",
        "stage05_realistic_cinematic_qwen2512_prompt_only": "txt2img_keyframe_realistic",
        "stage05_realistic_cinematic_qwen_edit_reference": "txt2img_keyframe_shortdrama_qwen_edit_reference",
        "stage05_realistic_cinematic_qwen_edit_dual_reference": "txt2img_keyframe_shortdrama_qwen_edit_dual_reference",
        "stage05_shortdrama_realistic": "txt2img_keyframe_realistic",
        "stage05_shortdrama_realistic_qwen_edit_reference": "txt2img_keyframe_shortdrama_qwen_edit_reference",
        "stage05_shortdrama_realistic_qwen_edit_dual_reference": "txt2img_keyframe_shortdrama_qwen_edit_dual_reference",
        "stage05_realistic_cinematic_zimage_photo_bridge": "txt2img_keyframe_realistic_zimage_photo_bridge",
        "stage05_realistic_cinematic_amazing_z_photo_original": "stage05_realistic_cinematic_amazing_z_photo_original",
        "stage05_anime_jp": "txt2img_keyframe_anime",
        "stage05_anime_cn_newguofeng": "txt2img_keyframe_anime_cn_newguofeng",
        "stage05_western_cartoon": "txt2img_keyframe_anime",
        "stage05_guofeng_ink": "txt2img_keyframe_guofeng_ink",
        "stage05_stylized_concept": "txt2img_keyframe_stylized_zimage_image_b_bridge",
        "stage05_stylized_concept_zimage_image_b_bridge": "txt2img_keyframe_stylized_zimage_image_b_bridge",
        "stage05_game_cg": "txt2img_keyframe_game_cg_clean_plate",
    }
    workflow_paths: dict[str, Path] = {}
    mapping_workflows: dict[str, dict] = {}
    for workflow_name in workflow_names:
        workflow_path = tmp_path / f"{workflow_name}.workflow_api.json"
        if workflow_name == "stage05_realistic_cinematic_amazing_z_photo_original":
            workflow_payload = {
                "nodes": [
                    {"id": 57, "type": "PrimitiveNode", "widgets_values": ["placeholder prompt"]},
                    {"id": 88, "type": "Fast Muter (rgthree)", "mode": 0},
                    {"id": 90, "type": "PrimitiveString", "widgets_values": ["{$@}"], "mode": 0},
                    {"id": 38, "type": "PrimitiveStringMultiline", "widgets_values": ["PRODUCTION {$@}"], "mode": 2},
                    {"id": 92, "type": "PrimitiveStringMultiline", "widgets_values": ["CLASSIC {$@}"], "mode": 2},
                    {"id": 459, "type": "PrimitiveStringMultiline", "widgets_values": ["DOCUMENTARY {$@}"], "mode": 2},
                    {"id": 307, "type": "PrimitiveInt", "widgets_values": [1, "fixed"]},
                    {"id": 243, "type": "PrimitiveInt", "widgets_values": [1088, "fixed"]},
                    {"id": 248, "type": "PrimitiveInt", "widgets_values": [1600, "fixed"]},
                    {"id": 9, "type": "SaveImage", "widgets_values": ["ZImage/test/ZI"]},
                ]
            }
        elif workflow_name in {"txt2img_keyframe_shortdrama_qwen_edit_reference", "txt2img_keyframe_shortdrama_qwen_edit_dual_reference"}:
            workflow_payload = {
                "10": {"inputs": {"image": "reference.png"}, "class_type": "LoadImage"},
                "11": {"inputs": {"image": "reference_context.png"}, "class_type": "LoadImage"},
                "20": {"inputs": {"width": 512, "height": 512}, "class_type": "ImageScale"},
                "22": {"inputs": {"prompt": "", "image2": ["11", 0]}, "class_type": "TextEncodeQwenImageEditPlus"},
                "23": {"inputs": {"prompt": "", "image2": ["11", 0]}, "class_type": "TextEncodeQwenImageEditPlus"},
                "30": {"inputs": {"seed": 1}, "class_type": "KSampler"},
                "50": {"inputs": {}, "class_type": "SaveImage"},
            }
        else:
            workflow_payload = {
                "6": {"inputs": {"text": ""}, "class_type": "CLIPTextEncode"},
                "7": {"inputs": {"text": ""}, "class_type": "CLIPTextEncode"},
                "3": {"inputs": {"seed": 1}, "class_type": "KSampler"},
                "5": {"inputs": {"width": 512, "height": 512}, "class_type": "EmptyLatentImage"},
                "9": {"inputs": {}, "class_type": "SaveImage"},
            }
        workflow_path.write_text(json.dumps(workflow_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        workflow_paths[workflow_name] = workflow_path
    for mapping_key, workflow_name in mapping_alias_to_workflow.items():
        if workflow_name in {"txt2img_keyframe_shortdrama_qwen_edit_reference", "txt2img_keyframe_shortdrama_qwen_edit_dual_reference"}:
            mapping_workflows[mapping_key] = {
                "file": str(workflow_paths[workflow_name]).replace("\\", "/"),
                "nodes": {
                    "positive_prompt": {"node_id": "22", "input_name": "prompt"},
                    "negative_prompt": {"node_id": "23", "input_name": "prompt"},
                    "reference_image_path": {"node_id": "10", "input_name": "image"},
                    "reference_image_path_2": {"node_id": "11", "input_name": "image"},
                    "seed": {"node_id": "30", "input_name": "seed"},
                    "width": {"node_id": "20", "input_name": "width"},
                    "height": {"node_id": "20", "input_name": "height"},
                },
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["prompt_only", "reference_guided"],
                },
            }
        elif workflow_name == "stage05_realistic_cinematic_amazing_z_photo_original":
            mapping_workflows[mapping_key] = {
                "file": str(workflow_paths[workflow_name]).replace("\\", "/"),
                "workflow_format": "ui_graph",
                "nodes": {
                    "positive_prompt": {"node_id": "57", "control": "widget_value", "widget_index": 0},
                    "style_selector": {
                        "node_id": "88",
                        "control": "choice_set_mode",
                        "default_choice": "none",
                        "choices": {
                            "none": {"node_id": "90"},
                            "production_photo": {"node_id": "38"},
                            "classic_film_photo": {"node_id": "92"},
                            "street_documentary_photo": {"node_id": "459"},
                        },
                    },
                    "seed": {"node_id": "307", "control": "widget_value", "widget_index": 0},
                    "short_side": {"node_id": "243", "control": "widget_value", "widget_index": 0},
                    "long_side": {"node_id": "248", "control": "widget_value", "widget_index": 0},
                    "output_prefix": {"node_id": "9", "control": "widget_value", "widget_index": 0},
                },
            }
        else:
            mapping_workflows[mapping_key] = {
                "file": str(workflow_paths[workflow_name]).replace("\\", "/"),
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


def _mark_job_missing_character_reference(manifest_json: Path, image_id: str) -> None:
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    for job in data["jobs"]:
        if job["image_id"] != image_id:
            continue
        job["reference_images"] = [
            "plugins/codex-video-pipeline-plugin/video_projects/demo_project/03_characters/reference_images/CHAR_001_primary.png"
        ]
        job["missing_reference_images"] = list(job["reference_images"])
        job["stage06_requires_mid_guide"] = True
        job["quality_gate"] = {
            "risk_tags": ["missing_character_reference"],
            "control_mode": "prompt_only",
            "requires_manual_review": True,
            "manual_review_status": "pending",
            "reason": "Character-locked continuity is required, but no Stage 03 reference image is available for this shot.",
        }
        break
    manifest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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


def test_workflow_mapping_applies_single_replacement_to_multiple_nodes(tmp_path: Path) -> None:
    workflow_path = tmp_path / "anime.workflow_api.json"
    workflow_path.write_text(json.dumps({
        "30": {"inputs": {"noise_seed": 1, "cfg": 1.0}, "class_type": "SamplerCustom"},
        "35": {"inputs": {"noise_seed": 1, "cfg": 1.0}, "class_type": "SamplerCustom"},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    mapping_path = tmp_path / "workflow_node_mapping.yaml"
    mapping_path.write_text(yaml.safe_dump({
        "workflows": {
            "txt2img_keyframe_anime": {
                "file": str(workflow_path).replace("\\", "/"),
                "nodes": {
                    "seed": [
                        {"node_id": "30", "input_name": "noise_seed"},
                        {"node_id": "35", "input_name": "noise_seed"},
                    ],
                    "first_pass_cfg": {"node_id": "30", "input_name": "cfg"},
                    "second_pass_cfg": {"node_id": "35", "input_name": "cfg"},
                },
            }
        }
    }, sort_keys=False, allow_unicode=True), encoding="utf-8")
    mapping_data, _ = workflow_mapping.load_workflow_mapping(mapping_path)
    workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "txt2img_keyframe_anime")
    updated = workflow_mapping.apply_node_inputs(workflow, entry["nodes"], {
        "seed": 987654,
        "first_pass_cfg": 1.1,
        "second_pass_cfg": 1.2,
    })
    assert updated["30"]["inputs"]["noise_seed"] == 987654
    assert updated["35"]["inputs"]["noise_seed"] == 987654
    assert updated["30"]["inputs"]["cfg"] == 1.1
    assert updated["35"]["inputs"]["cfg"] == 1.2


def test_repo_route_specific_mapping_entries_use_distinct_workflow_files() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    anime_jp = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_anime_jp")
    direct_anime_cn = workflow_mapping.get_workflow_mapping(mapping_data, "txt2img_keyframe_anime_cn_newguofeng")
    direct_guofeng = workflow_mapping.get_workflow_mapping(mapping_data, "txt2img_keyframe_guofeng_ink")
    direct_stylized = workflow_mapping.get_workflow_mapping(mapping_data, "txt2img_keyframe_stylized_concept")
    anime_cn = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_anime_cn_newguofeng")
    western_cartoon = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_western_cartoon")
    guofeng = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_guofeng_ink")
    stylized = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_stylized_concept")
    realistic_bridge = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_realistic_cinematic_zimage_photo_bridge")
    realistic_original = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_realistic_cinematic_amazing_z_photo_original")
    realistic_reference = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_realistic_cinematic_qwen_edit_reference")
    realistic_dual_reference = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_realistic_cinematic_qwen_edit_dual_reference")
    shortdrama_reference = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_shortdrama_realistic_qwen_edit_reference")
    shortdrama_dual_reference = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_shortdrama_realistic_qwen_edit_dual_reference")
    stylized_bridge = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_stylized_concept_zimage_image_b_bridge")
    game_cg = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_game_cg")
    assert direct_anime_cn["file"].endswith("txt2img_keyframe_anime_cn_newguofeng.workflow_api.json")
    assert direct_guofeng["file"].endswith("txt2img_keyframe_guofeng_ink.workflow_api.json")
    assert direct_stylized["file"].endswith("txt2img_keyframe_stylized_concept.workflow_api.json")
    assert anime_jp["file"].endswith("user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json")
    assert anime_cn["file"].endswith("txt2img_keyframe_anime_cn_newguofeng.workflow_api.json")
    assert western_cartoon["file"].endswith("user/default/workflows/Zimage/amazing-z-comics_SAFETENSORS.json")
    assert guofeng["file"].endswith("txt2img_keyframe_guofeng_ink.workflow_api.json")
    assert stylized["file"].endswith("txt2img_keyframe_stylized_zimage_image_b_bridge.workflow_api.json")
    assert realistic_bridge["file"].endswith("txt2img_keyframe_realistic_zimage_photo_bridge.workflow_api.json")
    assert realistic_original["file"].endswith("user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json")
    assert realistic_reference["file"].endswith("txt2img_keyframe_shortdrama_qwen_edit_reference.workflow_api.json")
    assert realistic_dual_reference["file"].endswith("txt2img_keyframe_shortdrama_qwen_edit_dual_reference.workflow_api.json")
    assert shortdrama_reference["file"].endswith("txt2img_keyframe_shortdrama_qwen_edit_reference.workflow_api.json")
    assert shortdrama_dual_reference["file"].endswith("txt2img_keyframe_shortdrama_qwen_edit_dual_reference.workflow_api.json")
    assert stylized_bridge["file"].endswith("txt2img_keyframe_stylized_zimage_image_b_bridge.workflow_api.json")
    assert game_cg["file"].endswith("txt2img_keyframe_game_cg_clean_plate.workflow_api.json")


def test_repo_route_specific_workflows_expose_required_nodes() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    for workflow_name in [
        "txt2img_keyframe_anime_cn_newguofeng",
        "txt2img_keyframe_guofeng_ink",
        "txt2img_keyframe_stylized_concept",
        "stage05_realistic_cinematic_zimage_photo_bridge",
        "stage05_shortdrama_realistic_qwen_edit_reference",
        "stage05_realistic_cinematic_qwen_edit_dual_reference",
        "stage05_shortdrama_realistic_qwen_edit_dual_reference",
        "stage05_anime_cn_newguofeng",
        "stage05_guofeng_ink",
        "stage05_stylized_concept",
        "stage05_stylized_concept_zimage_image_b_bridge",
        "stage05_game_cg",
    ]:
        workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, workflow_name)
        updated = workflow_mapping.apply_node_inputs(workflow, entry["nodes"], {
            "positive_prompt": "hero frame",
            "negative_prompt": "bad frame",
            "seed": 123,
            "width": 896,
            "height": 1536,
        })
        positive_node_id = entry["nodes"]["positive_prompt"]["node_id"]
        negative_node_id = entry["nodes"]["negative_prompt"]["node_id"]
        seed_node_id = entry["nodes"]["seed"]["node_id"]
        width_node_id = entry["nodes"]["width"]["node_id"]
        height_node_id = entry["nodes"]["height"]["node_id"]
        assert updated[positive_node_id]["inputs"][entry["nodes"]["positive_prompt"]["input_name"]] == "hero frame"
        assert updated[negative_node_id]["inputs"][entry["nodes"]["negative_prompt"]["input_name"]] == "bad frame"
        assert updated[seed_node_id]["inputs"][entry["nodes"]["seed"]["input_name"]] == 123
        assert updated[width_node_id]["inputs"][entry["nodes"]["width"]["input_name"]] == 896
        assert updated[height_node_id]["inputs"][entry["nodes"]["height"]["input_name"]] == 1536


def test_ui_graph_mapping_applies_original_amazing_z_control_points(tmp_path: Path) -> None:
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    mapping_data, _ = workflow_mapping.load_workflow_mapping(mapping_path)
    workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "stage05_realistic_cinematic_amazing_z_photo_original")
    assert comfyui_ui_workflow.resolve_workflow_format(entry) == "ui_graph"
    updated = comfyui_ui_workflow.apply_ui_node_inputs(
        workflow,
        entry["nodes"],
        {
            "positive_prompt": "single woman walking along the shoreline at sunset",
            "style_selector": "classic_film_photo",
            "seed": 2468,
            "short_side": 960,
            "long_side": 1664,
            "output_prefix": "Stage05/IMG_S001_START",
        },
    )
    nodes_by_id = {str(node["id"]): node for node in updated["nodes"]}
    assert nodes_by_id["57"]["widgets_values"][0] == "single woman walking along the shoreline at sunset"
    assert nodes_by_id["90"]["mode"] == 2
    assert nodes_by_id["38"]["mode"] == 2
    assert nodes_by_id["92"]["mode"] == 0
    assert nodes_by_id["459"]["mode"] == 2
    assert nodes_by_id["307"]["widgets_values"][0] == 2468
    assert nodes_by_id["243"]["widgets_values"][0] == 960
    assert nodes_by_id["248"]["widgets_values"][0] == 1664
    assert nodes_by_id["9"]["widgets_values"][0] == "Stage05/IMG_S001_START"


def test_repo_shortdrama_reference_bridge_accepts_reference_image_path() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "stage05_shortdrama_realistic_qwen_edit_reference")
    assert workflow["5"]["inputs"]["clip_name"] == "Qwen2.5\\qwen_2.5_vl_7b_fp8_scaled.safetensors"
    updated = workflow_mapping.apply_node_inputs(workflow, entry["nodes"], {
        "positive_prompt": "same heroine in a rainy convenience-store doorway",
        "negative_prompt": "identity drift, extra limbs",
        "reference_image_path": "IMG_S001_START_ref_primary_character.png",
        "seed": 456,
        "width": 896,
        "height": 1536,
    })
    assert updated["10"]["inputs"]["image"] == "IMG_S001_START_ref_primary_character.png"
    assert updated["22"]["inputs"]["prompt"] == "same heroine in a rainy convenience-store doorway"
    assert updated["23"]["inputs"]["prompt"] == "identity drift, extra limbs"


def test_repo_shortdrama_dual_reference_bridge_accepts_secondary_reference_image_path() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "stage05_realistic_cinematic_qwen_edit_dual_reference")
    updated = workflow_mapping.apply_node_inputs(workflow, entry["nodes"], {
        "positive_prompt": "real umbrella handoff in rainy convenience-store doorway",
        "negative_prompt": "extra hands, duplicated umbrella",
        "reference_image_path": "IMG_S001_ref_primary.png",
        "reference_image_path_2": "IMG_S001_ref_context.png",
        "seed": 789,
        "width": 896,
        "height": 1536,
    })
    assert updated["10"]["inputs"]["image"] == "IMG_S001_ref_primary.png"
    assert updated["11"]["inputs"]["image"] == "IMG_S001_ref_context.png"
    assert updated["22"]["inputs"]["image2"] == ["11", 0]
    assert updated["23"]["inputs"]["image2"] == ["11", 0]


def test_repo_stylized_bridge_exposes_style_anchor_nodes() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "stage05_stylized_concept")
    updated = workflow_mapping.apply_node_inputs(workflow, entry["nodes"], {
        "positive_prompt": "hero frame",
        "style_anchor": "cyberpunk preset anchor",
        "negative_prompt": "bad frame",
        "negative_style_anchor": "anti-cyberpunk preset anchor",
        "seed": 123,
        "width": 896,
        "height": 1536,
    })
    assert updated["11"]["inputs"]["text"] == "cyberpunk preset anchor"
    assert updated["14"]["inputs"]["text"] == "anti-cyberpunk preset anchor"
    game_cg_workflow, game_cg_entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "stage05_game_cg")
    game_cg_updated = workflow_mapping.apply_node_inputs(game_cg_workflow, game_cg_entry["nodes"], {
        "positive_prompt": "hero frame",
        "style_anchor": "heroic splash anchor",
        "negative_prompt": "bad frame",
        "negative_style_anchor": "anti-splash anchor",
        "seed": 321,
        "width": 1024,
        "height": 1536,
    })
    assert game_cg_updated["11"]["inputs"]["text"] == "heroic splash anchor"
    assert game_cg_updated["14"]["inputs"]["text"] == "anti-splash anchor"


def test_repo_guofeng_ink_workflow_exposes_style_anchor_nodes() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, "stage05_guofeng_ink")
    updated = workflow_mapping.apply_node_inputs(workflow, entry["nodes"], {
        "positive_prompt": "ink hero frame",
        "style_anchor": "poetic ink wash anchor",
        "negative_prompt": "bad frame",
        "negative_style_anchor": "anti-modern fashion anchor",
        "seed": 222,
        "width": 1024,
        "height": 1024,
    })
    assert updated["11"]["inputs"]["text"] == "poetic ink wash anchor"
    assert updated["14"]["inputs"]["text"] == "anti-modern fashion anchor"


def test_build_stage05_zimage_photo_bridge_generates_api_workflow(tmp_path: Path) -> None:
    source = tmp_path / "amazing-z-photo_SAFETENSORS.json"
    source.write_text(json.dumps({
        "nodes": [
            {"id": 38, "type": "PrimitiveStringMultiline", "widgets_values": [
                "YOUR CONTEXT:\nYou are a Hollywood filmmaker making a high-budget film.\n"
                "Your photographs exhibit {$spicy-content-with} atmospheric composition and premium studio lighting.\n"
                "YOUR PHOTO:\n{$@}"
            ]},
            {"id": 56, "type": "EmptyLatentImage", "widgets_values": [944, 1408, 1]},
            {"id": 50, "type": "KSamplerAdvanced", "widgets_values": ["enable", 2, "fixed", 8, 1, "euler", "simple", 0, 10000, "disable"]},
            {"id": 572, "type": "UNETLoader", "widgets_values": ["z_image_turbo_bf16.safetensors", "default"]},
            {"id": 573, "type": "CLIPLoader", "widgets_values": ["qwen_3_4b.safetensors", "lumina2", "default"]},
            {"id": 574, "type": "VAELoader", "widgets_values": ["ae.safetensors"]},
        ]
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "bridge.workflow_api.json"
    assert build_stage05_zimage_photo_bridge.main([str(source), str(output)]) == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["1"]["inputs"]["unet_name"] == "Zimage\\z_image_turbo_bf16.safetensors"
    assert data["2"]["inputs"]["clip_name"] == "Zimage\\qwen_3_4b.safetensors"
    assert data["3"]["inputs"]["vae_name"] == "Zimage\\ae.safetensors"
    assert data["2"]["inputs"]["type"] == "lumina2"
    assert data["20"]["inputs"]["width"] == 944
    assert data["20"]["inputs"]["height"] == 1408
    assert data["30"]["inputs"]["steps"] == 8
    assert "Hollywood filmmaker making a high-budget film" in data["11"]["inputs"]["text"]


def test_build_stage05_zimage_image_b_bridge_generates_api_workflow(tmp_path: Path) -> None:
    source = tmp_path / "amazing-z-image-b_SAFETENSORS.json"
    source.write_text(json.dumps({
        "nodes": [
            {"id": 92, "type": "PrimitiveStringMultiline", "widgets_values": [
                "YOUR CONTEXT:\nYou are a digital artist.\n"
                "Your image is a masterpiece featuring {$spicy-content-with} heavy chromatic aberration, and digital intense color.\n"
                "YOUR IMAGE:\n{$@}"
            ]},
            {"id": 56, "type": "EmptyLatentImage", "widgets_values": [944, 1408, 1]},
            {"id": 50, "type": "KSamplerAdvanced", "widgets_values": ["enable", 2, "fixed", 8, 1, "euler", "simple", 0, 10000, "disable"]},
            {"id": 572, "type": "UNETLoader", "widgets_values": ["z_image_turbo_bf16.safetensors", "default"]},
            {"id": 573, "type": "CLIPLoader", "widgets_values": ["qwen_3_4b.safetensors", "lumina2", "default"]},
            {"id": 574, "type": "VAELoader", "widgets_values": ["ae.safetensors"]},
        ]
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "bridge.workflow_api.json"
    assert build_stage05_zimage_image_b_bridge.main([str(source), str(output)]) == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["1"]["inputs"]["unet_name"] == "Zimage\\z_image_turbo_bf16.safetensors"
    assert data["2"]["inputs"]["clip_name"] == "Zimage\\qwen_3_4b.safetensors"
    assert data["3"]["inputs"]["vae_name"] == "Zimage\\ae.safetensors"
    assert data["2"]["inputs"]["type"] == "lumina2"
    assert data["20"]["inputs"]["width"] == 944
    assert data["20"]["inputs"]["height"] == 1408
    assert data["30"]["inputs"]["steps"] == 8
    assert "heavy chromatic aberration" in data["11"]["inputs"]["text"]


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


def test_resolve_stage05_route_prefers_registry_for_known_stage00_style() -> None:
    brief = {"normalized": {"style": "国风水墨/古风", "genre": "治愈"}}
    prompts = {"shot_prompts": [{"style_prompt": "modern anime character key art"}]}
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "guofeng_ink"
    assert resolved["style_family"] == "guofeng"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_guofeng_ink"
    assert resolved["comfyui_workflow_name"] == "txt2img_keyframe_guofeng_ink"
    assert resolved["comfyui_model_id"] == "valiantcat/Qwen-Image-Gufeng-LoRA"
    assert resolved["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_guofeng_ink"
    assert resolved["preferred_comfyui_model_candidate"] == "valiantcat/Qwen-Image-Gufeng-LoRA"
    assert resolved["route_migration_state"] == "research_gap"
    assert resolved["comfyui_style_preset_key"] == "elegant_single_subject_umbrella"
    assert resolved["comfyui_style_preset_label"] == "Elegant Single Subject Umbrella"
    assert "exactly two arms and two hands" in resolved["comfyui_style_positive_anchor"]
    assert "one oil-paper umbrella only in the full frame" in resolved["comfyui_style_positive_anchor"]


def test_resolve_stage05_route_prefers_registry_for_stylized_concept_style() -> None:
    brief = {"normalized": {"style": "赛博朋克", "genre": "悬疑"}}
    prompts = {"shot_prompts": [{"style_prompt": "stylized concept art, neon silhouette, bold color blocking"}]}
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "stylized_concept"
    assert resolved["style_family"] == "stylized"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_stylized_concept"
    assert resolved["comfyui_workflow_name"] == "txt2img_keyframe_stylized_zimage_image_b_bridge"
    assert resolved["comfyui_model_id"] == "Tongyi-MAI/Z-Image"
    assert resolved["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_stylized_zimage_image_b_bridge"
    assert resolved["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image"
    assert resolved["route_migration_state"] == "repo_transitional"
    assert resolved["comfyui_style_preset_key"] == "cyberpunk_neon"
    assert resolved["comfyui_style_preset_label"] == "Cyberpunk Neon"
    assert "heavy chromatic aberration" in resolved["comfyui_style_positive_anchor"]
    assert "washed-out neon" in resolved["comfyui_style_negative_anchor"]


def test_resolve_stage05_route_falls_back_for_unknown_custom_style() -> None:
    brief = {"normalized": {"style": "超现实拼贴实验风", "genre": "治愈"}}
    prompts = {"shot_prompts": [{"style_prompt": "stylized concept art, bold shape design"}]}
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is False
    assert resolved["resolution_mode"] == "legacy_style_family_fallback"
    assert resolved["route_key"] == "stylized"
    assert resolved["style_family"] == "stylized"
    assert resolved["comfyui_workflow_name"] == "txt2img_keyframe_stylized"


def test_resolve_stage05_route_prefers_registry_for_game_cg_style() -> None:
    brief = {"normalized": {"style": "游戏CG感", "genre": "热血"}}
    prompts = {"shot_prompts": [{"style_prompt": "hero splash art, armor detail, dramatic perspective"}]}
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "game_cg"
    assert resolved["style_family"] == "stylized"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_game_cg"
    assert resolved["comfyui_workflow_name"] == "txt2img_keyframe_game_cg_clean_plate"
    assert resolved["comfyui_model_id"] == "Tongyi-MAI/Z-Image"
    assert resolved["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_game_cg_clean_plate"
    assert resolved["comfyui_style_preset_key"] == "heroic_splash_art"
    assert resolved["comfyui_style_preset_label"] == "Heroic Splash Art"
    assert "premium character-action illustration plate" in resolved["comfyui_style_positive_anchor"]
    assert "no integrated title treatment" in resolved["comfyui_style_positive_anchor"]
    assert "visible title text" in resolved["comfyui_style_negative_anchor"]


def test_workflow_replacements_for_job_includes_optional_style_anchors_when_supported() -> None:
    replacements = run_comfyui_txt2img.workflow_replacements_for_job(
        {
            "prompt": "hero frame",
            "negative_prompt": "bad frame",
            "style_prompt": "stylized concept art",
            "camera_prompt": "wide shot",
            "consistency_prompt": "same character",
            "comfyui_style_positive_anchor": "preset-positive",
            "comfyui_style_negative_anchor": "preset-negative",
        },
        {
            "positive_prompt": {"node_id": "10", "input_name": "text"},
            "negative_prompt": {"node_id": "13", "input_name": "text"},
            "style_anchor": {"node_id": "11", "input_name": "text"},
            "negative_style_anchor": {"node_id": "14", "input_name": "text"},
            "seed": {"node_id": "30", "input_name": "seed"},
            "steps": {"node_id": "30", "input_name": "steps"},
            "cfg": {"node_id": "30", "input_name": "cfg"},
            "width": {"node_id": "20", "input_name": "width"},
            "height": {"node_id": "20", "input_name": "height"},
        },
        width=1024,
        height=1536,
        seed=42,
        optimization={
            "workflow_replacements": {
                "steps": 8,
                "cfg": 1.0,
            }
        },
    )
    assert replacements["style_anchor"] == "preset-positive"
    assert replacements["negative_style_anchor"] == "preset-negative"
    assert "text" in replacements["negative_prompt"]
    assert "logo" in replacements["negative_prompt"]
    assert replacements["seed"] == 42
    assert replacements["steps"] == 8
    assert replacements["cfg"] == 1.0


def test_build_provider_prompt_adds_prop_guardrails_for_umbrella_scenes() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "ancient Chinese woman holding an oil-paper umbrella in a misty corridor",
        "style_prompt": "guofeng ink wash illustration",
        "consistency_prompt": "same woman, same umbrella",
        "camera_prompt": "medium-wide scenic frame",
        "negative_prompt": "low resolution, watermark",
    })
    assert "exactly two arms and two hands" in prompt
    assert "umbrella held by one believable visible hand" in prompt
    assert "floating umbrella" in prompt
    assert "one umbrella only in the entire frame" in prompt
    assert "second umbrella" in prompt
    assert "text" in prompt
    assert "logo" in prompt


def test_build_provider_prompt_adds_realistic_establishing_guardrails() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "single woman walking along the shoreline at sunset",
        "style_prompt": "realistic cinematic still",
        "consistency_prompt": "same woman, same beach, same dress",
        "camera_prompt": "wide shot",
        "negative_prompt": "low resolution",
        "stage05_route_key": "realistic_cinematic",
        "reference_guidance_override_reason": "prompt_only_establishing_shot_guardrail",
    })
    assert "true environmental establishing shot" in prompt
    assert "not a behind-the-scenes production still" in prompt
    assert "film set" in prompt
    assert "camera rig" in prompt


def test_build_provider_prompt_adds_guofeng_scenic_guardrails() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "ancient Chinese woman holding one oil-paper umbrella in misty rain",
        "style_prompt": "guofeng ink wash illustration",
        "consistency_prompt": "same woman, same umbrella, same hanfu",
        "camera_prompt": "medium scenic shot",
        "negative_prompt": "low resolution",
        "stage05_route_key": "guofeng_ink",
    })
    assert "medium scenic guofeng frame" in prompt
    assert "visible rain atmosphere" in prompt
    assert "not a face-dominant beauty portrait" in prompt
    assert "cropped umbrella canopy" in prompt


def test_build_provider_prompt_adds_clean_artwork_guardrails_for_game_cg() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "heroic rider crossing a plateau, game key art",
        "style_prompt": "premium fantasy action illustration",
        "consistency_prompt": "same rider, same horse, same armor",
        "camera_prompt": "wide action shot",
        "negative_prompt": "low resolution",
        "stage05_route_key": "game_cg",
    })
    assert "clean full-bleed artwork only" in prompt
    assert "no footer title plaque" in prompt
    assert "artwork-only image content" in prompt
    assert "wordmark" in prompt
    assert "title card" in prompt


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
    assert manifest["stage05_route_key"] == "realistic_cinematic"
    assert manifest["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only"
    assert manifest["comfyui_model_id"] == "Qwen/Qwen-Image-2512"
    assert manifest["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic"
    assert manifest["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Image-2512"
    assert manifest["route_migration_state"] == "official_fallback_for_semantic_alignment"
    assert manifest["preferred_comfyui_workflow_source_ref"] == "workflows/comfyui/txt2img_keyframe_realistic.workflow_api.json"
    assert manifest["preferred_comfyui_workflow_format"] == "api_workflow"
    assert manifest["preferred_comfyui_workflow_custom_node_dependencies"] == []
    assert manifest["preferred_comfyui_workflow_import_blockers"] == []
    assert manifest["comfyui_optimization_profile"] == "balanced"
    assert manifest["comfyui_optimization_profile_label"] == "Balanced"
    assert manifest["comfyui_optimization"]["profile_key"] == "balanced"
    assert manifest["comfyui_optimization"]["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only"
    assert manifest["route_resolution"]["used_registry"] is True
    assert manifest["comfyui_workflow_router"]["realistic"] == "txt2img_keyframe_realistic"
    assert all(job["style_family"] == "realistic" for job in manifest["jobs"])
    assert all(job["stage05_route_key"] == "realistic_cinematic" for job in manifest["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only" for job in manifest["jobs"])
    assert all(job["comfyui_workflow_name"] == "txt2img_keyframe_realistic" for job in manifest["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic" for job in manifest["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Image-2512" for job in manifest["jobs"])
    assert all(job["route_migration_state"] == "official_fallback_for_semantic_alignment" for job in manifest["jobs"])
    assert all(job["preferred_comfyui_workflow_format"] == "api_workflow" for job in manifest["jobs"])
    assert all(job["comfyui_optimization_profile"] == "balanced" for job in manifest["jobs"])
    assert all(job["comfyui_optimization_profile_label"] == "Balanced" for job in manifest["jobs"])
    request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["workflow_name"] == "auto_style_family"
    assert request_manifest["workflow_selection_mode"] == "stage05_route_registry"
    assert request_manifest["stage05_route_key"] == "realistic_cinematic"
    assert request_manifest["route_resolution_mode"] == "stage00_style_registry"
    assert request_manifest["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only"
    assert request_manifest["workflow_mapping_keys"] == ["stage05_realistic_cinematic_qwen2512_prompt_only"]
    assert request_manifest["comfyui_model_id"] == "Qwen/Qwen-Image-2512"
    assert request_manifest["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic"
    assert request_manifest["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Image-2512"
    assert request_manifest["route_migration_state"] == "official_fallback_for_semantic_alignment"
    assert request_manifest["preferred_comfyui_workflow_source_ref"] == "workflows/comfyui/txt2img_keyframe_realistic.workflow_api.json"
    assert request_manifest["preferred_comfyui_workflow_format"] == "api_workflow"
    assert request_manifest["preferred_comfyui_workflow_custom_node_dependencies"] == []
    assert request_manifest["preferred_comfyui_workflow_import_blockers"] == []
    assert request_manifest["optimization_profile"] == "balanced"
    assert request_manifest["optimization_profile_label"] == "Balanced"
    assert request_manifest["workflow_path"] == str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")
    assert request_manifest["workflow_paths"] == [str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")]
    assert len(request_manifest["requests"]) == 2
    assert all(item["status"] == "planned" for item in request_manifest["requests"])
    assert all(item["stage05_route_key"] == "realistic_cinematic" for item in request_manifest["requests"])
    assert all(item["style_family"] == "realistic" for item in request_manifest["requests"])
    assert all(item["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only" for item in request_manifest["requests"])
    assert all(item["comfyui_model_id"] == "Qwen/Qwen-Image-2512" for item in request_manifest["requests"])
    assert all(item["workflow_name"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
    assert all(item["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
    assert all(item["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Image-2512" for item in request_manifest["requests"])
    assert all(item["route_migration_state"] == "official_fallback_for_semantic_alignment" for item in request_manifest["requests"])
    assert all(item["preferred_comfyui_workflow_format"] == "api_workflow" for item in request_manifest["requests"])
    assert all(item["comfyui_optimization_profile"] == "balanced" for item in request_manifest["requests"])
    assert all(item["comfyui_optimization_profile_label"] == "Balanced" for item in request_manifest["requests"])
    assert all(item["width"] == 896 for item in request_manifest["requests"])
    assert all(item["height"] == 1344 for item in request_manifest["requests"])
    assert not any((manifest_json.parent / "keyframes").glob("*.png"))


def test_run_comfyui_txt2img_ui_graph_route_converts_original_workflow(monkeypatch, tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    for job in manifest["jobs"]:
        job["comfyui_style_selector"] = "production_photo"
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    captured_workflows: list[dict] = []

    def _fake_convert(workflow: dict, *, base_url: str, script_path=None, node_modules_dir=None) -> dict:
        captured_workflows.append(workflow)
        return {
            "prompt": {
                "9": {
                    "inputs": {
                        "filename_prefix": "Stage05/IMG_S001_START",
                    },
                    "class_type": "SaveImage",
                }
            },
            "extra_data": {
                "extra_pnginfo": {
                    "workflow": workflow,
                }
            },
        }

    monkeypatch.setattr(run_comfyui_txt2img.comfyui_ui_workflow, "convert_ui_workflow_to_prompt", _fake_convert)

    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_txt2img.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--workflow-name", "stage05_realistic_cinematic_amazing_z_photo_original",
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert len(captured_workflows) == 2
    first_nodes = {str(node["id"]): node for node in captured_workflows[0]["nodes"]}
    second_nodes = {str(node["id"]): node for node in captured_workflows[1]["nodes"]}
    assert "落日海滩" in first_nodes["57"]["widgets_values"][0]
    assert "continuation of S001" in second_nodes["57"]["widgets_values"][0]
    assert first_nodes["90"]["mode"] == 2
    assert first_nodes["38"]["mode"] == 0
    assert first_nodes["92"]["mode"] == 2
    assert second_nodes["90"]["mode"] == 2
    assert second_nodes["38"]["mode"] == 0
    assert second_nodes["92"]["mode"] == 2
    assert first_nodes["243"]["widgets_values"][0] == 896
    assert first_nodes["248"]["widgets_values"][0] == 1344
    assert second_nodes["243"]["widgets_values"][0] == 896
    assert second_nodes["248"]["widgets_values"][0] == 1344
    assert first_nodes["9"]["widgets_values"][0] == "Stage05/IMG_S001_START"
    assert second_nodes["9"]["widgets_values"][0] == "Stage05/IMG_S001_END"
    submitted_payload = _FakeComfyTxt2ImgHandler.requests[0]
    assert "extra_data" in submitted_payload
    request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert request_manifest["workflow_path"].endswith("stage05_realistic_cinematic_amazing_z_photo_original.workflow_api.json")


def test_run_comfyui_txt2img_reference_guided_route_stages_reference_image(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    project_dir = manifest_json.parents[1]
    reference_dir = project_dir / "03_characters" / "reference_images"
    reference_dir.mkdir(parents=True, exist_ok=True)
    reference_path = reference_dir / "CHAR_001_primary.png"
    reference_path.write_bytes(b"PNGDATA")

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    manifest["stage05_route_key"] = "shortdrama_realistic"
    manifest["comfyui_workflow_mapping_key"] = "stage05_shortdrama_realistic_qwen_edit_reference"
    manifest["comfyui_workflow_name"] = "txt2img_keyframe_shortdrama_qwen_edit_reference"
    manifest["comfyui_control_mode"] = "reference_guided"
    manifest["reference_guidance_requested"] = True
    manifest["reference_guidance_ready"] = True
    manifest["reference_guidance_active"] = True
    manifest["reference_image_status"] = {
        "required": True,
        "all_present": True,
        "existing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "missing_paths": [],
    }
    for job in manifest["jobs"]:
        job["stage05_route_key"] = "shortdrama_realistic"
        job["comfyui_workflow_mapping_key"] = "stage05_shortdrama_realistic_qwen_edit_reference"
        job["comfyui_workflow_name"] = "txt2img_keyframe_shortdrama_qwen_edit_reference"
        job["comfyui_control_mode"] = "reference_guided"
        job["reference_guidance_requested"] = True
        job["reference_guidance_ready"] = True
        job["reference_guidance_active"] = True
        job["reference_images"] = ["03_characters/reference_images/CHAR_001_primary.png"]
        job["missing_reference_images"] = []
        gate = dict(job.get("quality_gate") or {})
        gate["risk_tags"] = []
        gate["requires_manual_review"] = False
        gate["manual_review_status"] = "not_required"
        gate["control_mode"] = "reference_guided"
        job["quality_gate"] = gate
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    output_root = tmp_path / "comfy_output"
    input_root = tmp_path / "comfy_input"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_address[1]}",
            output_root=output_root,
            input_root=input_root,
        )
        assert run_comfyui_txt2img.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--workflow-name", "stage05_shortdrama_realistic_qwen_edit_reference",
        ]) == 0
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert _FakeComfyTxt2ImgHandler.requests
    submitted_prompt = _FakeComfyTxt2ImgHandler.requests[0]["prompt"]
    staged_name = submitted_prompt["10"]["inputs"]["image"]
    assert staged_name.startswith("IMG_S001_START_ref_primary_")
    staged_path = input_root / staged_name
    assert staged_path.exists()
    request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    staged_records = request_manifest["requests"][0]["staged_reference_images"]
    assert staged_records[0]["source_path"] == "03_characters/reference_images/CHAR_001_primary.png"
    assert staged_records[0]["staged_name"] == staged_name


def test_run_comfyui_txt2img_dual_reference_route_stages_secondary_reference_image(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    project_dir = manifest_json.parents[1]
    reference_dir = project_dir / "03_characters" / "reference_images"
    reference_dir.mkdir(parents=True, exist_ok=True)
    primary_reference = reference_dir / "CHAR_001_primary.png"
    primary_reference.write_bytes(b"PRIMARY")
    context_reference = project_dir / "05_images" / "keyframes" / "S001_end.png"
    context_reference.parent.mkdir(parents=True, exist_ok=True)
    context_reference.write_bytes(b"CONTEXT")

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    manifest["stage05_route_key"] = "realistic_cinematic"
    manifest["comfyui_workflow_mapping_key"] = "stage05_realistic_cinematic_qwen_edit_dual_reference"
    manifest["comfyui_workflow_name"] = "txt2img_keyframe_shortdrama_qwen_edit_dual_reference"
    manifest["comfyui_control_mode"] = "reference_guided"
    manifest["reference_guidance_requested"] = True
    manifest["reference_guidance_ready"] = True
    manifest["reference_guidance_active"] = True
    for job in manifest["jobs"]:
        job["stage05_route_key"] = "realistic_cinematic"
        job["comfyui_workflow_mapping_key"] = "stage05_realistic_cinematic_qwen_edit_dual_reference"
        job["comfyui_workflow_name"] = "txt2img_keyframe_shortdrama_qwen_edit_dual_reference"
        job["comfyui_control_mode"] = "reference_guided"
        job["reference_guidance_requested"] = True
        job["reference_guidance_ready"] = True
        job["reference_guidance_active"] = True
        job["reference_images"] = [
            "03_characters/reference_images/CHAR_001_primary.png",
            "05_images/keyframes/S001_end.png",
        ]
        job["missing_reference_images"] = []
        gate = dict(job.get("quality_gate") or {})
        gate["risk_tags"] = []
        gate["requires_manual_review"] = False
        gate["manual_review_status"] = "not_required"
        gate["control_mode"] = "reference_guided"
        job["quality_gate"] = gate
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    output_root = tmp_path / "comfy_output"
    input_root = tmp_path / "comfy_input"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(
            tmp_path,
            base_url=f"http://127.0.0.1:{server.server_address[1]}",
            output_root=output_root,
            input_root=input_root,
        )
        assert run_comfyui_txt2img.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--workflow-name", "stage05_realistic_cinematic_qwen_edit_dual_reference",
        ]) == 0
    finally:
        server.shutdown()
        thread.join(timeout=5)

    submitted_prompt = _FakeComfyTxt2ImgHandler.requests[0]["prompt"]
    primary_staged_name = submitted_prompt["10"]["inputs"]["image"]
    secondary_staged_name = submitted_prompt["11"]["inputs"]["image"]
    assert primary_staged_name.startswith("IMG_S001_START_ref_primary_")
    assert secondary_staged_name.startswith("IMG_S001_START_ref_secondary_")
    assert (input_root / primary_staged_name).exists()
    assert (input_root / secondary_staged_name).exists()
    request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    staged_records = request_manifest["requests"][0]["staged_reference_images"]
    assert [item["slot"] for item in staged_records] == ["reference_image_path", "reference_image_path_2"]
    assert staged_records[1]["source_path"] == "05_images/keyframes/S001_end.png"


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
        assert all(
            job["notes"].startswith(
                "route=realistic_cinematic; route_state=official_fallback_for_semantic_alignment; preferred_workflow=txt2img_keyframe_realistic; profile=balanced; size=896x1344; mapping=stage05_realistic_cinematic_qwen2512_prompt_only; workflow=txt2img_keyframe_realistic;"
            )
            for job in data["jobs"]
        )
        request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["workflow_name"] == "auto_style_family"
        assert request_manifest["stage05_route_key"] == "realistic_cinematic"
        assert request_manifest["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only"
        assert request_manifest["optimization_profile"] == "balanced"
        assert request_manifest["optimization_profile_label"] == "Balanced"
        assert request_manifest["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic"
        assert request_manifest["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Image-2512"
        assert request_manifest["route_migration_state"] == "official_fallback_for_semantic_alignment"
        assert request_manifest["preferred_comfyui_workflow_format"] == "api_workflow"
        assert request_manifest["workflow_path"] == str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")
        assert all(item["status"] == "succeeded" for item in request_manifest["requests"])
        assert all(item["stage05_route_key"] == "realistic_cinematic" for item in request_manifest["requests"])
        assert all(item["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only" for item in request_manifest["requests"])
        assert all(item["workflow_name"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
        assert all(item["route_migration_state"] == "official_fallback_for_semantic_alignment" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_format"] == "api_workflow" for item in request_manifest["requests"])
        assert all(item["comfyui_optimization_profile"] == "balanced" for item in request_manifest["requests"])
        workflow_payload = _FakeComfyTxt2ImgHandler.requests[0]["prompt"]
        assert "Avoid:" in workflow_payload["6"]["inputs"]["text"]
        assert workflow_payload["5"]["inputs"]["width"] == 896
        assert workflow_payload["5"]["inputs"]["height"] == 1344
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_txt2img_runs_auto_repair_second_pass_for_risky_prompt(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    risky_job = manifest["jobs"][0]
    risky_job["prompt"] = "realistic woman holding one oil-paper umbrella in rain"
    risky_job["negative_prompt"] = "low resolution"
    risky_job["quality_gate"] = {
        "risk_tags": ["umbrella_prop_contact"],
        "control_mode": "prompt_only",
        "requires_manual_review": True,
        "manual_review_status": "pending",
        "reason": "Umbrella prop-contact scenes remain prompt-only on the current Stage 05 route.",
    }
    manifest["jobs"] = [risky_job]
    manifest["summary"]["expected_image_count"] = 1
    manifest["summary"]["shot_count"] = 1
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    server, thread = _start_server("success", output_root=output_root)
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_txt2img.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--image-id", risky_job["image_id"],
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 0
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        job = data["jobs"][0]
        assert job["auto_repair_status"] == "auto_second_pass_succeeded"
        assert "repair=auto_second_pass_succeeded" in job["notes"]
        assert job["creator_review_card"]["suggestions"]
        assert job["creator_review_card"]["priority_label"] == "高优先级复核"
        assert len(job["creator_review_card"]["checklist"]) == 3
        assert Path(job["repair_preview_path"]).exists()
        manual_review_text = (manifest_json.parent / "manual_review.md").read_text(encoding="utf-8")
        assert "IMG_S001_START" in manual_review_text
        assert "一修前预检" in manual_review_text
        assert "Top 3 快速问题卡" in manual_review_text
        prompt_patch_plan = json.loads((manifest_json.parent / "prompt_patch_plan.json").read_text(encoding="utf-8"))
        assert prompt_patch_plan["patch_count"] == 1
        assert prompt_patch_plan["top_prompt_patches"][0]["negative_prompt_additions"]
        prompt_patch_cards = (manifest_json.parent / "prompt_patch_cards.md").read_text(encoding="utf-8")
        assert "Prompt 补丁" in prompt_patch_cards
        request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["auto_repair_plan"]["enabled"] is True
        assert len(request_manifest["requests"][0]["pass_history"]) == 2
        assert len(_FakeComfyTxt2ImgHandler.requests) == 2
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_txt2img_blocks_missing_character_reference_before_generation(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    _mark_job_missing_character_reference(manifest_json, "IMG_S001_START")
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)

    assert run_comfyui_txt2img.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--image-id", "IMG_S001_START",
    ]) == 1

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    blocked_job = next(job for job in data["jobs"] if job["image_id"] == "IMG_S001_START")
    assert blocked_job["status"] == "blocked"
    assert blocked_job["provider"] == "comfyui_txt2img"
    assert blocked_job["errors"]
    assert "missing a Stage 03 reference image" in blocked_job["notes"]
    assert data["manual_recovery"]["status"] == "required"
    assert data["creator_runtime_status"]["headline"] == "高风险关键帧已阻断，先补角色参考图。"
    assert "CHAR_001_primary.png" in " ".join(data["manual_recovery"]["steps"])
    assert any(
        item["decision"] == "manual_recovery_required"
        and item["reason"] == "missing_character_reference_before_generation"
        for item in data["provider_decisions"]
    )
    request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    blocked_request = next(item for item in request_manifest["requests"] if item["image_id"] == "IMG_S001_START")
    assert blocked_request["status"] == "blocked"
    assert "CHAR_001_primary.png" in " ".join(blocked_request["missing_reference_images"])
    manual_review = (manifest_json.parent / "manual_review.md").read_text(encoding="utf-8")
    assert "当前阻断" in manual_review
    assert "CHAR_001_primary.png" in manual_review


def test_validator_accepts_null_optional_route_metadata_on_successful_manifest(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
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
        data["preferred_comfyui_workflow_format"] = None
        data["preferred_comfyui_workflow_custom_node_dependencies"] = None
        data["preferred_comfyui_workflow_import_blockers"] = None
        for job in data["jobs"]:
            job["preferred_comfyui_workflow_format"] = None
            job["preferred_comfyui_workflow_custom_node_dependencies"] = None
            job["preferred_comfyui_workflow_import_blockers"] = None
        ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
        assert ok, errors
        assert warnings == []
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
        assert request_manifest["stage05_route_key"] == "realistic_cinematic"
        assert request_manifest["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only"
        assert request_manifest["optimization_profile"] == "balanced"
        assert request_manifest["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic"
        assert request_manifest["route_migration_state"] == "official_fallback_for_semantic_alignment"
        assert request_manifest["preferred_comfyui_workflow_format"] == "api_workflow"
        assert request_manifest["workflow_path"] == str(workflow_paths["txt2img_keyframe_realistic"]).replace("\\", "/")
        assert all(item["status"] == "failed" for item in request_manifest["requests"])
        assert all(item["stage05_route_key"] == "realistic_cinematic" for item in request_manifest["requests"])
        assert all(item["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen2512_prompt_only" for item in request_manifest["requests"])
        assert all(item["workflow_name"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic" for item in request_manifest["requests"])
        assert all(item["route_migration_state"] == "official_fallback_for_semantic_alignment" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_format"] == "api_workflow" for item in request_manifest["requests"])
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
