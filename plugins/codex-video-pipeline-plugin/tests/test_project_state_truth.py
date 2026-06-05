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
    assert (project_dir / "creator_home.html").exists()
    overview_json = json.loads((project_dir / "creator_status_overview.json").read_text(encoding="utf-8"))
    assert overview_json["trusted_stage"] == "STAGE_05_KEYFRAME_IMAGES"
    assert overview_json["recommended_entry"]["label"] == "打开 Stage 05 审图工作台"


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


def test_sync_project_truth_frontloads_reference_image_recovery_before_stage05(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "reference_gap_project"
    (project_dir / "03_characters").mkdir(parents=True, exist_ok=True)
    (project_dir / "04_keyframes").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_title": "雨夜便利店让伞",
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_04_KEYFRAME_PROMPTS_GENERATION",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": True,
        "keyframe_prompts_confirmed": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "03_characters" / "character_bible.json").write_text(json.dumps({
        "stage": "STAGE_03_CHARACTER_BIBLE",
        "project_id": project_dir.name,
        "reference_image_status": {
            "all_present": False,
            "missing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
        "stage05_execution_readiness": {
            "safe_to_auto_generate": False,
            "missing_reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "04_keyframes" / "keyframe_prompts.json").write_text(json.dumps({
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "project_id": project_dir.name,
        "reference_image_status": {
            "all_present": False,
            "missing_paths": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
        "stage05_execution_readiness": {
            "safe_to_auto_generate": False,
            "missing_reference_images": ["03_characters/reference_images/CHAR_001_primary.png"],
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path

    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    overview = synced["creator_status_overview"]
    assert overview["project_display_name"] == "雨夜便利店让伞"
    assert "角色参考图" in overview["current_result"]
    assert "参考图" in overview["current_blocker"]
    assert overview["recommended_entry"]["label"] == "打开角色参考图说明"
    assert overview["recommended_entry"]["path"].endswith("03_characters/reference_image_start_here.md")


def test_sync_project_truth_marks_stage01_generated_as_pending_confirmation(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "stage01_generated_pending_confirm"
    (project_dir / "01_script").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_title": "黄昏海滩散步",
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_01_SCRIPT_GENERATION",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": False,
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "01_script" / "script.json").write_text(json.dumps({
        "stage": "STAGE_01_SCRIPT_GENERATION",
        "project_id": project_dir.name,
        "title": "海风停在黄昏里",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path

    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    overview = synced["creator_status_overview"]
    script_step = next(step for step in overview["steps"] if step["step"] == "剧本")
    assert synced["current_stage"] == "STAGE_01_SCRIPT_GENERATION"
    assert overview["trusted_stage"] == "STAGE_01_SCRIPT_GENERATION"
    assert script_step["status"] == "generated"
    assert "已生成" in script_step["current_result"]
    assert "待用户确认" in script_step["current_result"]
    assert "Stage 02" in script_step["current_blocker"]
    assert script_step["next_action"] == "确认剧本内容。"


def test_sync_project_truth_marks_stage02_dispatch_failure_as_rerunnable(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "stage02_dispatch_stalled"
    (project_dir / "01_script").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_title": "雨夜便利店",
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_01_SCRIPT_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": False,
        "allowed_next_stage": "STAGE_02_STORYBOARD",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "01_script" / "script.json").write_text(json.dumps({
        "stage": "STAGE_01_SCRIPT_GENERATION",
        "project_id": project_dir.name,
        "title": "雨夜便利店门口",
        "status": "confirmed",
        "allowed_next_stage": "STAGE_02_STORYBOARD",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path

    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    overview = synced["creator_status_overview"]
    storyboard_step = next(step for step in overview["steps"] if step["step"] == "分镜")
    recommended = overview["recommended_entry"]
    assert overview["trusted_stage"] == "STAGE_01_SCRIPT_CONFIRMED"
    assert storyboard_step["status"] == "current"
    assert storyboard_step["current_result"] == "Stage 02 分镜尚未产出。"
    assert "还没完成" in storyboard_step["current_blocker"]
    assert storyboard_step["next_action"] == "重试 Stage 02 正式分镜生成。"
    assert "continue_pipeline.py" in storyboard_step["command"]
    assert recommended["label"] == "重试 Stage 02 正式分镜生成"
    assert "continue_pipeline.py" in recommended["command"]


def test_sync_project_truth_backfills_stage03_stage04_confirmation_when_stage05_is_confirmed(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "stage05_backfill_confirmation"
    (project_dir / "03_characters").mkdir(parents=True, exist_ok=True)
    (project_dir / "04_keyframes").mkdir(parents=True, exist_ok=True)
    (project_dir / "05_images").mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
        "status": "active",
        "brief_locked": True,
        "script_confirmed": True,
        "storyboard_confirmed": True,
        "character_bible_confirmed": False,
        "keyframe_prompts_confirmed": False,
        "keyframe_images_confirmed": True,
        "allowed_next_stage": "STAGE_06_VIDEO_CLIPS",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "03_characters" / "character_bible.json").write_text(json.dumps({
        "stage": "STAGE_03_CHARACTER_BIBLE",
        "status": "draft",
        "project_id": project_dir.name,
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "matches_storyboard": True,
            "ready_for_keyframe_stage": True,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "04_keyframes" / "keyframe_prompts.json").write_text(json.dumps({
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "status": "draft",
        "project_id": project_dir.name,
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "matches_storyboard": True,
            "uses_character_consistency": True,
            "covers_all_storyboard_shots": True,
            "ready_for_image_generation": True,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (project_dir / "05_images" / "keyframe_image_manifest.json").write_text(json.dumps({
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": project_dir.name,
        "image_provider_strategy": {"primary": "comfyui_txt2img", "fallback": ["manual"]},
        "jobs": [
            {
                "image_id": "IMG_S001_START",
                "provider": "comfyui_txt2img",
                "status": "succeeded",
                "evidence": {"file_exists": True, "file_size_bytes": 2048},
            }
        ],
        "quality_review": {"manual_review_cleared": True},
        "self_check": {
            "all_required_images_exist": True,
            "manual_review_cleared": True,
            "ready_for_video_clip_generation": True,
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    assert project_state.sync_project_manifest_truth(manifest_path) == manifest_path

    synced = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert synced["character_bible_confirmed"] is True
    assert synced["keyframe_prompts_confirmed"] is True
    overview = synced["creator_status_overview"]
    storyboard_step = next(step for step in overview["steps"] if step["step"] == "分镜")
    assert storyboard_step["status"] == "confirmed"
    assert storyboard_step["current_result"] == "分镜已确认。"
