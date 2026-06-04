#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_CORE = ROOT / "scripts" / "pipeline_core"
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
TEMPLATES = ROOT / "templates"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage05_quality_gates = load_module("stage05_quality_gates_test", PIPELINE_CORE / "stage05_quality_gates.py")
new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_quality_gate_test", IMAGES / "new_keyframe_image_jobs.py")


def test_scene_risk_tags_cover_many_prompt_families() -> None:
    scenarios = [
        ("cinematic beach walk at sunset", []),
        ("ancient Chinese woman holding one oil-paper umbrella in mist", ["umbrella_prop_contact"]),
        ("anime heroine gripping a katana in a duel stance", ["weapon_hand_contact"]),
        ("guofeng scholar opening a folding fan near the window", ["fan_hand_contact"]),
        ("young musician playing a bamboo flute under moonlight", ["instrument_hand_contact"]),
        ("realistic close-up of a hand offering a teacup", ["cup_hand_contact"]),
        ("romance poster, a couple holding hands while walking", ["two_subject_contact"]),
        ("cowgirl riding a horse across the field", ["riding_pose_contact"]),
    ]
    for prompt, expected_tags in scenarios:
        tags = stage05_quality_gates.scene_risk_tags_for_job({"prompt": prompt})
        assert tags == expected_tags, prompt


def test_build_quality_gate_skips_manual_review_when_structure_guided() -> None:
    prompt_only_gate = stage05_quality_gates.build_quality_gate({
        "prompt": "young musician playing a bamboo flute under moonlight",
        "comfyui_control_mode": "prompt_only",
    })
    assert prompt_only_gate["requires_manual_review"] is True
    assert prompt_only_gate["manual_review_status"] == "pending"

    pose_guided_gate = stage05_quality_gates.build_quality_gate({
        "prompt": "young musician playing a bamboo flute under moonlight",
        "comfyui_control_mode": "pose_guided",
    })
    assert pose_guided_gate["requires_manual_review"] is False
    assert pose_guided_gate["manual_review_status"] == "not_required"

    interaction_gate = stage05_quality_gates.build_quality_gate({
        "prompt": "young woman handing the only umbrella to another person in the rain",
        "comfyui_control_mode": "reference_guided",
        "stage06_route_hint": "interaction_handoff",
    })
    assert interaction_gate["requires_manual_review"] is True
    assert interaction_gate["manual_review_status"] == "pending"


def test_build_quality_gate_exposes_creator_repair_suggestions_and_auto_repair_plan() -> None:
    job = {
        "image_id": "IMG_UMBRELLA",
        "prompt": "ancient Chinese woman holding one oil-paper umbrella in mist",
        "comfyui_control_mode": "prompt_only",
    }
    gate = stage05_quality_gates.build_quality_gate(job)
    assert gate["auto_repair_recommended"] is True
    assert "多手" in gate["creator_risk_summary"]
    assert len(gate["creator_repair_suggestions"]) >= 2
    assert gate["review_priority_label"] == "高优先级复核"
    assert gate["review_priority_score"] >= 90
    assert len(gate["review_checklist"]) == 3
    assert "先查伞的数量" in gate["review_focus"]

    plan = stage05_quality_gates.build_auto_repair_plan(job, gate)
    assert plan["enabled"] is True
    assert plan["mode"] == "two_pass_prompt_repair"
    assert plan["pass_count"] == 2
    assert "umbrella_prop_contact" in plan["target_failure_modes"]
    assert any("one umbrella only" in item for item in plan["repair_prompt_sections"])
    assert any("duplicate umbrella" in item.lower() for item in plan["repair_negative_hints"])

    creator_review_card = stage05_quality_gates.build_creator_review_card(job, gate, auto_repair_status="auto_second_pass_succeeded")
    assert creator_review_card is not None
    assert creator_review_card["priority_label"] == "高优先级复核"
    assert creator_review_card["auto_repair_status"] == "auto_second_pass_succeeded"
    assert len(creator_review_card["checklist"]) == 3


def test_build_auto_repair_plan_enables_reference_guided_second_pass_for_interaction_handoff() -> None:
    job = {
        "image_id": "IMG_S001_MID",
        "prompt": "young woman handing the only umbrella to another person in the rain",
        "comfyui_control_mode": "reference_guided",
        "stage06_route_hint": "interaction_handoff",
    }
    gate = stage05_quality_gates.build_quality_gate(job)
    plan = stage05_quality_gates.build_auto_repair_plan(job, gate)
    assert gate["requires_manual_review"] is True
    assert plan["enabled"] is True
    assert plan["mode"] == "two_pass_reference_guided_repair"
    assert plan["pass_count"] == 2
    assert "umbrella_prop_contact" in plan["target_failure_modes"]


def test_summarize_quality_review_counts_mixed_scene_matrix() -> None:
    jobs = [
        {"image_id": "IMG_SAFE", "prompt": "cinematic beach walk at sunset", "comfyui_control_mode": "prompt_only"},
        {"image_id": "IMG_UMBRELLA", "prompt": "ancient woman holding one oil-paper umbrella", "comfyui_control_mode": "prompt_only"},
        {"image_id": "IMG_SWORD", "prompt": "hero gripping a katana", "comfyui_control_mode": "prompt_only"},
        {"image_id": "IMG_FLUTE", "prompt": "musician playing a bamboo flute", "comfyui_control_mode": "pose_guided"},
        {
            "image_id": "IMG_CUP",
            "prompt": "close-up hand holding a teacup",
            "comfyui_control_mode": "prompt_only",
            "quality_gate": {"manual_review_status": "approved"},
        },
    ]
    summary = stage05_quality_gates.summarize_quality_review(jobs)
    assert summary["risky_image_count"] == 4
    assert summary["required_count"] == 3
    assert summary["approved_count"] == 1
    assert summary["pending_count"] == 2
    assert summary["blocking_image_ids"] == ["IMG_UMBRELLA", "IMG_SWORD"]
    assert summary["manual_review_cleared"] is False
    assert "高风险镜头已进入人工复核队列" in summary["creator_feedback_headline"]
    assert summary["next_review_image_ids"][:2] == ["IMG_UMBRELLA", "IMG_SWORD"]
    assert summary["review_queue"][0]["priority_label"] == "高优先级复核"
    assert summary["review_queue"][0]["checklist"]
    assert len(summary["top_review_cards"]) == 2
    assert summary["top_review_cards"][0]["image_id"] == "IMG_UMBRELLA"
    assert summary["top_review_cards"][0]["quick_fix"]


def test_new_keyframe_image_jobs_builds_risk_matrix_for_many_scene_types(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260530_stage05_scene_matrix"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T21:00:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = [
        {
            "shot_id": "S001",
            "start_keyframe_prompt": "cinematic beach walk at sunset",
            "end_keyframe_prompt": "the same woman looks back at the sea",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same woman",
            "style_prompt": "warm realism",
            "camera_prompt": "wide shot",
        },
        {
            "shot_id": "S002",
            "start_keyframe_prompt": "ancient Chinese woman holding one oil-paper umbrella in mist",
            "end_keyframe_prompt": "the same woman turns with the same oil-paper umbrella",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same woman, same umbrella",
            "style_prompt": "guofeng ink wash",
            "camera_prompt": "medium shot",
        },
        {
            "shot_id": "S003",
            "start_keyframe_prompt": "anime heroine gripping a katana in a duel stance",
            "end_keyframe_prompt": "the same heroine lowers the katana slightly",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same heroine, same katana",
            "style_prompt": "anime action illustration",
            "camera_prompt": "dynamic medium shot",
        },
        {
            "shot_id": "S004",
            "start_keyframe_prompt": "guofeng scholar opening a folding fan near the window",
            "end_keyframe_prompt": "the same scholar half-closes the folding fan",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same scholar, same fan",
            "style_prompt": "poetic guofeng illustration",
            "camera_prompt": "mid shot",
        },
        {
            "shot_id": "S005",
            "start_keyframe_prompt": "young musician playing a bamboo flute under moonlight",
            "end_keyframe_prompt": "the same musician lowers the bamboo flute slightly",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same musician, same flute",
            "style_prompt": "guofeng moonlit scene",
            "camera_prompt": "medium close-up",
        },
        {
            "shot_id": "S006",
            "start_keyframe_prompt": "realistic close-up of a hand offering a teacup",
            "end_keyframe_prompt": "the same hand steadies the teacup on a tray",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same hand, same teacup",
            "style_prompt": "refined realistic still",
            "camera_prompt": "insert close-up",
        },
        {
            "shot_id": "S007",
            "start_keyframe_prompt": "romance poster, a couple holding hands while walking",
            "end_keyframe_prompt": "the same couple keeps holding hands and turns toward camera",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same couple",
            "style_prompt": "romantic poster art",
            "camera_prompt": "medium wide shot",
        },
        {
            "shot_id": "S008",
            "start_keyframe_prompt": "cowgirl riding a horse across the field",
            "end_keyframe_prompt": "the same rider keeps riding the horse while pulling it to a gentle stop",
            "negative_prompt": "low resolution",
            "consistency_prompt": "same rider, same horse",
            "style_prompt": "cinematic western still",
            "camera_prompt": "wide action shot",
        },
    ]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert manifest["quality_review"]["risky_image_count"] == 14
    assert manifest["quality_review"]["required_count"] == 0
    assert manifest["quality_review"]["pending_count"] == 0
    assert manifest["quality_review"]["manual_review_cleared"] is True
    assert len(manifest["quality_review"]["review_queue"]) == 0
    assert manifest["quality_review"]["next_review_image_ids"] == []
    assert len(manifest["quality_review"]["top_review_cards"]) == 0
    assert manifest["self_check"]["manual_review_cleared"] is True
    assert manifest["allowed_next_stage"] is None

    risk_tags = {tag for job in manifest["jobs"] for tag in job["quality_gate"]["risk_tags"]}
    assert risk_tags == {
        "umbrella_prop_contact",
        "weapon_hand_contact",
        "fan_hand_contact",
        "instrument_hand_contact",
        "cup_hand_contact",
        "two_subject_contact",
        "riding_pose_contact",
    }
    safe_jobs = [job for job in manifest["jobs"] if job["shot_id"] == "S001"]
    assert all(job["quality_gate"]["requires_manual_review"] is False for job in safe_jobs)
    manual_review_text = (images_dir / "manual_review.md").read_text(encoding="utf-8")
    assert "# Stage 05 Manual Review" in manual_review_text
    assert "待人工复核数：0" in manual_review_text
    assert "当前没有高风险镜头" in manual_review_text
    prompt_patch_plan = json.loads((images_dir / "prompt_patch_plan.json").read_text(encoding="utf-8"))
    assert prompt_patch_plan["patch_count"] == 0
    assert prompt_patch_plan["queue_patch_count"] == 0
    assert len(prompt_patch_plan["all_prompt_patches"]) == 0
    assert prompt_patch_plan["top_prompt_patches"] == []
    prompt_patch_cards = (images_dir / "prompt_patch_cards.md").read_text(encoding="utf-8")
    assert "# Stage 05 Prompt Patch Cards" in prompt_patch_cards
    assert "当前没有需要生成 prompt patch 的高风险镜头" in prompt_patch_cards
