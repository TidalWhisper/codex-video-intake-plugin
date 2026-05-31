#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import threading
from pathlib import Path
from types import ModuleType
from urllib.parse import quote
from urllib import request

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "skills" / "video-project-intake" / "scripts"
SCRIPT = ROOT / "skills" / "video-script-generation" / "scripts"
STORYBOARD = ROOT / "skills" / "video-storyboard-generation" / "scripts"
PIPELINE = ROOT / "skills" / "video-production-pipeline" / "scripts"
CHARACTER = ROOT / "skills" / "video-character-bible" / "scripts"
KEYFRAME = ROOT / "skills" / "video-keyframe-prompts" / "scripts"
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
VIDEOCLIPS = ROOT / "skills" / "video-video-clips" / "scripts"
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


create_project_folder = load_module("create_project_folder_for_test", INTAKE / "create_project_folder.py")
new_project_brief_template = load_module("new_project_brief_template_for_test", INTAKE / "new_project_brief_template.py")
lock_project_brief = load_module("lock_project_brief_for_test", INTAKE / "lock_project_brief.py")
validate_project_brief = load_module("validate_project_brief", INTAKE / "validate_project_brief.py")
validate_project_structure = load_module("validate_project_structure_for_test", INTAKE / "validate_project_structure.py")
new_script_template = load_module("new_script_template_for_test", SCRIPT / "new_script_template.py")
validate_script = load_module("validate_script_for_test", SCRIPT / "validate_script.py")
new_storyboard_template = load_module("new_storyboard_template_for_test", STORYBOARD / "new_storyboard_template.py")
validate_storyboard = load_module("validate_storyboard_for_test", STORYBOARD / "validate_storyboard.py")
new_character_bible_template = load_module("new_character_bible_template_for_test", CHARACTER / "new_character_bible_template.py")
validate_character_bible = load_module("validate_character_bible_for_test", CHARACTER / "validate_character_bible.py")
new_keyframe_prompts_template = load_module("new_keyframe_prompts_template_for_test", KEYFRAME / "new_keyframe_prompts_template.py")
validate_keyframe_prompts = load_module("validate_keyframe_prompts_for_test", KEYFRAME / "validate_keyframe_prompts.py")
new_keyframe_image_jobs = load_module("new_keyframe_image_jobs_for_test", IMAGES / "new_keyframe_image_jobs.py")
validate_keyframe_image_manifest = load_module("validate_keyframe_image_manifest_for_test", IMAGES / "validate_keyframe_image_manifest.py")
generate_placeholder_keyframe_images = load_module("generate_placeholder_keyframe_images_for_test", IMAGES / "generate_placeholder_keyframe_images.py")
sync_keyframe_image_manifest = load_module("sync_keyframe_image_manifest_for_test", IMAGES / "sync_keyframe_image_manifest.py")
rerun_top_prompt_patches = load_module("rerun_top_prompt_patches_for_test", IMAGES / "rerun_top_prompt_patches.py")
approve_stage05_review_queue = load_module("approve_stage05_review_queue_for_test", IMAGES / "approve_stage05_review_queue.py")
serve_stage05_review_workbench = load_module("serve_stage05_review_workbench_for_test", IMAGES / "serve_stage05_review_workbench.py")
new_video_clip_jobs = load_module("new_video_clip_jobs_for_test", VIDEOCLIPS / "new_video_clip_jobs.py")
validate_video_clip_manifest = load_module("validate_video_clip_manifest_for_test", VIDEOCLIPS / "validate_video_clip_manifest.py")
generate_placeholder_video_clips = load_module("generate_placeholder_video_clips_for_test", VIDEOCLIPS / "generate_placeholder_video_clips.py")
sync_video_clip_manifest = load_module("sync_video_clip_manifest_for_test", VIDEOCLIPS / "sync_video_clip_manifest.py")
new_audio_jobs = load_module("new_audio_jobs_for_test", AUDIO / "new_audio_jobs.py")
validate_audio_manifest = load_module("validate_audio_manifest_for_test", AUDIO / "validate_audio_manifest.py")
generate_placeholder_audio = load_module("generate_placeholder_audio_for_test", AUDIO / "generate_placeholder_audio.py")
sync_audio_manifest = load_module("sync_audio_manifest_for_test", AUDIO / "sync_audio_manifest.py")
new_assembly_manifest = load_module("new_assembly_manifest_for_test", ASSEMBLY / "new_assembly_manifest.py")
validate_assembly_manifest = load_module("validate_assembly_manifest_for_test", ASSEMBLY / "validate_assembly_manifest.py")
assemble_with_ffmpeg = load_module("assemble_with_ffmpeg_for_test", ASSEMBLY / "assemble_with_ffmpeg.py")
sync_assembly_manifest = load_module("sync_assembly_manifest_for_test", ASSEMBLY / "sync_assembly_manifest.py")
new_qa_manifest = load_module("new_qa_manifest_for_test", QA / "new_qa_manifest.py")
validate_qa_manifest = load_module("validate_qa_manifest_for_test", QA / "validate_qa_manifest.py")
package_delivery = load_module("package_delivery_for_test", QA / "package_delivery.py")
update_project_manifest = load_module("update_project_manifest_for_test", PIPELINE / "update_project_manifest.py")
show_creator_home = load_module("show_creator_home_for_test", PIPELINE / "show_creator_home.py")


def load_example_brief() -> dict:
    return json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))


def load_rainy_store_brief(project_dir: Path) -> dict:
    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T14:20:12+08:00",
    })
    brief["user_answers"] = {
        "idea": "一位20岁出头的女孩在雨夜便利店门口把最后一把伞留给陌生人，自己淋着雨走远，回头发现门口多了一杯热可可",
        "target_duration": "12秒",
        "genre": "治愈",
        "style": "写实电影感",
        "visual_spec": "9:16 竖屏 1080P",
        "characters": "有固定主角/人物",
        "voice": "只需要旁白",
        "music": "需要 underscore",
        "final_output": "合成粗剪成片",
    }
    brief["normalized"].update({
        "idea": "一位20岁出头的女孩在雨夜便利店门口把最后一把伞留给陌生人，自己淋着雨走远，回头发现门口多了一杯热可可",
        "target_duration_sec": 12,
        "target_duration_label": "12秒",
        "genre": "治愈",
        "style": "写实电影感",
        "aspect_ratio": "9:16",
        "aspect_ratio_label": "9:16 竖屏",
        "resolution": "1080P",
        "resolution_label": "1080P",
        "characters_mode": "有固定主角/人物",
        "characters_required": True,
        "voice_mode": "只需要旁白",
        "voice_required": True,
        "music_mode": "需要",
        "music_profile": "underscore",
        "music_required": True,
        "final_output": "合成粗剪成片",
    })
    return brief


def test_validate_project_brief_example() -> None:
    data = load_example_brief()
    ok, errors, warnings = validate_project_brief.validate(data, TEMPLATES / "project_brief.draft.example.json")
    assert ok, errors
    assert data["normalized"]["music_profile"] == "underscore"


def test_new_project_brief_template_generates_schema_compliant_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_INTAKE",
        "brief_locked": False,
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    draft_path = intake_dir / "project_brief.draft.json"
    assert new_project_brief_template.main(["new_project_brief_template.py", str(draft_path)]) == 0

    data = json.loads(draft_path.read_text(encoding="utf-8"))
    assert data["project_id"] == project_dir.name
    assert data["project_dir"] == str(project_dir).replace("\\", "/")
    ok, errors, warnings = validate_project_brief.validate(data, draft_path)
    assert ok, errors


def test_create_project_folder_uses_readable_slug_for_chinese_numeric_title(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", [
        "create_project_folder.py",
        "--root",
        str(tmp_path / "video_projects"),
        "--title",
        "一位20岁出头的女孩在落日余辉的海滩边散步",
    ])
    assert create_project_folder.main() == 0
    projects = list((tmp_path / "video_projects").iterdir())
    assert len(projects) == 1
    project_dir = projects[0]
    assert not project_dir.name.endswith("_20")
    assert not project_dir.name.endswith("_project")
    assert any("\u4e00" <= ch <= "\u9fff" for ch in project_dir.name.rsplit("_", 1)[-1])
    manifest = json.loads((project_dir / "project_manifest.json").read_text(encoding="utf-8"))
    assert manifest["project_title"] == "一位20岁出头的女孩在落日余辉的海滩边散步"
    assert validate_project_structure.main(["validate_project_structure.py", str(project_dir)]) == 0


def test_project_brief_must_match_containing_project_folder(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", [
        "create_project_folder.py",
        "--root",
        str(tmp_path / "video_projects"),
        "--project-id",
        "video_20260528_103000_sunset_beach_girl",
    ])
    assert create_project_folder.main() == 0
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    draft_path = project_dir / "00_intake" / "project_brief.draft.json"

    data = load_example_brief()
    data["project_id"] = project_dir.name
    data["project_dir"] = str(project_dir).replace("\\", "/")
    draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    ok, errors, warnings = validate_project_brief.validate(data, draft_path)
    assert ok, errors

    data["project_id"] = "video_wrong_project"
    draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    ok, errors, warnings = validate_project_brief.validate(data, draft_path)
    assert not ok
    assert any("containing project folder" in e or "basename of project_dir" in e for e in errors)


def test_validate_project_brief_accepts_utf8_bom(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_INTAKE",
        "brief_locked": False,
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    draft = load_example_brief()
    draft["project_id"] = project_dir.name
    draft["project_dir"] = str(project_dir).replace("\\", "/")
    draft_path = intake_dir / "project_brief.draft.json"
    draft_path.write_text("\ufeff" + json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

    assert validate_project_brief.main(["validate_project_brief.py", str(draft_path)]) == 0


def test_validate_script_example_final() -> None:
    data = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_script.validate(data, mode="final")
    assert ok, errors


def test_new_script_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0

    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    assert script_data["script"]["music_profile"] == "underscore"
    ok, errors, warnings = validate_script.validate(script_data, mode="draft")
    assert ok, errors
    ok, errors, warnings = validate_script.validate(script_data, mode="final")
    assert ok, errors
    assert script_data["title"]
    assert script_data["duration_plan"]["beats"]
    assert script_data["script"]["sections"]
    assert (script_dir / "story_direction.md").exists()
    assert (script_dir / "story_direction.json").exists()
    assert (script_dir / "plot_structure.md").exists()
    assert (script_dir / "plot_structure.json").exists()
    assert (script_dir / "script.md").exists()
    assert (script_dir / "script_review.md").exists()

def test_validate_storyboard_example_final() -> None:
    data = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_storyboard.validate(data, mode="final")
    assert ok, errors


def test_new_storyboard_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.3.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard_json = storyboard_dir / "storyboard.json"
    assert new_storyboard_template.main(["new_storyboard_template.py", str(locked_brief), str(script_json), str(storyboard_json)]) == 0

    storyboard_data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_storyboard.validate(storyboard_data, mode="draft")
    assert ok, errors
    ok, errors, warnings = validate_storyboard.validate(storyboard_data, mode="final")
    assert ok, errors
    assert storyboard_data["shots"]
    assert storyboard_data["shot_count"] == len(storyboard_data["shots"])
    assert (storyboard_dir / "storyboard.md").exists()
    assert (storyboard_dir / "storyboard_review.md").exists()



def test_validate_character_bible_example_final() -> None:
    data = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_character_bible.validate(data, mode="final")
    assert ok, errors


def test_new_character_bible_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    character_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.4.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character_json = character_dir / "character_bible.json"
    assert new_character_bible_template.main(["new_character_bible_template.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json)]) == 0

    character_data = json.loads(character_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_character_bible.validate(character_data, mode="draft")
    assert ok, errors
    ok, errors, warnings = validate_character_bible.validate(character_data, mode="final")
    assert ok, errors
    assert character_data["characters"]
    assert "performance_profile" in character_data["characters"][0]
    assert character_data["reference_image_status"]["all_present"] is False
    assert character_data["stage05_execution_readiness"]["safe_to_auto_generate"] is False
    assert character_data["self_check"]["reference_images_ready"] is False
    assert (character_dir / "character_bible.md").exists()
    assert (character_dir / "character_review.md").exists()
    assert (character_dir / "reference_image_plan.json").exists()
    assert (character_dir / "reference_image_start_here.md").exists()
    review_text = (character_dir / "character_review.md").read_text(encoding="utf-8")
    reference_start_here = (character_dir / "reference_image_start_here.md").read_text(encoding="utf-8")
    assert "角色参考图就绪：否" in review_text
    assert "CHAR_001_primary.png" in review_text
    assert "角色参考图补齐入口" in reference_start_here
    assert "03_characters/reference_images/CHAR_001_primary.png" in reference_start_here

def test_update_project_manifest_sets_pipeline_flags(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    project_dir.mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", [
        "update_project_manifest.py",
        str(project_dir),
        "--stage", "STAGE_01_SCRIPT_CONFIRMED",
        "--script-confirmed", "true",
        "--allowed-next-stage", "STAGE_02_STORYBOARD",
        "--character-bible-confirmed", "false",
        "--keyframe-prompts-confirmed", "true",
        "--keyframe-images-confirmed", "false",
        "--video-clips-confirmed", "true",
        "--audio-confirmed", "true",
        "--assembly-confirmed", "false",
    ])
    assert update_project_manifest.main() == 0
    data = json.loads((project_dir / "project_manifest.json").read_text(encoding="utf-8"))
    assert data["current_stage"] == "STAGE_01_SCRIPT_CONFIRMED"
    assert data["script_confirmed"] is True
    assert data["allowed_next_stage"] == "STAGE_02_STORYBOARD"
    assert data["character_bible_confirmed"] is False


def test_show_creator_home_points_to_reference_recovery_or_workbench(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "video_projects" / "creator_status_demo"
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

    assert show_creator_home.main(["--project-dir", str(project_dir)]) == 0
    output = capsys.readouterr().out
    assert "CREATOR_HOME_READY" in output
    assert "RECOMMENDED_ENTRY_LABEL: 打开角色参考图说明" in output
    assert "03_characters/reference_image_start_here.md" in output



def test_validate_keyframe_prompts_example_final() -> None:
    data = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_prompts.validate(data, mode="final")
    assert ok, errors


def test_new_keyframe_prompts_template_generates_final_ready_draft(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    intake_dir.mkdir(parents=True)
    script_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    character_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script["source_brief"] = str(locked_brief).replace("\\", "/")
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard["source_brief"] = str(locked_brief).replace("\\", "/")
    storyboard["source_script"] = str(script_json).replace("\\", "/")
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character["source_brief"] = str(locked_brief).replace("\\", "/")
    character["source_script"] = str(script_json).replace("\\", "/")
    character["source_storyboard"] = str(storyboard_json).replace("\\", "/")
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert new_keyframe_prompts_template.main([
        "new_keyframe_prompts_template.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(keyframe_json)
    ]) == 0

    keyframe_data = json.loads(keyframe_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_prompts.validate(keyframe_data, mode="draft")
    assert ok, errors
    assert len(keyframe_data["shot_prompts"]) == len(storyboard["shots"])
    ok, errors, warnings = validate_keyframe_prompts.validate(keyframe_data, mode="final")
    assert ok, errors
    assert keyframe_data["transition_prompts"]
    assert keyframe_data["shot_prompts"][0]["performance_prompt"]
    assert keyframe_data["reference_image_status"]["all_present"] is False
    assert keyframe_data["stage05_execution_readiness"]["safe_to_auto_generate"] is False
    assert keyframe_data["self_check"]["character_reference_images_ready"] is False
    assert (keyframe_dir / "keyframe_prompts.md").exists()
    assert (keyframe_dir / "motion_prompts.json").exists()
    assert (keyframe_dir / "prompt_review.md").exists()
    assert (keyframe_dir / "stage05_start_here.md").exists()
    prompt_review_text = (keyframe_dir / "prompt_review.md").read_text(encoding="utf-8")
    stage05_start_here = (keyframe_dir / "stage05_start_here.md").read_text(encoding="utf-8")
    assert "角色参考图就绪：否" in prompt_review_text
    assert "CHAR_001_primary.png" in prompt_review_text
    assert "03_characters/reference_image_start_here.md" in stage05_start_here


def test_rainy_store_story_anchors_survive_stage01_to_stage04(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "creator_trial_20260530_rainy_store"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief = load_rainy_store_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0
    storyboard_json = storyboard_dir / "storyboard.json"
    assert new_storyboard_template.main(["new_storyboard_template.py", str(locked_brief), str(script_json), str(storyboard_json)]) == 0
    character_json = character_dir / "character_bible.json"
    assert new_character_bible_template.main([
        "new_character_bible_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
    ]) == 0
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert new_keyframe_prompts_template.main([
        "new_keyframe_prompts_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(keyframe_json),
    ]) == 0

    script_data = json.loads(script_json.read_text(encoding="utf-8"))
    storyboard_data = json.loads(storyboard_json.read_text(encoding="utf-8"))
    character_data = json.loads(character_json.read_text(encoding="utf-8"))
    keyframe_data = json.loads(keyframe_json.read_text(encoding="utf-8"))

    assert script_data["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert script_data["story_anchors"]["key_props"][:2] == ["最后一把伞", "热可可"]
    script_text = (script_dir / "script.md").read_text(encoding="utf-8")
    assert "雨夜便利店门口" in script_text
    assert "最后一把伞" in script_text
    assert "热可可" in script_text
    assert "核心场景" not in script_text
    assert "海边女孩" not in script_text

    joined_storyboard = "\n".join(
        f"{shot.get('scene')} {shot.get('composition')} {shot.get('action')} {shot.get('key_prop')}"
        for shot in storyboard_data["shots"]
    )
    assert "雨夜便利店门口" in joined_storyboard
    assert "最后一把伞" in joined_storyboard
    assert "热可可" in joined_storyboard
    assert storyboard_data["shots"][0]["location"] == "便利店门口"
    assert storyboard_data["shots"][0]["weather"] == "雨夜"

    assert character_data["characters"][0]["name"] == "20岁出头的女孩"
    assert "最后一把伞" in character_data["characters"][0]["appearance"]["accessories"]

    prompt_text = (keyframe_dir / "keyframe_prompts.md").read_text(encoding="utf-8")
    assert "地点：便利店门口" in prompt_text
    assert "天气：雨夜" in prompt_text
    assert "关键道具：最后一把伞" in prompt_text
    assert "关键道具：热可可" in prompt_text
    assert "构图重点：" in prompt_text
    assert "镜头意图：" in prompt_text
    assert all(shot.get("intent_summary") for shot in keyframe_data["shot_prompts"])
    assert all("地点：" in shot["scene_summary"] for shot in keyframe_data["shot_prompts"])
    assert all("天气：" in shot["scene_summary"] for shot in keyframe_data["shot_prompts"])
    assert "Character identity anchor:" in keyframe_data["shot_prompts"][0]["consistency_prompt"]
    assert "Primary protagonist must remain 20岁出头的女孩" in keyframe_data["shot_prompts"][0]["start_keyframe_prompt"]
    assert "do not swap protagonist identity" in keyframe_data["shot_prompts"][0]["end_keyframe_prompt"]


def test_rainy_store_story_anchors_survive_stage06_to_stage08_and_tiny_rough_cut_cannot_pass(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "creator_trial_20260530_rainy_store"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assembly_dir = project_dir / "08_assembly"
    for path in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir, images_dir, video_dir, audio_dir, assembly_dir]:
        path.mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_04_KEYFRAME_PROMPTS_GENERATION",
        "status": "active",
        "brief_locked": True,
        "keyframe_images_confirmed": True,
        "video_clips_confirmed": True,
        "audio_confirmed": True,
        "assembly_confirmed": True,
        "allowed_next_stage": "STAGE_09_QA",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    brief = load_rainy_store_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script_json = script_dir / "script.json"
    assert new_script_template.main(["new_script_template.py", str(locked_brief), str(script_json)]) == 0
    storyboard_json = storyboard_dir / "storyboard.json"
    assert new_storyboard_template.main(["new_storyboard_template.py", str(locked_brief), str(script_json), str(storyboard_json)]) == 0
    character_json = character_dir / "character_bible.json"
    assert new_character_bible_template.main([
        "new_character_bible_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
    ]) == 0
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    assert new_keyframe_prompts_template.main([
        "new_keyframe_prompts_template.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(keyframe_json),
    ]) == 0

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    image_manifest = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    first_shot_jobs = [job for job in image_manifest["jobs"] if job["shot_id"] == "S001"]
    assert any("missing_character_reference" in (job.get("quality_gate") or {}).get("risk_tags", []) for job in first_shot_jobs)
    assert any("Character identity anchor:" in job.get("consistency_prompt", "") for job in first_shot_jobs)
    for job in image_manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(image_manifest_json), "--provider", "openai_image"]
        assert sync_keyframe_image_manifest.main() == 0
        sys.argv = [
            "approve_stage05_review_queue.py",
            str(image_manifest_json),
            "--all-pending",
            "--content-aligned",
            "--content-alignment-note",
            "Rainy store creator sample approved after Stage 05 review workbench inspection.",
        ]
        assert approve_stage05_review_queue.main() == 0
    finally:
        sys.argv = old_argv

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0
    clip_manifest = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    clip_text = json.dumps(clip_manifest, ensure_ascii=False)
    assert "雨夜便利店门口" in clip_text
    assert "最后一把伞" in clip_text
    assert "热可可" in clip_text
    assert "海边女孩" not in clip_text
    assert "核心场景" not in clip_text
    for job in clip_manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42REALCLIP" + (b"0" * 512))
        job["status"] = "succeeded"
        job["provider"] = "comfyui_ltx_i2v"
    clip_manifest_json.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_video_clip_manifest.py", str(clip_manifest_json)]
        assert sync_video_clip_manifest.main() == 0
    finally:
        sys.argv = old_argv

    audio_manifest_json = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main([
        "new_audio_jobs.py",
        str(locked_brief),
        str(script_json),
        str(storyboard_json),
        str(character_json),
        str(clip_manifest_json),
        str(audio_manifest_json),
    ]) == 0
    audio_manifest = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    audio_text = json.dumps(audio_manifest, ensure_ascii=False)
    assert "雨夜便利店门口" in audio_text
    assert "热可可" in audio_text
    assert "海边女孩" not in audio_text
    assert "核心场景" not in audio_text
    voiceovers = [job for job in audio_manifest["jobs"] if job["audio_type"] == "voiceover"]
    assert voiceovers
    assert all(job["speaker_name"] == "旁白" for job in voiceovers)
    for job in audio_manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"audio-output")
        job["status"] = "succeeded"
        job["provider"] = "manual"
    audio_manifest_json.write_text(json.dumps(audio_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        sys.argv = ["sync_audio_manifest.py", str(audio_manifest_json)]
        assert sync_audio_manifest.main() == 0
    finally:
        sys.argv = old_argv

    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assert new_assembly_manifest.main([
        "new_assembly_manifest.py",
        str(locked_brief),
        str(storyboard_json),
        str(clip_manifest_json),
        str(audio_manifest_json),
        str(assembly_manifest_json),
    ]) == 0
    assembly_manifest = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
    assembly_text = json.dumps(assembly_manifest, ensure_ascii=False)
    assert "雨夜便利店门口" in assembly_text
    assert "热可可" in assembly_text
    assert "海边女孩" not in assembly_text
    assert "核心场景" not in assembly_text

    rough_cut_path = project_dir / "08_assembly" / "rough_cut" / "rough_cut.mp4"
    rough_cut_path.parent.mkdir(parents=True, exist_ok=True)
    rough_cut_path.write_bytes(b"\x00\x00\x00\x18ftypmp42tiny")
    assembly_manifest["assembly_provider"] = "ffmpeg"
    assembly_manifest["ffmpeg_commands"] = [{
        "command": ["ffmpeg"],
        "provider": "ffmpeg",
        "strategy": "reencode_mix",
        "return_code": 0,
        "stdout_excerpt": "",
        "stderr_excerpt": "",
        "ran_at": "2026-05-30T00:00:00+00:00",
    }]
    assembly_manifest_json.write_text(json.dumps(assembly_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        sys.argv = ["sync_assembly_manifest.py", str(assembly_manifest_json)]
        assert sync_assembly_manifest.main() == 0
    finally:
        sys.argv = old_argv

        synced_assembly = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
        assert synced_assembly["self_check"]["ready_for_qa_stage"] is False
        assert synced_assembly["allowed_next_stage"] is None
        project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert project_manifest["current_stage"] == "STAGE_08_ASSEMBLY"
        assert project_manifest["keyframe_images_confirmed"] is True
        assert project_manifest["video_clips_confirmed"] is True
        assert project_manifest["audio_confirmed"] is True
        assert project_manifest["assembly_confirmed"] is False

def test_stage06_stays_draft_only_when_stage05_manual_review_not_cleared(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_stage06_draft_only_gate"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for path in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        path.mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "active",
        "brief_locked": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T12:00:00+08:00",
    })
    brief["user_answers"]["final_output"] = "生成视频片段素材包"
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps({
        "stage": "STAGE_02_STORYBOARD_GENERATION",
        "project_id": project_dir.name,
        "shots": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "scene": "雨夜便利店门口",
            "location": "便利店门口",
            "weather": "雨夜",
            "key_prop": "最后一把伞",
            "action": "女孩把最后一把伞递给陌生人",
            "emotion": "克制善意",
        }],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    prompts_json = keyframe_dir / "keyframe_prompts.json"
    prompts_json.write_text(json.dumps({
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "project_id": project_dir.name,
        "shot_prompts": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "motion_prompt": "完成一次清晰的递伞动作",
            "negative_prompt": "多手，重复道具",
        }],
        "global_negative_prompt": "多手，重复道具",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    start_image = images_dir / "S001_start.png"
    end_image = images_dir / "S001_end.png"
    start_image.write_bytes(b"png-start")
    end_image.write_bytes(b"png-end")
    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    image_manifest_json.write_text(json.dumps({
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": project_dir.name,
        "image_provider_strategy": {"primary": "openai_image", "fallback": ["comfyui", "manual"]},
        "jobs": [
            {
                "image_id": "IMG_S001_START",
                "shot_id": "S001",
                "frame_role": "start",
                "output_path": str(start_image).replace("\\", "/"),
                "provider": "openai_image",
                "evidence": {"file_path": str(start_image).replace("\\", "/"), "file_exists": True, "file_size_bytes": start_image.stat().st_size},
            },
            {
                "image_id": "IMG_S001_END",
                "shot_id": "S001",
                "frame_role": "end",
                "output_path": str(end_image).replace("\\", "/"),
                "provider": "openai_image",
                "evidence": {"file_path": str(end_image).replace("\\", "/"), "file_exists": True, "file_size_bytes": end_image.stat().st_size},
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

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(prompts_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0

    planned = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert planned["planning_overrides"]["stage05_gate_ready_for_stage06"] is False
    assert planned["formal_promotion_status"] == "draft_only"
    assert any("Stage 05 review is not cleared yet" in item for item in planned["self_check"]["notes"])

    for job in planned["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42REALCLIP" + (b"0" * 512))
        job["status"] = "succeeded"
        job["provider"] = "comfyui_ltx_i2v"
    clip_manifest_json.write_text(json.dumps(planned, ensure_ascii=False, indent=2), encoding="utf-8")

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_video_clip_manifest.py", str(clip_manifest_json)]
        assert sync_video_clip_manifest.main() == 0
    finally:
        sys.argv = old_argv

    synced = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert synced["self_check"]["all_required_clips_exist"] is True
    assert synced["self_check"]["ready_for_audio_stage"] is False
    assert synced["self_check"]["formal_progression_ready"] is False
    assert synced["allowed_next_stage"] is None
    assert synced["formal_promotion_status"] == "draft_only"
    assert any("formal_progression_blocker:" in item for item in synced["self_check"]["notes"])

    project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert project_manifest["current_stage"] == "STAGE_05_KEYFRAME_IMAGES"
    assert project_manifest["video_clips_confirmed"] is False


def test_lock_project_brief_derives_routing_and_updates_manifest(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_INTAKE",
        "brief_locked": False,
        "allowed_next_stage": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    draft = load_example_brief()
    draft["project_id"] = project_dir.name
    draft["project_dir"] = str(project_dir).replace("\\", "/")
    draft["status"] = "draft"
    draft["confirmed_by_user"] = False
    draft["normalized"]["final_output"] = "只要剧本"
    draft_path = intake_dir / "project_brief.draft.json"
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    locked_path = intake_dir / "project_brief.locked.json"

    assert lock_project_brief.main(["lock_project_brief.py", str(draft_path), str(locked_path)]) == 0
    locked = json.loads(locked_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert locked["routing"]["requested_output_scope"] == "script_only"
    assert locked["routing"]["requested_terminal_stage"] == "STAGE_01_SCRIPT_CONFIRMED"
    assert locked["compiled_requirements"]["requested_output_scope"] == "script_only"
    assert locked["quality_contract"]["project_shape"] == locked["compiled_requirements"]["project_shape"]
    assert locked["quality_contract"]["axes"]
    assert manifest["requested_terminal_stage"] == "STAGE_01_SCRIPT_CONFIRMED"
    assert manifest["compiled_requirements"]["requested_output_scope"] == "script_only"
    assert manifest["quality_contract"]["axes"]


def test_stage05_compiler_keeps_openai_first_for_anime_projects(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_anime_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["genre"] = "动漫短片"
    brief["normalized"]["style"] = "日系动画风（日本动漫感）"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"][0]["style_prompt"] = "anime key visual, clean cel shading"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    data = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    assert data["compiled_requirements"]["visual_family_hint"] == "anime"
    assert data["image_provider_strategy"]["primary"] == "openai_gpt_image2"
    assert data["jobs"][0]["provider_priority"][0] == "openai_gpt_image2"
    assert data["stage05_route_key"] == "anime_jp"
    assert data["comfyui_workflow_mapping_key"] == "stage05_anime_jp"
    assert data["comfyui_model_id"] == "circlestone-labs/Anima"
    assert data["preferred_comfyui_workflow_candidate"] == "anima_comparison_workflow"
    assert data["preferred_comfyui_model_candidate"] == "circlestone-labs/Anima"
    assert data["route_migration_state"] == "needs_api_conversion"
    assert data["jobs"][0]["comfyui_workflow_name"] == "txt2img_keyframe_anime"
    assert data["jobs"][0]["comfyui_workflow_mapping_key"] == "stage05_anime_jp"
    assert data["jobs"][0]["comfyui_model_id"] == "circlestone-labs/Anima"
    assert data["jobs"][0]["preferred_comfyui_workflow_candidate"] == "anima_comparison_workflow"
    assert data["jobs"][0]["preferred_comfyui_model_candidate"] == "circlestone-labs/Anima"
    assert data["jobs"][0]["route_migration_state"] == "needs_api_conversion"
    assert data["jobs"][0]["stage05_route_key"] == "anime_jp"
    assert data["route_resolution"]["used_registry"] is True
    assert data["route_resolution"]["resolution_mode"] == "stage00_style_registry"
    assert data["route_resolution"]["workflow_mapping_resolution"] == "route_registry_current_mapping"
    assert data["route_resolution"]["preferred_comfyui_workflow_candidate"] == "anima_comparison_workflow"
    assert data["route_resolution"]["preferred_comfyui_model_candidate"] == "circlestone-labs/Anima"
    assert data["route_resolution"]["route_migration_state"] == "needs_api_conversion"


def test_stage05_route_registry_maps_cn_animation_style_to_new_route_key(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_cn_anime_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["genre"] = "动画短片"
    brief["normalized"]["style"] = "国漫动画风（中国动画/新国风）"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"][0]["style_prompt"] = "anime key visual, eastern architecture, refined line art"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json)]) == 0
    data = json.loads(image_manifest_json.read_text(encoding="utf-8"))
    assert data["stage05_route_key"] == "anime_cn_newguofeng"
    assert data["style_family"] == "anime"
    assert data["comfyui_workflow_mapping_key"] == "stage05_anime_cn_newguofeng"
    assert data["comfyui_model_id"] == "neta-art/Neta-Lumina"
    assert data["preferred_comfyui_workflow_candidate"] == "neta_lumina_official"
    assert data["preferred_comfyui_model_candidate"] == "neta-art/Neta-Lumina"
    assert data["route_migration_state"] == "needs_api_conversion"
    assert data["jobs"][0]["comfyui_workflow_name"] == "txt2img_keyframe_anime_cn_newguofeng"
    assert data["jobs"][0]["comfyui_workflow_mapping_key"] == "stage05_anime_cn_newguofeng"
    assert data["route_resolution"]["used_registry"] is True


def test_validate_keyframe_image_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "keyframe_image_manifest.example.json").read_text(encoding="utf-8"))
    assert data["stage05_route_key"] == "realistic_cinematic"
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic"
    assert data["comfyui_model_id"] == "Tongyi-MAI/Z-Image"
    assert data["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic_zimage_photo_bridge"
    assert data["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image"
    assert data["route_migration_state"] == "repo_transitional"
    assert data["preferred_comfyui_workflow_source_ref"] == "workflows/comfyui/txt2img_keyframe_realistic_zimage_photo_bridge.workflow_api.json"
    assert data["preferred_comfyui_workflow_format"] == "api_workflow"
    assert data["preferred_comfyui_workflow_custom_node_dependencies"] == []
    assert data["preferred_comfyui_workflow_import_blockers"] == []
    assert data["route_resolution"]["resolution_mode"] == "stage00_style_registry"
    assert all(job["stage05_route_key"] == "realistic_cinematic" for job in data["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic" for job in data["jobs"])
    assert all(job["comfyui_workflow_name"] == "txt2img_keyframe_realistic_zimage_photo_bridge" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic_zimage_photo_bridge" for job in data["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image" for job in data["jobs"])
    assert all(job["route_migration_state"] == "repo_transitional" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_format"] == "api_workflow" for job in data["jobs"])
    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, TEMPLATES / "keyframe_image_manifest.example.json", mode="final")
    assert ok, errors


def test_new_keyframe_image_jobs_passes_draft_then_placeholder_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.6.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "aspect_ratio": "9:16",
        "resolution": "1080P",
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
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
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="draft")
    assert ok, errors
    assert warnings
    assert data["reference_image_status"]["all_present"] is False
    assert data["stage05_execution_readiness"]["safe_to_auto_generate"] is False
    assert data["reference_guidance_requested"] is True
    assert data["reference_guidance_ready"] is False
    assert data["reference_guidance_active"] is False
    assert "selected_workflow_does_not_accept_reference_images" in data["workflow_capability_gaps"]
    assert data["comfyui_workflow_capabilities"]["supports_reference_images"] is False
    assert len(data["jobs"]) == 2 * len(keyframe["shot_prompts"])
    assert data["style_family"] == "realistic"
    assert data["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic"
    assert data["comfyui_model_id"] == "Tongyi-MAI/Z-Image"
    assert data["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic_zimage_photo_bridge"
    assert data["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image"
    assert data["route_migration_state"] == "repo_transitional"
    assert data["preferred_comfyui_workflow_source_ref"] == "workflows/comfyui/txt2img_keyframe_realistic_zimage_photo_bridge.workflow_api.json"
    assert data["preferred_comfyui_workflow_format"] == "api_workflow"
    assert data["comfyui_workflow_router"]["realistic"] == "txt2img_keyframe_realistic"
    assert all(job["style_family"] == "realistic" for job in data["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic" for job in data["jobs"])
    assert all(job["comfyui_workflow_name"] == "txt2img_keyframe_realistic_zimage_photo_bridge" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_realistic_zimage_photo_bridge" for job in data["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "Tongyi-MAI/Z-Image" for job in data["jobs"])
    assert all(job["route_migration_state"] == "repo_transitional" for job in data["jobs"])
    assert all(job["preferred_comfyui_workflow_format"] == "api_workflow" for job in data["jobs"])
    assert all(job["reference_guidance_requested"] is True for job in data["jobs"])
    assert all(job["reference_guidance_active"] is False for job in data["jobs"])

    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
    assert not ok
    assert any("status must be succeeded" in e or "image file does not exist" in e for e in errors)

    # Test-only placeholder generation creates real files and should then pass final validation.
    import sys as _sys
    old_argv = _sys.argv[:]
    try:
        _sys.argv = ["generate_placeholder_keyframe_images.py", str(manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        _sys.argv = old_argv
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="final")
    assert ok, errors


def test_sync_keyframe_image_manifest_backfills_route_key_from_top_level(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_210000_route_sync_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-29T21:00:00+08:00",
    })
    brief["normalized"]["style"] = "日系动画风（日本动漫感）"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
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

    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["stage05_route_key"] == "anime_jp"
    data.pop("stage05_route_key", None)
    data.pop("comfyui_workflow_mapping_key", None)
    data.pop("comfyui_model_id", None)
    data.pop("preferred_comfyui_workflow_candidate", None)
    data.pop("preferred_comfyui_model_candidate", None)
    data.pop("route_migration_state", None)
    for job in data["jobs"]:
        job.pop("stage05_route_key", None)
        job.pop("comfyui_workflow_mapping_key", None)
        job.pop("comfyui_model_id", None)
        job.pop("preferred_comfyui_workflow_candidate", None)
        job.pop("preferred_comfyui_model_candidate", None)
        job.pop("route_migration_state", None)
    manifest_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(manifest_json)]
        assert sync_keyframe_image_manifest.main() == 0
    finally:
        sys.argv = old_argv

    synced = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert synced["stage05_route_key"] == "anime_jp"
    assert synced["comfyui_workflow_mapping_key"] == "stage05_anime_jp"
    assert synced["comfyui_model_id"] == "circlestone-labs/Anima"
    assert synced["preferred_comfyui_workflow_candidate"] == "anima_comparison_workflow"
    assert synced["preferred_comfyui_model_candidate"] == "circlestone-labs/Anima"
    assert synced["route_migration_state"] == "needs_api_conversion"
    assert synced["preferred_comfyui_workflow_source_ref"] == "https://huggingface.co/circlestone-labs/Anima/blob/main/anima_comparison.json"
    assert all(job["stage05_route_key"] == "anime_jp" for job in synced["jobs"])
    assert all(job["comfyui_workflow_mapping_key"] == "stage05_anime_jp" for job in synced["jobs"])
    assert all(job["comfyui_model_id"] == "circlestone-labs/Anima" for job in synced["jobs"])
    assert all(job["preferred_comfyui_workflow_candidate"] == "anima_comparison_workflow" for job in synced["jobs"])
    assert all(job["preferred_comfyui_model_candidate"] == "circlestone-labs/Anima" for job in synced["jobs"])
    assert all(job["route_migration_state"] == "needs_api_conversion" for job in synced["jobs"])
    assert synced["status"] == "draft"
    assert synced["summary"]["generated_image_count"] == 0


def test_new_keyframe_image_jobs_activates_reference_guided_mode_when_mapping_supports_it(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_reference_ready"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    reference_dir = project_dir / "03_characters" / "reference_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
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
    (reference_dir / "CHAR_001_primary.png").write_bytes(b"PNGDATA")

    fake_mapping_path = tmp_path / "workflow_node_mapping.yaml"
    fake_mapping = {
        "workflows": {
            "stage05_realistic_cinematic_qwen_edit_reference": {
                "file": "workflows/comfyui/fake_reference.workflow_api.json",
                "nodes": {
                    "positive_prompt": {"node_id": "1", "input_name": "text"},
                    "reference_image_path": {"node_id": "2", "input_name": "image"},
                },
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["prompt_only", "reference_guided"],
                },
            }
        }
    }
    monkeypatch.setattr(new_keyframe_image_jobs, "load_workflow_mapping", lambda root=None: (fake_mapping, fake_mapping_path))
    monkeypatch.setattr(new_keyframe_image_jobs, "get_workflow_mapping", lambda data, workflow_name: data["workflows"][workflow_name])

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert data["comfyui_control_mode"] == "reference_guided"
    assert data["reference_guidance_requested"] is True
    assert data["reference_guidance_ready"] is True
    assert data["reference_guidance_active"] is True
    assert data["workflow_capability_gaps"] == []
    assert data["comfyui_workflow_capabilities"]["supports_reference_images"] is True
    assert all(job["comfyui_control_mode"] == "reference_guided" for job in data["jobs"])
    assert all(job["reference_guidance_active"] is True for job in data["jobs"])


def test_new_keyframe_image_jobs_promotes_interaction_handoff_to_dual_reference_when_context_frame_exists(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_120000_handoff_dual_ref"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    keyframes_output_dir = images_dir / "keyframes"
    reference_dir = project_dir / "03_characters" / "reference_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    keyframes_output_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.5.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T12:00:00+08:00",
    })
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    (reference_dir / "CHAR_001_primary.png").write_bytes(b"PNGDATA")
    (keyframes_output_dir / "S001_end.png").write_bytes(b"PNGDATA")

    fake_mapping_path = tmp_path / "workflow_node_mapping.yaml"
    fake_mapping = {
        "workflows": {
            "stage05_realistic_cinematic_qwen_edit_reference": {
                "file": "workflows/comfyui/fake_reference.workflow_api.json",
                "nodes": {
                    "positive_prompt": {"node_id": "1", "input_name": "text"},
                    "reference_image_path": {"node_id": "2", "input_name": "image"},
                },
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["prompt_only", "reference_guided"],
                },
            },
            "stage05_realistic_cinematic_qwen_edit_dual_reference": {
                "file": "workflows/comfyui/fake_dual_reference.workflow_api.json",
                "nodes": {
                    "positive_prompt": {"node_id": "1", "input_name": "text"},
                    "reference_image_path": {"node_id": "2", "input_name": "image"},
                    "reference_image_path_2": {"node_id": "3", "input_name": "image"},
                },
                "capabilities": {
                    "supports_reference_images": True,
                    "supported_control_modes": ["prompt_only", "reference_guided"],
                },
            },
        }
    }
    monkeypatch.setattr(new_keyframe_image_jobs, "load_workflow_mapping", lambda root=None: (fake_mapping, fake_mapping_path))
    monkeypatch.setattr(new_keyframe_image_jobs, "get_workflow_mapping", lambda data, workflow_name: data["workflows"][workflow_name])
    monkeypatch.setattr(
        new_keyframe_image_jobs,
        "classify_stage06_generation",
        lambda shot_prompt, storyboard_shot, bundle: {"route_hint": "interaction_handoff"},
    )

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main([
        "new_keyframe_image_jobs.py",
        str(locked_brief),
        str(keyframe_json),
        str(manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    mid_job = next(job for job in data["jobs"] if job["image_id"] == "IMG_S001_MID")
    assert mid_job["stage06_route_hint"] == "interaction_handoff"
    assert mid_job["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_dual_reference"
    assert mid_job["comfyui_workflow_name"] == "fake_dual_reference"
    assert mid_job["reference_bundle_mode"] == "primary_plus_context_frame"
    assert mid_job["reference_images"] == [
        "03_characters/reference_images/CHAR_001_primary.png",
        "05_images/keyframes/S001_end.png",
    ]
    assert mid_job["secondary_reference_images"] == ["05_images/keyframes/S001_end.png"]
    assert "avoid symmetrical posing" in mid_job["prompt"]
    assert "floating handle" in mid_job["negative_prompt"]


def test_resolve_stage05_route_switches_shortdrama_realistic_to_reference_guided_target_when_refs_ready() -> None:
    brief = {
        "normalized": {
            "style": "短剧爽感",
            "genre": "治愈",
        }
    }
    prompts = {
        "reference_image_status": {
            "all_present": True,
        },
        "stage05_execution_readiness": {
            "reference_image_required": True,
        },
        "shot_prompts": [
            {
                "style_prompt": "realistic dramatic short drama still",
            }
        ],
    }
    resolved = new_keyframe_image_jobs.resolve_stage05_route(brief, prompts)
    assert resolved["used_registry"] is True
    assert resolved["route_key"] == "shortdrama_realistic"
    assert resolved["reference_guided_route_selected"] is True
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_shortdrama_realistic_qwen_edit_reference"
    assert resolved["comfyui_workflow_name"] == "txt2img_keyframe_shortdrama_qwen_edit_reference"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Image-Edit-2511"
    assert resolved["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_shortdrama_qwen_edit_reference"
    assert resolved["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Image-Edit-2511"
    assert resolved["comfyui_control_mode"] == "reference_guided"


def test_resolve_stage05_route_switches_realistic_cinematic_to_reference_guided_target_when_refs_ready() -> None:
    brief = {
        "normalized": {
            "style": "写实电影感",
            "genre": "治愈",
        }
    }
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
    assert resolved["comfyui_workflow_mapping_key"] == "stage05_realistic_cinematic_qwen_edit_reference"
    assert resolved["comfyui_workflow_name"] == "txt2img_keyframe_shortdrama_qwen_edit_reference"
    assert resolved["comfyui_model_id"] == "Qwen/Qwen-Image-Edit-2511"
    assert resolved["preferred_comfyui_workflow_candidate"] == "txt2img_keyframe_shortdrama_qwen_edit_reference"
    assert resolved["preferred_comfyui_model_candidate"] == "Qwen/Qwen-Image-Edit-2511"
    assert resolved["comfyui_control_mode"] == "reference_guided"


def test_sync_keyframe_image_manifest_blocks_risky_umbrella_scene_until_approved(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260530_umbrella_review_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T20:00:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "ancient Chinese woman holding one oil-paper umbrella in misty rain"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman turns slightly while holding the same oil-paper umbrella"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert manifest["comfyui_control_mode"] == "prompt_only"
    assert manifest["quality_review"]["manual_review_cleared"] is False
    assert all(job["quality_gate"]["requires_manual_review"] is True for job in manifest["jobs"])
    assert all(job["quality_gate"]["manual_review_status"] == "pending" for job in manifest["jobs"])

    for job in manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(manifest_json)]
        assert sync_keyframe_image_manifest.main() == 0
    finally:
        sys.argv = old_argv

    blocked = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert blocked["self_check"]["all_required_images_exist"] is True
    assert blocked["self_check"]["manual_review_cleared"] is False
    assert blocked["self_check"]["ready_for_video_clip_generation"] is False
    assert blocked["allowed_next_stage"] is None
    assert blocked["quality_review"]["next_review_image_ids"] == ["IMG_S001_START", "IMG_S001_END"]
    assert blocked["quality_review"]["review_queue"][0]["priority_label"] == "高优先级复核"
    assert blocked["jobs"][0]["creator_review_card"]["checklist"]
    manual_review_text = (images_dir / "manual_review.md").read_text(encoding="utf-8")
    assert "# Stage 05 Manual Review" in manual_review_text
    assert "建议先看" in manual_review_text
    assert "Top 3 快速问题卡" in manual_review_text
    assert "IMG_S001_START" in manual_review_text
    assert "复核清单" in manual_review_text
    review_workbench_html = (images_dir / "stage05_review_workbench.html").read_text(encoding="utf-8")
    review_workbench_json = json.loads((images_dir / "stage05_review_workbench.json").read_text(encoding="utf-8"))
    assert "Stage 05 审图工作台" in review_workbench_html
    assert review_workbench_json["cards"][0]["image_id"] == "IMG_S001_START"
    prompt_patch_plan = json.loads((images_dir / "prompt_patch_plan.json").read_text(encoding="utf-8"))
    assert prompt_patch_plan["patch_count"] == 2
    assert prompt_patch_plan["queue_patch_count"] == 2
    assert prompt_patch_plan["top_prompt_patches"][0]["image_id"] == "IMG_S001_START"
    assert "auto_repair_stage05_review_queue.py" in prompt_patch_plan["top_prompt_patches"][0]["rerun_command"]
    prompt_patch_cards = (images_dir / "prompt_patch_cards.md").read_text(encoding="utf-8")
    assert "最短改法" in prompt_patch_cards

    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_keyframe_image_manifest.py", str(manifest_json), "--approve-risky-jobs"]
        assert sync_keyframe_image_manifest.main() == 0
    finally:
        sys.argv = old_argv

    approved = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert approved["quality_review"]["manual_review_cleared"] is True
    assert approved["self_check"]["manual_review_cleared"] is True
    assert approved["self_check"]["ready_for_video_clip_generation"] is True
    assert approved["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"
    assert all(job["quality_gate"]["manual_review_status"] == "approved" for job in approved["jobs"])


def test_rerun_top_prompt_patches_invokes_stage05_runner_in_priority_order(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260530_prompt_patch_rerun_demo"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T20:00:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:2]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "ancient Chinese woman holding one oil-paper umbrella in misty rain"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman turns slightly while holding the same oil-paper umbrella"
    keyframe["shot_prompts"][1]["start_keyframe_prompt"] = "another woman holding one oil-paper umbrella under street rain"
    keyframe["shot_prompts"][1]["end_keyframe_prompt"] = "the same woman keeps holding the same oil-paper umbrella while stepping forward"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    invoked: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        assert argv is not None
        invoked.append(list(argv))
        manifest_data = json.loads(manifest_json.read_text(encoding="utf-8"))
        target_image_id = argv[2]
        for job in manifest_data["jobs"]:
            if job["image_id"] != target_image_id:
                continue
            output_path = Path(job["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"png")
            job["status"] = "succeeded"
            break
        manifest_json.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    monkeypatch.setattr(
        rerun_top_prompt_patches,
        "select_stage05_runner",
        lambda data, config_path=None: {
            "provider": "openai_gpt_image2",
            "status": "ready",
            "reason": "test_forced_openai",
            "priority": ["openai_gpt_image2", "comfyui_txt2img", "manual"],
            "probe_results": [],
            "config_path": None,
        },
    )
    monkeypatch.setattr(rerun_top_prompt_patches.run_openai_gpt_image2, "main", fake_main)
    assert rerun_top_prompt_patches.main([str(manifest_json), "--limit", "3", "--allow-beyond-requested-scope"]) == 0

    assert [args[2] for args in invoked] == ["IMG_S001_START", "IMG_S001_END", "IMG_S002_START"]
    assert all("--allow-beyond-requested-scope" in args for args in invoked)
    rerun_report = json.loads((images_dir / "prompt_patch_rerun_report.json").read_text(encoding="utf-8"))
    assert rerun_report["selected_count"] == 3
    assert rerun_report["success_count"] == 3
    assert rerun_report["failure_count"] == 0
    assert rerun_report["selected_provider"] == "openai_gpt_image2"
    assert rerun_report["results"][0]["command"].startswith("python ")
    assert rerun_report["remaining_pending_count"] == 4
    assert rerun_report["next_pending_image_ids"][:3] == ["IMG_S001_START", "IMG_S001_END", "IMG_S002_START"]
    rerun_report_md = (images_dir / "prompt_patch_rerun_report.md").read_text(encoding="utf-8")
    assert "# Stage 05 Prompt Patch Rerun Report" in rerun_report_md
    assert "IMG_S001_START" in rerun_report_md

    assert approve_stage05_review_queue.main([str(manifest_json), "--top", "3", "--note", "creator approved after visual review"]) == 1
    assert approve_stage05_review_queue.main([
        str(manifest_json),
        "--top",
        "3",
        "--note",
        "creator approved after visual review",
        "--content-aligned",
        "--content-alignment-note",
        "Reviewed against shot intent and image content matches the prompt package.",
    ]) == 0

    invoked.clear()
    assert rerun_top_prompt_patches.main([str(manifest_json), "--limit", "3", "--dry-run"]) == 0
    assert invoked == []
    rerun_report = json.loads((images_dir / "prompt_patch_rerun_report.json").read_text(encoding="utf-8"))
    assert rerun_report["selected_count"] == 1
    assert rerun_report["results"][0]["image_id"] == "IMG_S002_END"
    assert rerun_report["skipped_manually_cleared_image_ids"] == ["IMG_S001_END", "IMG_S001_START", "IMG_S002_START"]
    assert rerun_report["previously_succeeded_image_ids"] == ["IMG_S001_END", "IMG_S001_START", "IMG_S002_START"]
    assert rerun_report["skipped_previously_succeeded_image_ids"] == []
    assert rerun_report["remaining_pending_count"] == 1
    assert rerun_report["next_pending_image_ids"] == ["IMG_S002_END"]
    approved_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    approved_jobs = {
        job["image_id"]: job
        for job in approved_manifest["jobs"]
        if job["image_id"] in {"IMG_S001_START", "IMG_S001_END", "IMG_S002_START"}
    }
    assert all(job["quality_gate"]["manual_review_status"] == "approved" for job in approved_jobs.values())
    assert all(job["quality_gate"]["review_note"] == "creator approved after visual review" for job in approved_jobs.values())
    assert all(job["quality_gate"]["content_text_alignment_confirmed"] is True for job in approved_jobs.values())
    assert all(job["quality_gate"]["content_text_alignment_note"] for job in approved_jobs.values())
    manual_review_text = (images_dir / "manual_review.md").read_text(encoding="utf-8")
    assert "## 看完后的推进" in manual_review_text
    assert "approve_stage05_review_queue.py" in manual_review_text

    final_pending_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    for job in final_pending_manifest["jobs"]:
        if job["image_id"] != "IMG_S002_END":
            continue
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        job["status"] = "succeeded"
        break
    manifest_json.write_text(json.dumps(final_pending_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assert approve_stage05_review_queue.main([
        str(manifest_json),
        "--all-pending",
        "--content-aligned",
        "--content-alignment-note",
        "Remaining approved images were checked against the prompt description and continuity notes.",
    ]) == 0
    fully_approved_manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    assert fully_approved_manifest["quality_review"]["manual_review_cleared"] is True
    assert fully_approved_manifest["self_check"]["ready_for_video_clip_generation"] is True
    assert fully_approved_manifest["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"


def test_rerun_top_prompt_patches_switches_to_comfyui_when_openai_unavailable(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_stage05_auto_repair_comfy"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T11:00:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "young woman with one umbrella in rainy storefront"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "same woman keeps one umbrella while leaving storefront"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    invoked: list[list[str]] = []

    def fake_comfy_main(argv: list[str] | None = None) -> int:
        assert argv is not None
        invoked.append(list(argv))
        manifest_data = json.loads(manifest_json.read_text(encoding="utf-8"))
        image_id = argv[2]
        for job in manifest_data["jobs"]:
            if job["image_id"] != image_id:
                continue
            output_path = Path(job["output_path"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"png")
            job["status"] = "succeeded"
            job["provider"] = "comfyui_txt2img"
            break
        manifest_json.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0

    monkeypatch.setattr(
        rerun_top_prompt_patches,
        "select_stage05_runner",
        lambda data, config_path=None: {
            "provider": "comfyui_txt2img",
            "status": "ready",
            "reason": "openai_invalid_api_key",
            "priority": ["openai_gpt_image2", "comfyui_txt2img", "manual"],
            "probe_results": [
                {"provider": "openai_gpt_image2", "status": "invalid_api_key"},
                {"provider": "comfyui_txt2img", "status": "ready"},
            ],
            "config_path": None,
        },
    )
    monkeypatch.setattr(rerun_top_prompt_patches.run_comfyui_txt2img, "main", fake_comfy_main)
    assert rerun_top_prompt_patches.main([str(manifest_json), "--image-id", "IMG_S001_START"]) == 0

    assert invoked and invoked[0][2] == "IMG_S001_START"
    rerun_report = json.loads((images_dir / "prompt_patch_rerun_report.json").read_text(encoding="utf-8"))
    assert rerun_report["selected_provider"] == "comfyui_txt2img"
    assert rerun_report["provider_probe"]["reason"] == "openai_invalid_api_key"
    assert rerun_report["results"][0]["provider"] == "comfyui_txt2img"


def test_stage05_review_workbench_server_serves_state_and_actions(tmp_path: Path, monkeypatch) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260531_stage05_workbench_server"
    intake_dir = project_dir / "00_intake"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    intake_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-31T12:00:00+08:00",
    })
    brief["normalized"]["style"] = "国风水墨/古风"
    brief["normalized"]["final_output"] = "生成关键帧图片素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe["shot_prompts"] = keyframe["shot_prompts"][:1]
    keyframe["shot_prompts"][0]["start_keyframe_prompt"] = "ancient Chinese woman holding one oil-paper umbrella in misty rain"
    keyframe["shot_prompts"][0]["end_keyframe_prompt"] = "the same woman turns slightly while holding the same oil-paper umbrella"
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    for job in manifest["jobs"]:
        output_path = Path(job["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    assert sync_keyframe_image_manifest.main([str(manifest_json)]) == 0

    invoked: list[list[str]] = []

    def fake_rerun(argv: list[str] | None = None) -> int:
        assert argv is not None
        invoked.append(list(argv))
        return 0

    monkeypatch.setattr(serve_stage05_review_workbench.rerun_top_prompt_patches, "main", fake_rerun)

    server = serve_stage05_review_workbench.build_server(manifest_json.resolve(), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"
        state = json.loads(request.urlopen(f"{base_url}/api/state").read().decode("utf-8"))
        assert state["cards"][0]["image_id"] == "IMG_S001_START"

        html_text = request.urlopen(f"{base_url}/").read().decode("utf-8")
        assert "Stage 05 审图工作台" in html_text
        assert "runWorkbenchAction" in html_text

        image_path = Path(manifest["jobs"][0]["output_path"]).resolve()
        image_bytes = request.urlopen(f"{base_url}/api/file?path={quote(str(image_path))}").read()
        assert image_bytes == b"png"

        approve_request = request.Request(
            f"{base_url}/api/action",
            data=json.dumps({"action": "approve_image", "image_id": "IMG_S001_START"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        approve_payload = json.loads(request.urlopen(approve_request).read().decode("utf-8"))
        assert approve_payload["ok"] is True
        assert approve_payload["state"]["quality_review"]["pending_count"] == 1

        rerun_request = request.Request(
            f"{base_url}/api/action",
            data=json.dumps({"action": "auto_repair_image", "image_id": "IMG_S001_END"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        rerun_payload = json.loads(request.urlopen(rerun_request).read().decode("utf-8"))
        assert rerun_payload["ok"] is True
        assert invoked and "--allow-beyond-requested-scope" in invoked[0]
        assert invoked[0][2] == "IMG_S001_END"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_validate_video_clip_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "video_clip_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_video_clip_manifest.validate(data, TEMPLATES / "video_clip_manifest.example.json", mode="final")
    assert ok, errors


def test_new_video_clip_jobs_passes_draft_then_placeholder_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    intake_dir.mkdir(parents=True)
    storyboard_dir.mkdir(parents=True)
    keyframe_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)
    video_dir.mkdir(parents=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.7.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "aspect_ratio": "9:16",
        "resolution": "1080P",
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
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
    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_video_clip_manifest.validate(data, clip_manifest_json, mode="draft")
    assert ok, errors
    assert warnings
    assert len(data["jobs"]) == len(keyframe["shot_prompts"])

    ok, errors, warnings = validate_video_clip_manifest.validate(data, clip_manifest_json, mode="final")
    assert not ok
    assert any("status must be succeeded" in e or "clip file does not exist" in e for e in errors)

    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_video_clip_manifest.validate(data, clip_manifest_json, mode="final")
    assert ok, errors


def test_sync_video_clip_manifest_demotes_placeholder_clips_from_ready_state(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260530_placeholder_demote"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for folder in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.7.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-30T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
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
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_video_clip_manifest.py", str(clip_manifest_json)]
        assert sync_video_clip_manifest.main() == 0
    finally:
        sys.argv = old_argv

    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert data["status"] == "draft"
    assert data["summary"]["generated_clip_count"] == 0
    assert data["self_check"]["all_required_clips_exist"] is False
    assert data["self_check"]["ready_for_audio_stage"] is False
    assert all(job["status"] == "failed" for job in data["jobs"])
    assert any("non-production clip evidence" in (job.get("notes") or "") for job in data["jobs"])


def test_stage05_placeholder_generation_auto_advances_project_manifest_and_unblocks_stage06(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for d in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        d.mkdir(parents=True, exist_ok=True)

    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_00_BRIEF_LOCKED",
        "brief_locked": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-29T19:08:42+08:00",
    })
    brief["normalized"]["final_output"] = "生成视频片段素材包"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
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
    project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert image_manifest["status"] == "generated"
    assert image_manifest["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"
    assert project_manifest["current_stage"] == "STAGE_05_KEYFRAME_IMAGES_CONFIRMED"
    assert project_manifest["keyframe_images_confirmed"] is True
    assert project_manifest["allowed_next_stage"] == "STAGE_06_VIDEO_CLIPS"

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0


def test_new_video_clip_jobs_blocks_when_requested_scope_stops_at_keyframe_prompts(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260529_190842_project"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    for d in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir]:
        d.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-29T19:08:42+08:00",
    })
    brief["normalized"]["final_output"] = "剧本 + 分镜 + 关键帧提示词"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    image_manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(image_manifest_json), "--allow-beyond-requested-scope"]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_keyframe_images.py", str(image_manifest_json), "--width", "64", "--height", "96"]
        assert generate_placeholder_keyframe_images.main() == 0
    finally:
        sys.argv = old_argv

    clip_manifest_json = video_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 1
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(keyframe_json),
        str(image_manifest_json),
        str(clip_manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0



def test_validate_audio_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "audio_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(data, TEMPLATES / "audio_manifest.example.json", mode="final")
    assert ok, errors


def test_new_audio_jobs_passes_draft_then_placeholder_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    script_dir = project_dir / "01_script"
    storyboard_dir = project_dir / "02_storyboard"
    character_dir = project_dir / "03_characters"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    for d in [intake_dir, script_dir, storyboard_dir, character_dir, keyframe_dir, images_dir, video_dir, audio_dir]:
        d.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.8.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "合成粗剪成片"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
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
    assert new_video_clip_jobs.main(["new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    clip_manifest = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    clip_manifest["status"] = "confirmed"
    clip_manifest_json.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    audio_manifest_json = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main([
        "new_audio_jobs.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(clip_manifest_json), str(audio_manifest_json)
    ]) == 0
    data = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(data, audio_manifest_json, mode="draft")
    assert ok, errors
    assert warnings
    assert data["summary"]["expected_voice_count"] > 0
    assert data["summary"]["expected_music_count"] == 1

    ok, errors, warnings = validate_audio_manifest.validate(data, audio_manifest_json, mode="final")
    assert not ok
    assert any("status must be succeeded" in e or "audio file does not exist" in e for e in errors)

    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_audio.py", str(audio_manifest_json)]
        assert generate_placeholder_audio.main() == 0
    finally:
        sys.argv = old_argv
    data = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_audio_manifest.validate(data, audio_manifest_json, mode="final")
    assert ok, errors



def test_validate_assembly_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "assembly_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, TEMPLATES / "assembly_manifest.example.json", mode="final")
    assert ok, errors


def test_new_assembly_manifest_passes_draft_then_placeholder_is_blocked_from_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    images_dir = project_dir / "05_images"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assembly_dir = project_dir / "08_assembly"
    for d in [intake_dir, storyboard_dir, keyframe_dir, images_dir, video_dir, audio_dir, assembly_dir]:
        d.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "0.9.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "合成粗剪成片"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    storyboard["project_id"] = project_dir.name
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
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
    assert new_video_clip_jobs.main(["new_video_clip_jobs.py", str(locked_brief), str(storyboard_json), str(keyframe_json), str(image_manifest_json), str(clip_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_video_clips.py", str(clip_manifest_json)]
        assert generate_placeholder_video_clips.main() == 0
    finally:
        sys.argv = old_argv
    clip_manifest = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    clip_manifest["status"] = "confirmed"
    clip_manifest_json.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build a minimal script/character file only because Stage 07 scaffolder requires them.
    script_dir = project_dir / "01_script"
    character_dir = project_dir / "03_characters"
    script_dir.mkdir(parents=True, exist_ok=True)
    character_dir.mkdir(parents=True, exist_ok=True)
    script = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    script["project_id"] = project_dir.name
    script_json = script_dir / "script.json"
    script_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    character = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    character["project_id"] = project_dir.name
    character_json = character_dir / "character_bible.json"
    character_json.write_text(json.dumps(character, ensure_ascii=False, indent=2), encoding="utf-8")

    audio_manifest_json = audio_dir / "audio_manifest.json"
    assert new_audio_jobs.main(["new_audio_jobs.py", str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(clip_manifest_json), str(audio_manifest_json)]) == 0
    old_argv = sys.argv[:]
    try:
        sys.argv = ["generate_placeholder_audio.py", str(audio_manifest_json)]
        assert generate_placeholder_audio.main() == 0
    finally:
        sys.argv = old_argv
    audio_manifest = json.loads(audio_manifest_json.read_text(encoding="utf-8"))
    audio_manifest["status"] = "confirmed"
    audio_manifest_json.write_text(json.dumps(audio_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assert new_assembly_manifest.main(["new_assembly_manifest.py", str(locked_brief), str(storyboard_json), str(clip_manifest_json), str(audio_manifest_json), str(assembly_manifest_json)]) == 0
    data = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, assembly_manifest_json, mode="draft")
    assert ok, errors
    assert warnings

    ok, errors, warnings = validate_assembly_manifest.validate(data, assembly_manifest_json, mode="final")
    assert not ok
    assert any("final output file does not exist" in e or "final output file is empty" in e for e in errors)

    old_argv = sys.argv[:]
    try:
        sys.argv = ["assemble_with_ffmpeg.py", str(assembly_manifest_json), "--placeholder-test"]
        assert assemble_with_ffmpeg.main() == 0
    finally:
        sys.argv = old_argv
    data = json.loads(assembly_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, assembly_manifest_json, mode="final")
    assert not ok
    assert any("placeholder" in e or "too small" in e for e in errors)



def test_validate_qa_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "qa_manifest.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_qa_manifest.validate(data, TEMPLATES / "qa_manifest.example.json", mode="final")
    assert ok, errors


def test_new_qa_manifest_passes_draft_then_package_delivery_passes_final(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl"
    intake_dir = project_dir / "00_intake"
    assembly_dir = project_dir / "08_assembly"
    qa_dir = project_dir / "09_qa"
    intake_dir.mkdir(parents=True, exist_ok=True)
    assembly_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
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
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path = project_dir / "project_manifest.json"
    manifest_path.write_text(json.dumps({
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_08_ASSEMBLY_CONFIRMED",
        "assembly_confirmed": True,
        "allowed_next_stage": "STAGE_09_QA",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Create a minimal Stage 08 assembly manifest with real rough_cut evidence.
    rough_cut = assembly_dir / "rough_cut" / "rough_cut.mp4"
    rough_cut.parent.mkdir(parents=True, exist_ok=True)
    rough_cut.write_bytes(b"\x00\x00\x00\x18ftypmp42QA" + (b"1" * 140))
    assembly_manifest = {
        "schema_version": "0.9.0",
        "stage": "STAGE_08_ASSEMBLY",
        "status": "generated",
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "source_storyboard": "",
        "source_video_clip_manifest": "",
        "source_audio_manifest": "",
        "assembly_provider_strategy": {"primary": "placeholder"},
        "output_root": str(assembly_dir).replace("\\", "/"),
        "rough_cut_dir": str(rough_cut.parent).replace("\\", "/"),
        "temp_dir": str((assembly_dir / "temp")).replace("\\", "/"),
        "concat_list_path": str((assembly_dir / "ffmpeg_concat_list.txt")).replace("\\", "/"),
        "edit_decision_list_path": str((assembly_dir / "edit_decision_list.json")).replace("\\", "/"),
        "audio_mix_plan_path": str((assembly_dir / "audio_mix_plan.json")).replace("\\", "/"),
        "subtitle_path": str((assembly_dir / "subtitles.srt")).replace("\\", "/"),
        "final_output_path": str(rough_cut).replace("\\", "/"),
        "timeline": [{"shot_id": "S001", "clip_path": str(rough_cut).replace("\\", "/"), "start_sec": 0, "duration_sec": 5, "source_clip_id": "CLIP_S001"}],
        "audio_tracks": [],
        "subtitle_tracks": [],
        "ffmpeg_commands": [{
            "command": ["ffmpeg"],
            "provider": "ffmpeg",
            "strategy": "reencode_mix",
            "return_code": 0,
            "stdout_excerpt": "",
            "stderr_excerpt": "",
            "ran_at": "2026-05-28T10:40:00+08:00",
        }],
        "assembly_provider": "ffmpeg",
        "evidence": {"file_path": str(rough_cut).replace("\\", "/"), "file_exists": True, "file_size_bytes": rough_cut.stat().st_size, "created_at": "2026-05-28T10:40:00+08:00"},
        "summary": {"timeline_clip_count": 1, "audio_track_count": 0, "rough_cut_duration_sec": 5},
        "self_check": {"has_timeline_from_confirmed_clips": True, "has_audio_mix_plan": True, "has_edit_decision_list": True, "has_final_output_file": True, "ready_for_qa_stage": True},
        "allowed_next_stage": "STAGE_09_QA",
        "errors": [],
    }
    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assembly_manifest_json.write_text(json.dumps(assembly_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    qa_manifest_json = qa_dir / "qa_manifest.json"
    assert new_qa_manifest.main(["new_qa_manifest.py", str(locked_brief), str(assembly_manifest_json), str(qa_manifest_json)]) == 0
    data = json.loads(qa_manifest_json.read_text(encoding="utf-8"))
    check_ids = {item["check_id"] for item in data["qa_checks"]}
    assert {"intent_alignment", "visual_continuity_contract", "performance_direction_contract", "audio_direction_contract", "format_fit_contract"}.issubset(check_ids)
    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="draft")
    assert ok, errors
    assert warnings

    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="final")
    assert not ok
    assert any("qa_checks" in e or "delivery_package" in e for e in errors)

    assert package_delivery.main(["package_delivery.py", str(qa_manifest_json)]) == 1
    assert package_delivery.main([
        "package_delivery.py",
        str(qa_manifest_json),
        "--content-aligned",
        "--content-alignment-note",
        "QA reviewer confirmed the delivered rough cut matches the script, storyboard, and prompt intent.",
    ]) == 0
    data = json.loads(qa_manifest_json.read_text(encoding="utf-8"))
    check_status = {item["check_id"]: item["status"] for item in data["qa_checks"]}
    assert check_status["intent_alignment"] == "pass"
    assert check_status["content_text_alignment"] == "pass"
    assert check_status["visual_continuity_contract"] in {"pass", "waived"}
    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="final")
    assert ok, errors
    assert data["content_alignment_review"]["confirmed"] is True
    assert data["content_alignment_review"]["status"] == "pass"
    project_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert project_manifest["current_stage"] == "STAGE_09_QA_CONFIRMED"
    assert project_manifest["qa_confirmed"] is True
    assert project_manifest["delivery_complete"] is True
    assert project_manifest["allowed_next_stage"] == "PROJECT_DELIVERED"


def test_package_delivery_blocks_when_requested_scope_stops_at_rough_cut(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "video_20260528_103000_scope_blocked_qa"
    intake_dir = project_dir / "00_intake"
    assembly_dir = project_dir / "08_assembly"
    qa_dir = project_dir / "09_qa"
    intake_dir.mkdir(parents=True, exist_ok=True)
    assembly_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    brief = load_example_brief()
    brief.update({
        "schema_version": "1.0.0",
        "project_id": project_dir.name,
        "project_dir": str(project_dir).replace("\\", "/"),
        "status": "locked",
        "confirmed_by_user": True,
        "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION",
        "locked_at": "2026-05-28T10:35:00+08:00",
    })
    brief["normalized"]["final_output"] = "合成粗剪成片"
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    rough_cut = assembly_dir / "rough_cut" / "rough_cut.mp4"
    rough_cut.parent.mkdir(parents=True, exist_ok=True)
    rough_cut.write_bytes(b"\x00\x00\x00\x18ftypmp42QB" + (b"2" * 140))
    assembly_manifest = {
        "schema_version": "0.9.0",
        "stage": "STAGE_08_ASSEMBLY",
        "status": "generated",
        "project_id": project_dir.name,
        "source_brief": str(locked_brief).replace("\\", "/"),
        "source_storyboard": "",
        "source_video_clip_manifest": "",
        "source_audio_manifest": "",
        "assembly_provider_strategy": {"primary": "placeholder"},
        "output_root": str(assembly_dir).replace("\\", "/"),
        "rough_cut_dir": str(rough_cut.parent).replace("\\", "/"),
        "temp_dir": str((assembly_dir / "temp")).replace("\\", "/"),
        "concat_list_path": str((assembly_dir / "ffmpeg_concat_list.txt")).replace("\\", "/"),
        "edit_decision_list_path": str((assembly_dir / "edit_decision_list.json")).replace("\\", "/"),
        "audio_mix_plan_path": str((assembly_dir / "audio_mix_plan.json")).replace("\\", "/"),
        "subtitle_path": str((assembly_dir / "subtitles.srt")).replace("\\", "/"),
        "final_output_path": str(rough_cut).replace("\\", "/"),
        "timeline": [{"shot_id": "S001", "clip_path": str(rough_cut).replace("\\", "/"), "start_sec": 0, "duration_sec": 5, "source_clip_id": "CLIP_S001"}],
        "audio_tracks": [],
        "subtitle_tracks": [],
        "ffmpeg_commands": [{
            "command": ["ffmpeg"],
            "provider": "ffmpeg",
            "strategy": "reencode_mix",
            "return_code": 0,
            "stdout_excerpt": "",
            "stderr_excerpt": "",
            "ran_at": "2026-05-28T10:40:00+08:00",
        }],
        "assembly_provider": "ffmpeg",
        "evidence": {"file_path": str(rough_cut).replace("\\", "/"), "file_exists": True, "file_size_bytes": rough_cut.stat().st_size, "created_at": "2026-05-28T10:40:00+08:00"},
        "summary": {"timeline_clip_count": 1, "audio_track_count": 0, "rough_cut_duration_sec": 5},
        "self_check": {"has_timeline_from_confirmed_clips": True, "has_audio_mix_plan": True, "has_edit_decision_list": True, "has_final_output_file": True, "ready_for_qa_stage": True},
        "allowed_next_stage": "STAGE_09_QA",
        "errors": [],
    }
    assembly_manifest_json = assembly_dir / "assembly_manifest.json"
    assembly_manifest_json.write_text(json.dumps(assembly_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    qa_manifest_json = qa_dir / "qa_manifest.json"
    assert new_qa_manifest.main([
        "new_qa_manifest.py",
        str(locked_brief),
        str(assembly_manifest_json),
        str(qa_manifest_json),
        "--allow-beyond-requested-scope",
    ]) == 0

    assert package_delivery.main(["package_delivery.py", str(qa_manifest_json)]) == 1
    assert package_delivery.main([
        "package_delivery.py",
        str(qa_manifest_json),
        "--allow-beyond-requested-scope",
        "--content-aligned",
        "--content-alignment-note",
        "Scope override run also includes manual confirmation that content matches the text description.",
    ]) == 0


def test_new_video_clip_jobs_ignores_template_leaked_story_anchors(tmp_path: Path) -> None:
    project_dir = tmp_path / "video_projects" / "creator_trial_20260530_rainy_store"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    keyframe_dir = project_dir / "04_keyframes"
    image_dir = project_dir / "05_images"
    clip_dir = project_dir / "06_video_clips"
    intake_dir.mkdir(parents=True, exist_ok=True)
    storyboard_dir.mkdir(parents=True, exist_ok=True)
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    clip_dir.mkdir(parents=True, exist_ok=True)

    brief = load_rainy_store_brief(project_dir)
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard = {
        "stage": "STAGE_02_STORYBOARD_GENERATION",
        "project_id": project_dir.name,
        "shots": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "scene": "雨夜便利店门口",
            "location": "便利店门口",
            "weather": "雨夜",
            "key_prop": "最后一把伞",
            "action": "20岁出头的女孩把最后一把伞留给陌生人",
            "emotion": "克制善意",
        }],
        "story_anchors": {
            "subject": "海边女孩",
            "location": "核心场景",
            "weather": "雨夜",
            "scene_label": "核心场景",
            "key_props": ["最后一把伞", "热可可"],
            "action_beats": ["动作与情绪逐步变化"],
            "emotion_beats": ["克制善意"],
            "composition_beats": ["进入故事空间"],
        },
    }
    storyboard_json = storyboard_dir / "storyboard.json"
    storyboard_json.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    prompts = {
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "project_id": project_dir.name,
        "shot_prompts": [{
            "shot_id": "S001",
            "duration_sec": 4,
            "motion_prompt": "",
            "performance_prompt": "",
            "dialogue_delivery_prompt": "",
            "consistency_prompt": "",
            "negative_prompt": "多手，额外人物",
        }],
        "global_negative_prompt": "多手，额外人物",
    }
    prompts_json = keyframe_dir / "keyframe_prompts.json"
    prompts_json.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")

    start_image = image_dir / "S001_start.png"
    end_image = image_dir / "S001_end.png"
    start_image.write_bytes(b"png-start")
    end_image.write_bytes(b"png-end")
    image_manifest = {
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": project_dir.name,
        "jobs": [
            {"image_id": "IMG_S001_START", "shot_id": "S001", "frame_role": "start", "output_path": str(start_image).replace("\\", "/"), "evidence": {"file_path": str(start_image).replace("\\", "/")}},
            {"image_id": "IMG_S001_END", "shot_id": "S001", "frame_role": "end", "output_path": str(end_image).replace("\\", "/"), "evidence": {"file_path": str(end_image).replace("\\", "/")}},
        ],
    }
    image_manifest_json = image_dir / "keyframe_image_manifest.json"
    image_manifest_json.write_text(json.dumps(image_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_manifest_json = clip_dir / "video_clip_manifest.json"
    assert new_video_clip_jobs.main([
        "new_video_clip_jobs.py",
        str(locked_brief),
        str(storyboard_json),
        str(prompts_json),
        str(image_manifest_json),
        str(clip_manifest_json),
    ]) == 0

    data = json.loads(clip_manifest_json.read_text(encoding="utf-8"))
    assert data["story_anchors"]["subject"] == "20岁出头的女孩"
    assert data["story_anchors"]["scene_label"] == "雨夜便利店门口"
    assert "海边女孩" not in data["jobs"][0]["consistency_prompt"]
    assert "核心场景" not in data["jobs"][0]["consistency_prompt"]
    assert "20岁出头的女孩" in data["jobs"][0]["consistency_prompt"]
    assert "雨夜便利店门口" in data["jobs"][0]["consistency_prompt"]
    assert "gentle camera movement" not in data["jobs"][0]["motion_prompt"]
    assert "可见的身体位移" in data["jobs"][0]["motion_prompt"]
    assert "最后一把伞" in data["jobs"][0]["motion_prompt"]
