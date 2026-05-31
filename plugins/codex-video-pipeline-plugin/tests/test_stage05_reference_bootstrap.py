#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_stage05_bootstrap_test", IMAGES / "new_keyframe_image_jobs.py")
bootstrap_reference_image_from_keyframe = load_module(
    "bootstrap_reference_image_from_keyframe_test",
    IMAGES / "bootstrap_reference_image_from_keyframe.py",
)


def test_bootstrap_reference_image_from_existing_keyframe_switches_realistic_route_to_reference_guided(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_bootstrap_reference_demo"
    intake_dir = project_dir / "00_intake"
    characters_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    reference_dir = characters_dir / "reference_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    characters_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "schema_version": "0.6.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T18:00:00+08:00",
    })
    brief["normalized"]["style"] = "写实电影感"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    target_reference = "03_characters/reference_images/CHAR_001_primary.png"
    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["status"] = "confirmed"
    keyframe["reference_image_status"] = {
        "required": True,
        "target_paths": [target_reference],
        "existing_paths": [],
        "missing_paths": [target_reference],
        "all_present": False,
        "item_count": 1,
        "missing_count": 1,
        "items": [{"character_id": "CHAR_001", "target_path": target_reference, "file_exists": False}],
    }
    keyframe["stage05_execution_readiness"] = {
        "continuity_mode": "character_locked",
        "reference_image_required": True,
        "safe_to_auto_generate": False,
        "blocker_reasons": ["missing_character_reference_images"],
        "missing_reference_images": [target_reference],
    }
    keyframe["self_check"]["character_reference_images_ready"] = False
    keyframe["self_check"]["safe_for_auto_image_generation"] = False
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    shot = keyframe["shot_prompts"][0]
    shot["dependencies"] = {"reference_images": [target_reference]}
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    character_bible = {
        "schema_version": "0.4.0",
        "stage": "STAGE_03_CHARACTER_BIBLE",
        "status": "draft",
        "project_id": project_dir.name,
        "reference_image_required": True,
        "compiled_requirements": {"continuity_mode": "character_locked"},
        "reference_image_plan": {
            "project_id": project_dir.name,
            "required": True,
            "reference_images": [
                {
                    "character_id": "CHAR_001",
                    "name": "主角",
                    "target_path": target_reference,
                    "visual_consistency_prompt": "same protagonist",
                    "negative_consistency_prompt": "different character",
                }
            ],
        },
        "reference_image_status": {
            "required": True,
            "target_paths": [target_reference],
            "existing_paths": [],
            "missing_paths": [target_reference],
            "all_present": False,
            "item_count": 1,
            "missing_count": 1,
            "items": [{"character_id": "CHAR_001", "target_path": target_reference, "file_exists": False}],
        },
        "stage05_execution_readiness": {
            "continuity_mode": "character_locked",
            "reference_image_required": True,
            "safe_to_auto_generate": False,
            "blocker_reasons": ["missing_character_reference_images"],
            "missing_reference_images": [target_reference],
        },
        "self_check": {
            "reference_images_planned": True,
            "reference_images_ready": False,
            "safe_for_character_locked_image_generation": False,
            "notes": [f"Reference images still missing for character-locked continuity: {target_reference}"],
        },
    }
    character_bible_path = characters_dir / "character_bible.json"
    character_bible_path.write_text(json.dumps(character_bible, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    source_job = manifest["jobs"][0]
    source_path = Path(source_job["output_path"])
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"PNGDATA")
    source_job["status"] = "succeeded"
    source_job["provider"] = "comfyui_txt2img"
    source_job["evidence"]["file_path"] = str(source_path).replace("\\", "/")
    source_job["evidence"]["file_exists"] = True
    source_job["evidence"]["file_size_bytes"] = source_path.stat().st_size
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    rerun_calls: list[list[str]] = []

    def fake_rerun(argv: list[str] | None = None) -> int:
        assert argv is not None
        rerun_calls.append(list(argv))
        image_id = argv[2]
        current = json.loads(manifest_json.read_text(encoding="utf-8"))
        for job in current["jobs"]:
            if job["image_id"] != image_id:
                continue
            output_path = Path(job["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(f"PNG-{image_id}".encode("utf-8"))
            job["status"] = "succeeded"
            job["provider"] = "comfyui_txt2img"
            job["notes"] = f"rerun via reference-guided bundle {image_id}"
            job["evidence"]["file_path"] = str(output_path).replace("\\", "/")
            job["evidence"]["file_exists"] = True
            job["evidence"]["file_size_bytes"] = output_path.stat().st_size
        manifest_json.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    bootstrap_reference_image_from_keyframe.run_comfyui_txt2img.main = fake_rerun

    assert bootstrap_reference_image_from_keyframe.main([
        str(manifest_json),
        "--target-reference",
        target_reference,
        "--source-image-id",
        str(source_job["image_id"]),
        "--allow-beyond-requested-scope",
    ]) == 0

    target_path = reference_dir / "CHAR_001_primary.png"
    assert target_path.exists()
    assert target_path.read_bytes() == b"PNGDATA"

    refreshed_character_bible = json.loads(character_bible_path.read_text(encoding="utf-8"))
    assert refreshed_character_bible["reference_image_status"]["all_present"] is True
    assert refreshed_character_bible["stage05_execution_readiness"]["safe_to_auto_generate"] is True

    refreshed_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert refreshed_manifest["reference_guidance_ready"] is True
    assert refreshed_manifest["reference_guidance_active"] is True
    assert refreshed_manifest["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_reference"
    assert refreshed_manifest["comfyui_workflow_name"] == "txt2img_keyframe_shortdrama_qwen_edit_reference"
    assert refreshed_manifest["route_resolution"]["workflow_mapping_resolution"] == "route_registry_reference_guided_target"
    assert [args[2] for args in rerun_calls] == ["IMG_S001_START", "IMG_S001_END"]
