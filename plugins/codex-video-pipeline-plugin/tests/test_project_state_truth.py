from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
project_state = importlib.import_module("pipeline_core.project_state")


def test_sync_project_truth_demotes_optimistic_manifest_to_stage05_review_required(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "creator_trial_20260530_rainy_store"
    (project_dir / "05_images").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_08_ASSEMBLY_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": True,
        "keyframe_prompts_confirmed": True,
        "keyframe_images_confirmed": True,
        "video_clips_confirmed": True,
        "audio_confirmed": True,
        "assembly_confirmed": True,
        "allowed_next_stage": "STAGE_09_QA",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "05_images" / "keyframe_image_manifest.json").write_text(json.dumps({
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": project_dir.name,
        "image_provider_strategy": {"primary": "openai_image", "fallback": ["comfyui", "manual"]},
        "jobs": [
            {
                "image_id": "IMG_S001_START",
                "provider": "openai_image",
                "evidence": {"file_exists": True, "file_size_bytes": 123},
            },
            {
                "image_id": "IMG_S001_END",
                "provider": "openai_image",
                "evidence": {"file_exists": True, "file_size_bytes": 123},
            },
        ],
        "quality_review": {
            "blocking_image_ids": ["IMG_S001_START"],
            "next_review_image_ids": ["IMG_S001_START"],
            "manual_review_cleared": False,
        },
        "self_check": {
            "all_required_images_exist": True,
            "manual_review_cleared": False,
            "ready_for_video_clip_generation": False,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path

    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert synced["current_stage"] == "STAGE_05_KEYFRAME_IMAGES"
    assert synced["allowed_next_stage"] is None
    assert synced["keyframe_images_confirmed"] is False
    assert synced["video_clips_confirmed"] is False
    assert synced["audio_confirmed"] is False
    assert synced["assembly_confirmed"] is False
    assert synced["creator_status_overview"]["current_blocker"].startswith("Stage 05")
    assert "IMG_S001_START" in synced["creator_status_overview"]["current_blocker"]
    assert (project_dir / "creator_status_overview.md").exists()
    overview_json = json.loads((project_dir / "creator_status_overview.json").read_text(encoding="utf-8"))
    assert overview_json["trusted_stage"] == "STAGE_05_KEYFRAME_IMAGES"


def test_sync_project_truth_marks_placeholder_stage06_as_non_confirmed(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "real_smoke"
    (project_dir / "05_images").mkdir(parents=True, exist_ok=True)
    (project_dir / "06_video_clips").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_06_VIDEO_CLIPS_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": True,
        "keyframe_prompts_confirmed": True,
        "keyframe_images_confirmed": True,
        "video_clips_confirmed": True,
        "allowed_next_stage": "STAGE_07_AUDIO",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "05_images" / "keyframe_image_manifest.json").write_text(json.dumps({
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": project_dir.name,
        "image_provider_strategy": {"primary": "openai_image", "fallback": ["comfyui", "manual"]},
        "jobs": [
            {
                "image_id": "IMG_S001_START",
                "provider": "openai_image",
                "evidence": {"file_exists": True, "file_size_bytes": 123},
            }
        ],
        "quality_review": {"manual_review_cleared": True},
        "self_check": {
            "all_required_images_exist": True,
            "manual_review_cleared": True,
            "ready_for_video_clip_generation": True,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "06_video_clips" / "video_clip_manifest.json").write_text(json.dumps({
        "stage": "STAGE_06_VIDEO_CLIPS",
        "status": "generated",
        "project_id": project_dir.name,
        "video_provider_strategy": {"primary": "comfyui_ltx_i2v", "fallback": ["manual"]},
        "jobs": [
            {
                "clip_id": "CLIP_S001",
                "provider": "placeholder_test_video_generator",
                "status": "succeeded",
                "evidence": {"file_exists": True, "file_size_bytes": 80},
            }
        ],
        "self_check": {
            "all_required_clips_exist": False,
            "ready_for_audio_stage": False,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path

    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert synced["current_stage"] == "STAGE_06_VIDEO_CLIPS"
    assert synced["allowed_next_stage"] is None
    assert synced["video_clips_confirmed"] is False
    stage06_truth = synced["state_truth"]["stage_states"]["stage06"]
    assert stage06_truth["evidence_origin_summary"]["placeholder_or_incomplete"] == 1
    assert "占位" in synced["creator_status_overview"]["current_result"]


def test_sync_project_truth_keeps_stage08_with_fallback_segments_out_of_confirmed(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "rough_cut_with_fallback_segments"
    (project_dir / "08_assembly" / "rough_cut").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_08_ASSEMBLY_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": True,
        "keyframe_prompts_confirmed": True,
        "keyframe_images_confirmed": True,
        "video_clips_confirmed": True,
        "audio_confirmed": True,
        "assembly_confirmed": True,
        "allowed_next_stage": "STAGE_09_QA",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    rough_cut = project_dir / "08_assembly" / "rough_cut" / "rough_cut.mp4"
    rough_cut.write_bytes(b"\x00\x00\x00\x18ftypmp42REALCUT" + (b"1" * 256))
    (project_dir / "08_assembly" / "assembly_manifest.json").write_text(json.dumps({
        "stage": "STAGE_08_ASSEMBLY",
        "status": "generated",
        "project_id": project_dir.name,
        "final_output_path": str(rough_cut).replace("\\", "/"),
        "assembly_provider": "ffmpeg",
        "evidence": {
            "file_path": str(rough_cut).replace("\\", "/"),
            "file_exists": True,
            "file_size_bytes": rough_cut.stat().st_size,
        },
        "summary": {
            "fallback_visual_segment_count": 1,
        },
        "self_check": {
            "has_timeline_from_confirmed_clips": True,
            "has_audio_mix_plan": True,
            "has_edit_decision_list": True,
            "has_final_output_file": True,
            "ready_for_qa_stage": True,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path

    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert synced["current_stage"] == "STAGE_08_ASSEMBLY"
    assert synced["allowed_next_stage"] is None
    assert synced["assembly_confirmed"] is False
    stage08_truth = synced["state_truth"]["stage_states"]["stage08"]
    assert stage08_truth["normalized_status"] == "review_required"
    assert "fallback" in synced["creator_status_overview"]["current_result"]
