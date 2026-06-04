#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

from PIL import Image
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
sync_keyframe_image_manifest = load_module("sync_keyframe_image_manifest_comfy_test", IMAGES / "sync_keyframe_image_manifest.py")
validate_keyframe_image_manifest = load_module("validate_keyframe_image_manifest_comfy_test", IMAGES / "validate_keyframe_image_manifest.py")
run_comfyui_txt2img = load_module("run_comfyui_txt2img_test", PROVIDERS / "run_comfyui_txt2img.py")
workflow_mapping = load_module("workflow_mapping_test", PROVIDERS / "workflow_mapping.py")
comfyui_ui_workflow = load_module("comfyui_ui_workflow_test", PROVIDERS / "comfyui_ui_workflow.py")


class _FakeComfyTxt2ImgHandler(BaseHTTPRequestHandler):
    mode = "success"
    prompt_id = "prompt-stage05"
    requests: list[dict] = []
    output_root: Path | None = None
    output_size: tuple[int, int] = (896, 1344)

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


def _start_server(
    mode: str,
    *,
    output_root: Path,
    output_size: tuple[int, int] = (896, 1344),
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _FakeComfyTxt2ImgHandler.mode = mode
    _FakeComfyTxt2ImgHandler.requests = []
    _FakeComfyTxt2ImgHandler.output_root = output_root
    _FakeComfyTxt2ImgHandler.output_size = output_size
    out_dir = output_root / "txt2img"
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode != "missing_file":
        Image.new("RGB", output_size, color=(120, 110, 100)).save(out_dir / "comfy_output.png", format="PNG")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeComfyTxt2ImgHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _patch_ui_graph_conversion(monkeypatch) -> None:
    def _fake_convert(workflow: dict, *, base_url: str, script_path=None, node_modules_dir=None) -> dict:
        nodes_by_id = {str(node["id"]): node for node in workflow["nodes"]}
        save_node = nodes_by_id.get("9") or nodes_by_id.get("89")
        assert save_node is not None
        output_prefix = save_node["widgets_values"][0]
        return {
            "prompt": {
                "9": {
                    "inputs": {
                        "filename_prefix": output_prefix,
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


def _write_config(tmp_path: Path, *, base_url: str, output_root: Path, input_root: Path | None = None) -> Path:
    data = yaml.safe_load((ROOT / "config" / "providers.example.yaml").read_text(encoding="utf-8"))
    data["openai_image"]["enabled"] = False
    data["comfyui"]["enabled"] = True
    data["comfyui"]["base_url"] = base_url
    effective_input_root = input_root or (tmp_path / "comfy_input")
    effective_input_root.mkdir(parents=True, exist_ok=True)
    data["comfyui"]["input_dir"] = str(effective_input_root).replace("\\", "/")
    data["comfyui"]["output_dir"] = str(output_root).replace("\\", "/")
    config_path = tmp_path / "providers.yaml"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def _write_test_png(path: Path, *, size: tuple[int, int] = (64, 96), color: tuple[int, int, int] = (128, 120, 112)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path, format="PNG")


def _write_mapping_and_workflow(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    workflow_names = [
        "txt2img_keyframe",
        "txt2img_keyframe_realistic",
        "stage05_realistic_cinematic_amazing_z_photo_original",
        "stage05_realistic_cinematic_qwen_edit_nextscene_local",
        "txt2img_keyframe_anime",
        "txt2img_keyframe_guofeng",
        "txt2img_keyframe_stylized",
    ]
    mapping_alias_to_workflow = {
        "txt2img_keyframe": "txt2img_keyframe",
        "txt2img_keyframe_realistic": "txt2img_keyframe_realistic",
        "txt2img_keyframe_anime": "txt2img_keyframe_anime",
        "txt2img_keyframe_guofeng": "txt2img_keyframe_guofeng",
        "txt2img_keyframe_stylized": "txt2img_keyframe_stylized",
        "stage05_realistic_cinematic_amazing_z_photo_original": "stage05_realistic_cinematic_amazing_z_photo_original",
        "stage05_realistic_cinematic_qwen_edit_nextscene_local": "stage05_realistic_cinematic_qwen_edit_nextscene_local",
        "stage05_anime_jp": "txt2img_keyframe_anime",
        "stage05_western_cartoon": "txt2img_keyframe_anime",
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
        elif workflow_name == "stage05_realistic_cinematic_qwen_edit_nextscene_local":
            workflow_payload = {
                "nodes": [
                    {"id": 13, "type": "LoadImage", "widgets_values": ["reference.png", "image"]},
                    {"id": 123, "type": "easy promptLine", "widgets_values": ["Next Scene：same heroine", 0, 1000, "", ""]},
                    {"id": 10, "type": "KSampler", "widgets_values": [1, "fixed", 4, 1, "euler", "simple", 1]},
                    {
                        "id": 21,
                        "type": "TextEncodeQwenImageEditPlusAdvance_lrzjason",
                        "widgets_values": [
                            "",
                            1024,
                            384,
                            "lanczos",
                            "center",
                            "Describe the key features of the input image (color, shape, size, texture, objects, background), then explain how the user's text instruction should alter or modify the image.",
                        ],
                    },
                    {"id": 89, "type": "SaveImage", "widgets_values": ["Stage05/TEST"]},
                ]
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
        if workflow_name == "stage05_realistic_cinematic_amazing_z_photo_original":
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
                    "width": {"node_id": "243", "control": "widget_value", "widget_index": 0},
                    "height": {"node_id": "248", "control": "widget_value", "widget_index": 0},
                    "output_prefix": {"node_id": "9", "control": "widget_value", "widget_index": 0},
                },
            }
        elif workflow_name == "stage05_realistic_cinematic_qwen_edit_nextscene_local":
            mapping_workflows[mapping_key] = {
                "file": str(workflow_paths[workflow_name]).replace("\\", "/"),
                "workflow_format": "ui_graph",
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["reference_guided"],
                },
                "nodes": {
                    "positive_prompt": {"node_id": "123", "control": "widget_value", "widget_index": 0},
                    "reference_image_path": {"node_id": "13", "control": "widget_value", "widget_index": 0},
                    "seed": {"node_id": "10", "control": "widget_value", "widget_index": 0},
                    "target_size": {"node_id": "21", "control": "widget_value", "widget_index": 1},
                    "target_vl_size": {"node_id": "21", "control": "widget_value", "widget_index": 2},
                    "crop_method": {"node_id": "21", "control": "widget_value", "widget_index": 4},
                    "output_prefix": {"node_id": "89", "control": "widget_value", "widget_index": 0},
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
    reference_dir = project_dir / "03_characters" / "reference_images"
    intake_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)
    reference_dir.mkdir(parents=True)

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
    keyframe["reference_image_status"] = {
        "required": True,
        "target_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "existing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "missing_paths": [],
        "all_present": True,
        "item_count": 1,
        "missing_count": 0,
        "items": [{"character_id": "CHAR_001", "target_path": "03_characters/reference_images/CHAR_001_primary.png", "file_exists": True}],
    }
    keyframe["stage05_execution_readiness"] = {
        "continuity_mode": "character_locked",
        "reference_image_required": True,
        "safe_to_auto_generate": True,
        "blocker_reasons": [],
        "missing_reference_images": [],
    }
    keyframe["self_check"]["character_reference_images_ready"] = True
    keyframe["self_check"]["safe_for_auto_image_generation"] = True
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_test_png(reference_dir / "CHAR_001_primary.png")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0
    return manifest_json


def _prepare_scope_blocked_manifest(tmp_path: Path) -> Path:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_scope_blocked"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    reference_dir = project_dir / "03_characters" / "reference_images"
    intake_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)
    reference_dir.mkdir(parents=True)

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
    keyframe["reference_image_status"] = {
        "required": True,
        "target_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "existing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        "missing_paths": [],
        "all_present": True,
        "item_count": 1,
        "missing_count": 0,
        "items": [{"character_id": "CHAR_001", "target_path": "03_characters/reference_images/CHAR_001_primary.png", "file_exists": True}],
    }
    keyframe["stage05_execution_readiness"] = {
        "continuity_mode": "character_locked",
        "reference_image_required": True,
        "safe_to_auto_generate": True,
        "blocker_reasons": [],
        "missing_reference_images": [],
    }
    keyframe["self_check"]["character_reference_images_ready"] = True
    keyframe["self_check"]["safe_for_auto_image_generation"] = True
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_test_png(reference_dir / "CHAR_001_primary.png")

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


def test_repo_stage05_mapping_entries_are_pinned_to_three_local_zimage_workflows() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    anime_jp = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_anime_jp")
    western_cartoon = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_western_cartoon")
    realistic_original = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_realistic_cinematic_amazing_z_photo_original")

    assert anime_jp["file"].endswith("user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json")
    assert western_cartoon["file"].endswith("user/default/workflows/Zimage/amazing-z-comics_SAFETENSORS.json")
    assert realistic_original["file"].endswith("user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json")

    assert "stage05_anime_cn_newguofeng" not in mapping_data["workflows"]
    assert "stage05_guofeng_ink" not in mapping_data["workflows"]
    assert "stage05_stylized_concept" not in mapping_data["workflows"]
    assert "stage05_game_cg" not in mapping_data["workflows"]
    assert "stage05_shortdrama_realistic_qwen_edit_reference" not in mapping_data["workflows"]
    assert "txt2img_keyframe_shortdrama_qwen_edit_reference" not in mapping_data["workflows"]
    assert "txt2img_keyframe_realistic_zimage_photo_bridge" not in mapping_data["workflows"]


def test_repo_stage05_zimage_workflows_expose_required_nodes() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    for workflow_name in [
        "stage05_anime_jp",
        "stage05_western_cartoon",
        "stage05_realistic_cinematic_amazing_z_photo_original",
    ]:
        workflow, entry, _ = workflow_mapping.load_mapped_workflow(mapping_data, workflow_name)
        updated = comfyui_ui_workflow.apply_ui_node_inputs(workflow, entry["nodes"], {
            "positive_prompt": "hero frame",
            "style_selector": entry["nodes"]["style_selector"]["default_choice"],
            "seed": 123,
            "width": 1536,
            "height": 896,
            "output_prefix": "ZImage/test/out",
        })
        positive_node_id = entry["nodes"]["positive_prompt"]["node_id"]
        seed_node_id = entry["nodes"]["seed"]["node_id"]
        width_node_id = entry["nodes"]["width"]["node_id"]
        height_node_id = entry["nodes"]["height"]["node_id"]
        ui_nodes = comfyui_ui_workflow._ui_nodes(updated)
        assert comfyui_ui_workflow._ensure_widget_values(
            comfyui_ui_workflow._find_ui_node(ui_nodes, positive_node_id, field_name="positive_prompt"),
            field_name="positive_prompt",
        )[entry["nodes"]["positive_prompt"]["widget_index"]] == "hero frame"
        assert comfyui_ui_workflow._ensure_widget_values(
            comfyui_ui_workflow._find_ui_node(ui_nodes, seed_node_id, field_name="seed"),
            field_name="seed",
        )[entry["nodes"]["seed"]["widget_index"]] == 123
        assert comfyui_ui_workflow._ensure_widget_values(
            comfyui_ui_workflow._find_ui_node(ui_nodes, width_node_id, field_name="width"),
            field_name="width",
        )[entry["nodes"]["width"]["widget_index"]] == 1536
        assert comfyui_ui_workflow._ensure_widget_values(
            comfyui_ui_workflow._find_ui_node(ui_nodes, height_node_id, field_name="height"),
            field_name="height",
        )[entry["nodes"]["height"]["widget_index"]] == 896


def test_repo_stage05_deleted_character_anchor_workflow_mapping_is_absent() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    assert "stage05_realistic_cinematic_qwen_edit_character_anchor_local" not in mapping_data["workflows"]


def test_repo_stage05_reference_guided_nextscene_workflow_exposes_required_nodes() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    entry = workflow_mapping.get_workflow_mapping(mapping_data, "stage05_realistic_cinematic_qwen_edit_nextscene_local")
    workflow, _, _ = workflow_mapping.load_mapped_workflow(
        mapping_data,
        "stage05_realistic_cinematic_qwen_edit_nextscene_local",
    )
    assert comfyui_ui_workflow.resolve_workflow_format(entry) == "ui_graph"
    updated = comfyui_ui_workflow.apply_ui_node_inputs(
        workflow,
        entry["nodes"],
        {
            "positive_prompt": "Next Scene：同一位年轻亚洲女性站在黄昏海边，保持同一张脸和同一条浅色长裙，侧身望向海平线，中景，暖金色逆光，情绪克制。",
            "reference_image_path": "IMG_S001_ref_primary.png",
            "seed": 2468,
            "target_size": 1024,
            "target_vl_size": 392,
            "crop_method": "center",
            "output_prefix": "Stage05/IMG_S001_START",
        },
    )
    nodes_by_id = {str(node["id"]): node for node in updated["nodes"]}
    assert nodes_by_id["123"]["widgets_values"][0].startswith("Next Scene：同一位年轻亚洲女性")
    assert nodes_by_id["13"]["widgets_values"][0] == "IMG_S001_ref_primary.png"
    assert nodes_by_id["10"]["widgets_values"][0] == 2468
    assert nodes_by_id["21"]["widgets_values"][1] == 1024
    assert nodes_by_id["21"]["widgets_values"][2] == 392
    assert nodes_by_id["21"]["widgets_values"][4] == "center"
    assert nodes_by_id["89"]["widgets_values"][0] == "Stage05/IMG_S001_START"


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
            "width": 1664,
            "height": 960,
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
    assert nodes_by_id["243"]["widgets_values"][0] == 1664
    assert nodes_by_id["248"]["widgets_values"][0] == 960
    assert nodes_by_id["9"]["widgets_values"][0] == "Stage05/IMG_S001_START"


def test_repo_deleted_stage05_bridge_mappings_are_absent() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.yaml")
    assert "stage05_shortdrama_realistic_qwen_edit_reference" not in mapping_data["workflows"]
    assert "stage05_realistic_cinematic_qwen_edit_dual_reference" not in mapping_data["workflows"]
    assert "stage05_realistic_cinematic_qwen_edit_character_anchor_local" not in mapping_data["workflows"]
    assert "stage05_stylized_concept" not in mapping_data["workflows"]
    assert "stage05_game_cg" not in mapping_data["workflows"]
    assert "stage05_guofeng_ink" not in mapping_data["workflows"]


def test_stage05_example_mapping_is_aligned_to_reference_guided_mainline() -> None:
    mapping_data, _ = workflow_mapping.load_workflow_mapping(ROOT / "config" / "workflow_node_mapping.example.yaml")
    assert "stage05_realistic_cinematic_qwen_edit_nextscene_local" in mapping_data["workflows"]
    assert "stage05_realistic_cinematic" not in mapping_data["workflows"]
    assert "stage05_realistic_cinematic_qwen2512_prompt_only" not in mapping_data["workflows"]
    assert "stage05_realistic_cinematic_qwen_edit_reference" not in mapping_data["workflows"]
    assert "stage05_shortdrama_realistic" not in mapping_data["workflows"]
    assert "stage05_shortdrama_realistic_qwen_edit_reference" not in mapping_data["workflows"]
    assert "stage05_shortdrama_realistic_qwen_edit_dual_reference" not in mapping_data["workflows"]
    assert "stage05_realistic_cinematic_zimage_photo_bridge" not in mapping_data["workflows"]
    assert "stage05_anime_cn_newguofeng" not in mapping_data["workflows"]
    assert "stage05_guofeng_ink" not in mapping_data["workflows"]
    assert "stage05_stylized_concept" not in mapping_data["workflows"]
    assert "stage05_game_cg" not in mapping_data["workflows"]
    assert "txt2img_keyframe_realistic_zimage_photo_bridge" not in mapping_data["workflows"]
    assert "txt2img_keyframe_stylized_zimage_image_b_bridge" not in mapping_data["workflows"]


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
    assert resolved["stage05_mode"] == "reference_guided_storyboard"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert resolved["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert resolved["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert resolved["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert resolved["route_migration_state"] == "stage05b_reference_guided_mainline"
    assert resolved["reference_bootstrap_workflow_mapping_key"] == "stage05_anime_jp"
    assert resolved["reference_bootstrap_workflow_name"] == "amazing_z_image_a_safetensors"
    assert resolved["reference_bootstrap_style_preset_key"] == "elegant_single_subject_umbrella"
    assert resolved["reference_bootstrap_style_preset_label"] == "Elegant Single Subject Umbrella"
    assert "clean limb count" in resolved["reference_bootstrap_style_positive_anchor"]
    assert "duplicated umbrella" in resolved["reference_bootstrap_style_negative_anchor"]


def test_resolve_stage05_route_prefers_registry_for_stylized_concept_style() -> None:
    brief = {"normalized": {"style": "赛博朋克", "genre": "悬疑"}}
    prompts = {"shot_prompts": [{"style_prompt": "stylized concept art, neon silhouette, bold color blocking"}]}
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "stylized_concept"
    assert resolved["style_family"] == "stylized"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert resolved["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert resolved["reference_bootstrap_workflow_mapping_key"] == "stage05_western_cartoon"
    assert resolved["reference_bootstrap_workflow_name"] == "amazing_z_comics_safetensors"
    assert resolved["reference_bootstrap_style_preset_key"] == "cyberpunk_neon"
    assert resolved["reference_bootstrap_style_preset_label"] == "Cyberpunk Neon"
    assert "neon-driven" in resolved["reference_bootstrap_style_positive_anchor"]
    assert "washed-out city realism" in resolved["reference_bootstrap_style_negative_anchor"]


def test_resolve_stage05_route_falls_back_for_unknown_custom_style() -> None:
    brief = {"normalized": {"style": "超现实拼贴实验风", "genre": "治愈"}}
    prompts = {"shot_prompts": [{"style_prompt": "stylized concept art, bold shape design"}]}
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is False
    assert resolved["resolution_mode"] == "heuristic_style_family_bootstrap_fallback_plus_stage05b_mainline"
    assert resolved["route_key"] == "stylized"
    assert resolved["style_family"] == "stylized"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert resolved["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert resolved["reference_bootstrap_workflow_mapping_key"] == "stage05_western_cartoon"


def test_resolve_stage05_route_prefers_registry_for_game_cg_style() -> None:
    brief = {"normalized": {"style": "游戏CG感", "genre": "热血"}}
    prompts = {"shot_prompts": [{"style_prompt": "hero splash art, armor detail, dramatic perspective"}]}
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "game_cg"
    assert resolved["style_family"] == "stylized"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert resolved["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert resolved["reference_bootstrap_workflow_mapping_key"] == "stage05_western_cartoon"
    assert resolved["reference_bootstrap_workflow_name"] == "amazing_z_comics_safetensors"
    assert resolved["reference_bootstrap_style_preset_key"] == "heroic_splash_art"
    assert resolved["reference_bootstrap_style_preset_label"] == "Heroic Splash Art"
    assert "high-impact hero plate" in resolved["reference_bootstrap_style_positive_anchor"]
    assert "weak costume readability" in resolved["reference_bootstrap_style_negative_anchor"]


def test_resolve_stage05_route_switches_realistic_cinematic_to_reference_guided_when_refs_ready() -> None:
    brief = {"normalized": {"style": "写实电影感", "genre": "治愈"}}
    prompts = {
        "reference_image_status": {
            "all_present": True,
        },
        "stage05_execution_readiness": {
            "reference_image_required": True,
        },
        "shot_prompts": [
            {
                "style_prompt": "realistic cinematic still",
            }
        ],
    }
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "realistic_cinematic"
    assert resolved["reference_guided_route_selected"] is True
    assert resolved["stage05_mode"] == "reference_guided_storyboard"
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert resolved["comfyui_workflow_name"] == "qwen_edit_nextscene_local"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert resolved["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert resolved["preferred_comfyui_workflow_source_ref"].endswith("QwenEdit+NextScene（自动分镜）-V1版.json")
    assert resolved["comfyui_control_mode"] == "reference_guided"
    assert resolved["reference_bootstrap_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert resolved["reference_bootstrap_workflow_name"] == "amazing_z_photo_safetensors"


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


def test_workflow_replacements_for_job_keeps_job_style_selector_over_optimization_default() -> None:
    replacements = run_comfyui_txt2img.workflow_replacements_for_job(
        {
            "prompt": "shoreline scene",
            "negative_prompt": "bad frame",
            "comfyui_style_selector": "classic_film_photo",
        },
        {
            "positive_prompt": {"node_id": "57", "control": "widget_value", "widget_index": 0},
            "negative_prompt": {"node_id": "60", "control": "widget_value", "widget_index": 0},
            "style_selector": {
                "node_id": "88",
                "control": "choice_set_mode",
                "default_choice": "production_photo",
            },
            "width": {"node_id": "243", "control": "widget_value", "widget_index": 0},
            "height": {"node_id": "248", "control": "widget_value", "widget_index": 0},
        },
        width=1344,
        height=896,
        seed=42,
        optimization={
            "workflow_replacements": {
                "style_selector": "production_photo",
            }
        },
    )
    assert replacements["style_selector"] == "classic_film_photo"


def test_workflow_replacements_for_qwen_nextscene_include_layout_controls() -> None:
    replacements = run_comfyui_txt2img.workflow_replacements_for_job(
        {
            "prompt": "Next Scene：same heroine on the beach at dusk.",
            "negative_prompt": "bad frame",
        },
        {
            "positive_prompt": {"node_id": "123", "control": "widget_value", "widget_index": 0},
            "seed": {"node_id": "10", "control": "widget_value", "widget_index": 0},
            "target_size": {"node_id": "21", "control": "widget_value", "widget_index": 1},
            "target_vl_size": {"node_id": "21", "control": "widget_value", "widget_index": 2},
            "crop_method": {"node_id": "21", "control": "widget_value", "widget_index": 4},
        },
        width=1344,
        height=896,
        seed=42,
    )
    assert replacements["target_size"] == 1024
    assert replacements["target_vl_size"] == 392
    assert replacements["crop_method"] == "center"


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


def test_build_provider_prompt_keeps_original_zimage_prompt_clean() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "黄昏海滩，黄昏海滩上，年轻女性沿着潮线慢慢往前走，像是在等海风把心事吹散。，先用横屏建立镜头交代海滩与天光。",
        "style_prompt": "写实电影感",
        "lighting_prompt": "warm sunset light",
        "consistency_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，深色过肩长发，浅色简洁长裙；保持同一张脸和同一服装轮廓。",
        "camera_prompt": "wide establishing shot",
        "performance_prompt": "慢、轻、克制，以真实呼吸带动作",
        "negative_prompt": "film set, tripod",
        "stage05_route_key": "realistic_cinematic",
        "comfyui_style_positive_anchor": "environment-first cinematic still",
        "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json",
    })
    assert "20岁出头的亚洲年轻女性" in prompt
    assert "深色过肩长发" in prompt
    assert "wide establishing shot" in prompt
    assert "warm sunset light" in prompt
    assert "不要出现摄影机" in prompt
    assert "Route intent:" not in prompt
    assert "Lighting:" not in prompt
    assert "Camera:" not in prompt
    assert "Avoid:" not in prompt


def test_build_provider_prompt_adds_realistic_establishing_guardrails() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "single woman walking along the shoreline at sunset",
        "style_prompt": "realistic cinematic still",
        "lighting_prompt": "warm sunset light",
        "consistency_prompt": "same woman, same beach, same dress",
        "camera_prompt": "wide shot",
        "negative_prompt": "low resolution",
        "comfyui_style_positive_anchor": "keep this inside the story world, not an on-set production image",
        "comfyui_style_negative_anchor": "camera rig, monitor, crew equipment",
        "stage05_route_key": "realistic_cinematic",
    })
    assert "Route intent: keep this inside the story world" in prompt
    assert "Lighting: warm sunset light" in prompt
    assert "true environmental establishing shot" in prompt
    assert "not a behind-the-scenes production still" in prompt
    assert "film set" in prompt
    assert "camera rig" in prompt
    assert "Style: realistic cinematic still" in prompt
    negative = run_comfyui_txt2img.effective_negative_prompt({
        "negative_prompt": "low resolution",
        "camera_prompt": "wide establishing shot",
        "stage05_route_key": "realistic_cinematic",
        "comfyui_style_negative_anchor": "camera rig, monitor, crew equipment",
    })
    assert "crew equipment" in negative
    assert "centered full-body portrait" in negative
    assert "hero poster framing" in negative


def test_build_provider_prompt_keeps_reference_guided_qwen_edit_prompt_natural() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "黄昏海滩，年轻的亚洲女性停下来望向海平线，呼吸和情绪都一点点慢下来。",
        "style_prompt": "realistic cinematic short film, natural skin texture, restrained emotion",
        "lighting_prompt": "warm sunset light, soft rim light, sea-surface reflections",
        "consistency_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，深色过肩长发，浅色简洁长裙；保持同一张脸和同一服装轮廓。",
        "camera_prompt": "medium close-up",
        "performance_prompt": "慢、轻、克制，以真实呼吸带动作",
        "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/Qwen-Edit-2511-shortdrama-character-anchor-base.json",
    })
    assert "严格沿用参考图中的同一位主角" in prompt
    assert "同一条裙子的版型、领口、腰线和整体轮廓" in prompt
    assert "medium close-up" in prompt
    assert "warm sunset light" in prompt
    assert "呼吸节奏放慢，表情更安静，视线停在海平线" in prompt
    assert "动作幅度要小，抬手、转身、迈步都放慢，停顿要清楚，不要大幅摆臂或夸张表情" in prompt
    assert "只改变场景、机位、动作和表情变化" in prompt
    assert "Route intent:" not in prompt
    assert "Lighting:" not in prompt
    assert "Camera:" not in prompt
    assert "Avoid:" not in prompt


def test_build_provider_prompt_keeps_reference_guided_qwen_nextscene_prompt_natural() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "Next Scene：黄昏海边，同一位年轻亚洲女性站在风里望向海平线，情绪慢慢沉下来。",
        "style_prompt": "realistic cinematic short film, natural skin texture, restrained emotion",
        "lighting_prompt": "warm sunset light, soft rim light, sea-surface reflections",
        "consistency_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，深色过肩长发，浅色简洁长裙；保持同一张脸和同一服装轮廓。",
        "camera_prompt": "medium close-up",
        "performance_prompt": "慢、轻、克制，以真实呼吸带动作",
        "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json",
    })
    assert "严格沿用参考图中的同一位主角" in prompt
    assert "同一条裙子的版型、领口、腰线和整体轮廓" in prompt
    assert "medium close-up" in prompt
    assert "warm sunset light" in prompt
    assert "表情更安静，嘴唇自然闭合，视线停在远处海平线" in prompt
    assert "胸口起伏、肩膀放松和步伐节奏要能看出真实呼吸带来的轻微变化" in prompt
    assert "只改变场景、机位、动作和表情变化" in prompt
    assert "只输出单张完整画面，不要宫格、拼贴、多分镜格或 contact sheet" in prompt
    assert "不要出现黑边、假电影边框、内嵌相框或任何画中画布局" in prompt
    assert "Route intent:" not in prompt
    assert "Lighting:" not in prompt
    assert "Camera:" not in prompt
    assert "Avoid:" not in prompt


def test_build_provider_prompt_trusts_concrete_qwen_nextscene_prompt_without_readding_abstract_tags() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "Next Scene：同一位20岁出头的亚洲年轻女性，保持同一张脸、同一发型、同一条浅色简洁长裙的版型、领口、腰线和整体轮廓不变。她继续沿着黄昏海滩向前走，把心事留在身后，整个人终于轻下来。镜头采用从人物后方偏左的三分之四长镜头，人物保持全身入镜，占画面中等偏小比例，发型长度、裙摆轮廓和行走姿态都要清楚可读，必须是完整满幅画面而不是假电影边框。暖金色夕阳逆光拉长背影，海面与晚霞继续呼吸，情绪收束而释然。full-frame image, no black bars, no embedded border, no picture-in-picture frame, no extra people, realistic cinematic short film.",
        "style_prompt": "realistic cinematic short film, natural skin texture, restrained emotion, coherent production design",
        "lighting_prompt": "warm sunset light, soft rim light, sea-surface reflections, gentle contrast, cinematic golden-hour atmosphere",
        "consistency_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，年轻干净的脸，深色过肩长发，浅色简洁长裙，黄昏海滩，表情安静克制、略带心事；保持同一张脸、同一发型、同一服装轮廓与同一情绪气场。",
        "identity_anchor_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，年轻干净的脸，深色过肩长发，浅色简洁长裙，黄昏海滩，表情安静克制、略带心事；保持同一张脸、同一发型、同一服装轮廓与同一情绪气场。",
        "camera_prompt": "wide shot / back view",
        "performance_prompt": "慢、轻、克制，以真实呼吸带动作",
        "prompt_composition_mode": "zimage_skill_aligned",
        "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json",
    })
    assert "严格沿用参考图中的同一位主角" in prompt
    assert "full-frame image" in prompt
    assert "no black bars" in prompt
    assert "镜头采用wide shot / back view" not in prompt
    assert "人物不要正面看向镜头，镜头以后背或侧后方轮廓为主" in prompt
    assert "必须是完整满幅画面，full-frame image, no black bars, no embedded border, no picture-in-picture frame" in prompt
    assert "发型长度、裙摆轮廓和行走姿态都要清楚可读，不能只剩模糊背影" in prompt
    assert "人物在画面中保持较小比例，环境空间要比人物更突出" in prompt
    assert "不要把画面拍成人像照或大半身构图，人物高度不要超过画面高度的三分之一，海岸线、天空和海面应占据主要画面" in prompt
    assert "肩膀比前一镜头更放松，步伐更稳定，呼吸更均匀" in prompt
    assert "肩膀自然下沉，背部不再紧绷" in prompt
    assert "海面反光、晚霞层次和海平线继续清楚可见" in prompt
    assert "主角始终是20岁出头的亚洲年轻女性，年轻干净的脸，深色过肩长发，浅色简洁长裙，黄昏海滩，表情平静，嘴唇自然闭合，眉头轻微收住，视线稳定，不夸张微笑" in prompt
    assert "人物状态与动作保持慢、轻、克制，以真实呼吸带动作" not in prompt
    assert "整体画面质感保持realistic cinematic short film" not in prompt
    assert "光线与环境氛围为warm sunset light" not in prompt
    assert "realistic cinematic short film" not in prompt
    assert "同一情绪气场" not in prompt
    assert "略带心事" not in prompt


def test_build_provider_prompt_adds_establishing_specific_qwen_reinforcement() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "Next Scene：同一位20岁出头的亚洲年轻女性沿着黄昏海滩慢慢往前走，海风把情绪一点点吹开。镜头采用极宽建立镜头，人物只占较小比例，环境完整可读。full-frame image, no black bars, no embedded border, no extra people, realistic cinematic short film.",
        "style_prompt": "realistic cinematic short film, natural skin texture, restrained emotion, coherent production design",
        "lighting_prompt": "warm sunset light, soft rim light, sea-surface reflections, gentle contrast, cinematic golden-hour atmosphere",
        "consistency_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，年轻干净的脸，深色过肩长发，浅色简洁长裙，黄昏海滩，表情安静克制、略带心事；保持同一张脸、同一发型、同一服装轮廓与同一情绪气场。",
        "identity_anchor_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，年轻干净的脸，深色过肩长发，浅色简洁长裙，黄昏海滩，表情安静克制、略带心事；保持同一张脸、同一发型、同一服装轮廓与同一情绪气场。",
        "camera_prompt": "wide establishing shot",
        "prompt_composition_mode": "zimage_skill_aligned",
        "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json",
    })
    assert "人物在画面中保持较小比例，环境空间要比人物更突出" in prompt
    assert "不要把画面拍成人像照或大半身构图，人物高度不要超过画面高度的三分之一，海岸线、天空和海面应占据主要画面" in prompt
    assert "人物不要站在画面正中央成为主视觉，面部不能比环境更抢眼，应先读到海岸线、海面和天光，再读到人物" in prompt


def test_build_provider_prompt_adds_backview_border_guardrails_for_qwen_even_without_precomposed_prompt() -> None:
    prompt = run_comfyui_txt2img.build_provider_prompt({
        "prompt": "Next Scene：同一位年轻亚洲女性在黄昏海边继续向前走。",
        "style_prompt": "realistic cinematic short film, natural skin texture, restrained emotion",
        "lighting_prompt": "warm sunset light, soft rim light, sea-surface reflections",
        "consistency_prompt": "Character identity anchor: 同一人物设定：20岁出头的亚洲年轻女性，深色过肩长发，浅色简洁长裙；保持同一张脸和同一服装轮廓。",
        "camera_prompt": "wide shot / back view",
        "performance_prompt": "慢、轻、克制，以真实呼吸带动作",
        "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json",
    })
    assert "必须是完整满幅画面，full-frame image, no black bars, no embedded border, no picture-in-picture frame" in prompt
    assert "发型长度、裙摆轮廓和行走姿态都要清楚可读，不能只剩模糊背影" in prompt
    assert "只输出单张完整画面，不要宫格、拼贴、多分镜格或 contact sheet" in prompt


def test_qwen_target_size_tracks_requested_dimensions() -> None:
    assert run_comfyui_txt2img._qwen_target_size_for_dimensions(1344, 896) == 1024
    assert run_comfyui_txt2img._qwen_target_size_for_dimensions(1536, 1024) == 1344


def test_qwen_target_vl_size_tracks_requested_orientation() -> None:
    assert run_comfyui_txt2img._qwen_target_vl_size_for_dimensions(1344, 896) == 392
    assert run_comfyui_txt2img._qwen_target_vl_size_for_dimensions(896, 1344) == 384


def test_qwen_nextscene_reference_is_adapted_to_landscape_canvas(tmp_path: Path) -> None:
    source_image = tmp_path / "portrait.png"

    Image.new("RGB", (896, 1344), color=(180, 170, 160)).save(source_image, format="PNG")
    manifest_path = tmp_path / "video_project" / "05_images" / "keyframe_image_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}", encoding="utf-8")
    input_dir = tmp_path / "comfy_input"
    input_dir.mkdir(parents=True, exist_ok=True)
    replacements, staged_records = run_comfyui_txt2img._reference_image_replacements_for_job(
        manifest_path,
        {
            "image_id": "IMG_S001_START",
            "aspect_ratio": "16:9",
            "reference_images": [str(source_image)],
            "reference_guidance_active": True,
        },
        width=1344,
        height=896,
        input_dir=input_dir,
        workflow_mapping_key="stage05_realistic_cinematic_qwen_edit_nextscene_local",
        nodes={"reference_image_path": {"node_id": "13", "control": "widget_value", "widget_index": 0}},
    )
    assert "reference_image_path" in replacements
    staged_path = input_dir / replacements["reference_image_path"]
    assert staged_path.exists()
    with Image.open(staged_path) as adapted:
        ratio = adapted.width / adapted.height
    assert abs(ratio - (16 / 9)) < 0.02


def test_validate_rendered_output_dimensions_blocks_landscape_request_that_falls_back_to_portrait(tmp_path: Path) -> None:
    output_path = tmp_path / "portrait.png"
    Image.new("RGB", (840, 1256), color=(160, 150, 140)).save(output_path, format="PNG")
    try:
        run_comfyui_txt2img._validate_rendered_output_dimensions(
            output_path,
            requested_width=1344,
            requested_height=896,
        )
    except Exception as exc:  # noqa: BLE001
        assert "fell back to portrait orientation" in str(exc)
    else:
        raise AssertionError("Expected orientation validation to fail")


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
    assert manifest["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert manifest["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert manifest["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert manifest["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert manifest["route_migration_state"] == "stage05b_reference_guided_mainline"
    assert manifest["preferred_comfyui_workflow_source_ref"] == "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json"
    assert manifest["preferred_comfyui_workflow_format"] == "ui_graph"
    assert manifest["preferred_comfyui_workflow_custom_node_dependencies"] == ["rgthree-comfy"]
    assert manifest["preferred_comfyui_workflow_import_blockers"] == []
    assert manifest["comfyui_optimization_profile"] == "balanced"
    assert manifest["comfyui_optimization_profile_label"] == "Balanced"
    assert manifest["comfyui_optimization"]["profile_key"] == "balanced"
    assert manifest["comfyui_optimization"]["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert manifest["route_resolution"]["used_registry"] is True
    assert all(job["style_family"] == "realistic" for job in manifest["jobs"])
    assert all(job["stage05_route_key"] == "realistic_cinematic" for job in manifest["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local" for job in manifest["jobs"])
    assert all(job["comfyui_workflow_name"] == "qwen_edit_nextscene_local" for job in manifest["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local" for job in manifest["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511" for job in manifest["jobs"])
    assert all(job["route_migration_state"] == "stage05b_reference_guided_mainline" for job in manifest["jobs"])
    assert all(job["preferred_comfyui_workflow_format"] == "ui_graph" for job in manifest["jobs"])
    assert all(job["comfyui_optimization_profile"] == "balanced" for job in manifest["jobs"])
    assert all(job["comfyui_optimization_profile_label"] == "Balanced" for job in manifest["jobs"])
    request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    assert request_manifest["workflow_name"] == "auto_style_family"
    assert request_manifest["workflow_selection_mode"] == "stage05_route_registry"
    assert request_manifest["stage05_route_key"] == "realistic_cinematic"
    assert request_manifest["route_resolution_mode"] == "stage00_style_registry_plus_stage05b_mainline"
    assert request_manifest["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    assert request_manifest["workflow_mapping_keys"] == ["stage05_realistic_cinematic_qwen_edit_nextscene_local"]
    assert request_manifest["comfyui_model_id"] == "Qwen/Qwen-Edit-2511"
    assert request_manifest["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
    assert request_manifest["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
    assert request_manifest["route_migration_state"] == "stage05b_reference_guided_mainline"
    assert request_manifest["preferred_comfyui_workflow_source_ref"] == "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json"
    assert request_manifest["preferred_comfyui_workflow_format"] == "ui_graph"
    assert request_manifest["preferred_comfyui_workflow_custom_node_dependencies"] == ["rgthree-comfy"]
    assert request_manifest["preferred_comfyui_workflow_import_blockers"] == []
    assert request_manifest["optimization_profile"] == "balanced"
    assert request_manifest["optimization_profile_label"] == "Balanced"
    assert request_manifest["workflow_path"] == str(workflow_paths["stage05_realistic_cinematic_qwen_edit_nextscene_local"]).replace("\\", "/")
    assert request_manifest["workflow_paths"] == [str(workflow_paths["stage05_realistic_cinematic_qwen_edit_nextscene_local"]).replace("\\", "/")]
    assert len(request_manifest["requests"]) == 2
    assert all(item["status"] == "planned" for item in request_manifest["requests"])
    assert all(item["stage05_route_key"] == "realistic_cinematic" for item in request_manifest["requests"])
    assert all(item["style_family"] == "realistic" for item in request_manifest["requests"])
    assert all(item["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local" for item in request_manifest["requests"])
    assert all(item["comfyui_model_id"] == "Qwen/Qwen-Edit-2511" for item in request_manifest["requests"])
    assert all(item["workflow_name"] == "qwen_edit_nextscene_local" for item in request_manifest["requests"])
    assert all(item["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local" for item in request_manifest["requests"])
    assert all(item["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511" for item in request_manifest["requests"])
    assert all(item["route_migration_state"] == "stage05b_reference_guided_mainline" for item in request_manifest["requests"])
    assert all(item["preferred_comfyui_workflow_format"] == "ui_graph" for item in request_manifest["requests"])
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


def test_run_comfyui_txt2img_dry_run_blocks_multiline_qwen_nextscene_prompt(tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    config_path = _write_config(tmp_path, base_url="http://127.0.0.1:8188", output_root=output_root)
    project_dir = manifest_json.parents[1]
    reference_dir = project_dir / "03_characters" / "reference_images"
    reference_dir.mkdir(parents=True, exist_ok=True)
    _write_test_png(reference_dir / "CHAR_001_primary.png")

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    data["comfyui_workflow_mapping_key"] = "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    data["comfyui_workflow_name"] = "stage05_realistic_cinematic_qwen_edit_nextscene_local"
    data["preferred_comfyui_workflow_source_ref"] = "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json"
    data["comfyui_control_mode"] = "reference_guided"
    data["reference_guidance_active"] = True
    for job in data["jobs"]:
        job["comfyui_workflow_mapping_key"] = "stage05_realistic_cinematic_qwen_edit_nextscene_local"
        job["comfyui_workflow_name"] = "stage05_realistic_cinematic_qwen_edit_nextscene_local"
        job["preferred_comfyui_workflow_source_ref"] = data["preferred_comfyui_workflow_source_ref"]
        job["comfyui_control_mode"] = "reference_guided"
        job["reference_guidance_active"] = True
        job["reference_images"] = ["03_characters/reference_images/CHAR_001_primary.png"]
        job["missing_reference_images"] = []
        job["stage06_route_hint"] = "single_subject_motion"
        job["stage06_requires_mid_guide"] = False
        job["prompt"] = "Next Scene：同一位年轻亚洲女性站在黄昏海边，望向海平线。\nNext Scene：同一位年轻亚洲女性继续站在黄昏海边，侧身转头。"
    manifest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    assert run_comfyui_txt2img.main([
        str(manifest_json),
        "--config", str(config_path),
        "--mapping", str(mapping_path),
        "--workflow-name", "stage05_realistic_cinematic_qwen_edit_nextscene_local",
        "--dry-run",
        "--allow-beyond-requested-scope",
    ]) == 1
    updated = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert updated["jobs"][0]["status"] == "blocked"
    assert "single-shot prompt" in updated["jobs"][0]["errors"][0]["message"]
    requests = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
    assert requests["requests"][0]["status"] == "blocked"
    assert "single-shot prompt" in requests["requests"][0]["error_message"]


def test_run_comfyui_txt2img_success_updates_manifest_and_passes_validator(monkeypatch, tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, workflow_paths = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    _patch_ui_graph_conversion(monkeypatch)
    server, thread = _start_server("success", output_root=output_root, output_size=(896, 1344))
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
                "route=realistic_cinematic; route_state=stage05b_reference_guided_mainline; preferred_workflow=qwen_edit_nextscene_local; profile=balanced; size=896x1344; mapping=stage05_realistic_cinematic_qwen_edit_nextscene_local; workflow=qwen_edit_nextscene_local;"
            )
            for job in data["jobs"]
        )
        request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["workflow_name"] == "auto_style_family"
        assert request_manifest["stage05_route_key"] == "realistic_cinematic"
        assert request_manifest["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
        assert request_manifest["optimization_profile"] == "balanced"
        assert request_manifest["optimization_profile_label"] == "Balanced"
        assert request_manifest["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
        assert request_manifest["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Edit-2511"
        assert request_manifest["route_migration_state"] == "stage05b_reference_guided_mainline"
        assert request_manifest["preferred_comfyui_workflow_format"] == "ui_graph"
        assert request_manifest["workflow_path"] == str(workflow_paths["stage05_realistic_cinematic_qwen_edit_nextscene_local"]).replace("\\", "/")
        assert all(item["status"] == "succeeded" for item in request_manifest["requests"])
        assert all(item["stage05_route_key"] == "realistic_cinematic" for item in request_manifest["requests"])
        assert all(item["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local" for item in request_manifest["requests"])
        assert all(item["workflow_name"] == "qwen_edit_nextscene_local" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local" for item in request_manifest["requests"])
        assert all(item["route_migration_state"] == "stage05b_reference_guided_mainline" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_format"] == "ui_graph" for item in request_manifest["requests"])
        assert all(item["comfyui_optimization_profile"] == "balanced" for item in request_manifest["requests"])
        workflow_payload = _FakeComfyTxt2ImgHandler.requests[0]["extra_data"]["extra_pnginfo"]["workflow"]
        first_nodes = {str(node["id"]): node for node in workflow_payload["nodes"]}
        assert "严格沿用参考图中的同一位主角" in first_nodes["123"]["widgets_values"][0]
        assert "不要出现黑边" in first_nodes["123"]["widgets_values"][0]
        assert "只输出单张完整画面" in first_nodes["123"]["widgets_values"][0]
        assert first_nodes["13"]["widgets_values"][0].endswith(".png")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_txt2img_fails_when_portrait_request_falls_back_to_landscape(monkeypatch, tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    _patch_ui_graph_conversion(monkeypatch)
    server, thread = _start_server("success", output_root=output_root, output_size=(1256, 840))
    try:
        config_path = _write_config(tmp_path, base_url=f"http://127.0.0.1:{server.server_port}", output_root=output_root)
        assert run_comfyui_txt2img.main([
            str(manifest_json),
            "--config", str(config_path),
            "--mapping", str(mapping_path),
            "--workflow-name", "stage05_realistic_cinematic_amazing_z_photo_original",
            "--poll-interval", "0.01",
            "--max-wait-seconds", "2",
        ]) == 1
        data = json.loads(manifest_json.read_text(encoding="utf-8"))
        assert all(job["status"] == "failed" for job in data["jobs"])
        assert "fell back to landscape orientation" in data["jobs"][0]["errors"][0]["message"]
        request_manifest = json.loads((manifest_json.parent / "comfyui_image_requests.json").read_text(encoding="utf-8"))
        assert request_manifest["requests"][0]["status"] == "failed"
        assert "fell back to landscape orientation" in request_manifest["requests"][0]["error_message"]
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_txt2img_runs_auto_repair_second_pass_for_risky_prompt(monkeypatch, tmp_path: Path) -> None:
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
        "reason": "Umbrella prop-contact scenes generated without structure guidance are still prone to anatomy drift, handle-contact errors, and duplicate umbrella artifacts. Review carefully before Stage 06.",
    }
    manifest["jobs"] = [risky_job]
    manifest["summary"]["expected_image_count"] = 1
    manifest["summary"]["shot_count"] = 1
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    _patch_ui_graph_conversion(monkeypatch)
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


def test_validator_accepts_null_optional_route_metadata_on_successful_manifest(monkeypatch, tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    _patch_ui_graph_conversion(monkeypatch)
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


def test_validator_accepts_mixed_job_style_presets_when_top_level_style_metadata_is_null(monkeypatch, tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    _patch_ui_graph_conversion(monkeypatch)
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
        data["comfyui_style_preset_key"] = None
        data["comfyui_style_preset_label"] = None
        data["comfyui_style_positive_anchor"] = None
        data["comfyui_style_negative_anchor"] = None
        for idx, job in enumerate(data["jobs"]):
            if idx % 2 == 0:
                job["comfyui_style_preset_key"] = "environmental_establishing_film"
                job["comfyui_style_preset_label"] = "Environmental Establishing Film"
                job["comfyui_style_positive_anchor"] = "environment-first cinematic still"
                job["comfyui_style_negative_anchor"] = "film set contamination"
        ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
        assert ok, errors
        assert warnings == []
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_sync_normalizes_mixed_job_style_presets_back_to_top_level_null(monkeypatch, tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, _ = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    _patch_ui_graph_conversion(monkeypatch)
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
        data["comfyui_style_preset_key"] = "environmental_establishing_film"
        data["comfyui_style_preset_label"] = "Environmental Establishing Film"
        data["comfyui_style_positive_anchor"] = "environment-first cinematic still"
        data["comfyui_style_negative_anchor"] = "film set contamination"
        for idx, job in enumerate(data["jobs"]):
            if idx % 2 == 0:
                job["comfyui_style_preset_key"] = "environmental_establishing_film"
                job["comfyui_style_preset_label"] = "Environmental Establishing Film"
                job["comfyui_style_positive_anchor"] = "environment-first cinematic still"
                job["comfyui_style_negative_anchor"] = "film set contamination"
            else:
                job["comfyui_style_preset_key"] = None
                job["comfyui_style_preset_label"] = None
                job["comfyui_style_positive_anchor"] = None
                job["comfyui_style_negative_anchor"] = None
        sync_keyframe_image_manifest.normalize_stage05_route_fields(data)
        assert data["comfyui_style_preset_key"] is None
        assert data["comfyui_style_preset_label"] is None
        assert data["comfyui_style_positive_anchor"] is None
        assert data["comfyui_style_negative_anchor"] is None
        ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
        assert ok, errors
        assert warnings == []
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_comfyui_txt2img_failure_records_errors(monkeypatch, tmp_path: Path) -> None:
    manifest_json = _prepare_manifest(tmp_path)
    mapping_path, workflow_paths = _write_mapping_and_workflow(tmp_path)
    output_root = tmp_path / "comfy_output"
    _patch_ui_graph_conversion(monkeypatch)
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
        assert request_manifest["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local"
        assert request_manifest["optimization_profile"] == "balanced"
        assert request_manifest["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local"
        assert request_manifest["route_migration_state"] == "stage05b_reference_guided_mainline"
        assert request_manifest["preferred_comfyui_workflow_format"] == "ui_graph"
        assert request_manifest["workflow_path"] == str(workflow_paths["stage05_realistic_cinematic_qwen_edit_nextscene_local"]).replace("\\", "/")
        assert all(item["status"] == "failed" for item in request_manifest["requests"])
        assert all(item["stage05_route_key"] == "realistic_cinematic" for item in request_manifest["requests"])
        assert all(item["workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_nextscene_local" for item in request_manifest["requests"])
        assert all(item["workflow_name"] == "qwen_edit_nextscene_local" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_candidate"] == "qwen_edit_nextscene_local" for item in request_manifest["requests"])
        assert all(item["route_migration_state"] == "stage05b_reference_guided_mainline" for item in request_manifest["requests"])
        assert all(item["preferred_comfyui_workflow_format"] == "ui_graph" for item in request_manifest["requests"])
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
