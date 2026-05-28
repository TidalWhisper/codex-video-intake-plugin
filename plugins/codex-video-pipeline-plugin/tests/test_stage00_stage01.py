#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

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
new_video_clip_jobs = load_module("new_video_clip_jobs_for_test", VIDEOCLIPS / "new_video_clip_jobs.py")
validate_video_clip_manifest = load_module("validate_video_clip_manifest_for_test", VIDEOCLIPS / "validate_video_clip_manifest.py")
generate_placeholder_video_clips = load_module("generate_placeholder_video_clips_for_test", VIDEOCLIPS / "generate_placeholder_video_clips.py")
new_audio_jobs = load_module("new_audio_jobs_for_test", AUDIO / "new_audio_jobs.py")
validate_audio_manifest = load_module("validate_audio_manifest_for_test", AUDIO / "validate_audio_manifest.py")
generate_placeholder_audio = load_module("generate_placeholder_audio_for_test", AUDIO / "generate_placeholder_audio.py")
new_assembly_manifest = load_module("new_assembly_manifest_for_test", ASSEMBLY / "new_assembly_manifest.py")
validate_assembly_manifest = load_module("validate_assembly_manifest_for_test", ASSEMBLY / "validate_assembly_manifest.py")
assemble_with_ffmpeg = load_module("assemble_with_ffmpeg_for_test", ASSEMBLY / "assemble_with_ffmpeg.py")
new_qa_manifest = load_module("new_qa_manifest_for_test", QA / "new_qa_manifest.py")
validate_qa_manifest = load_module("validate_qa_manifest_for_test", QA / "validate_qa_manifest.py")
package_delivery = load_module("package_delivery_for_test", QA / "package_delivery.py")
update_project_manifest = load_module("update_project_manifest_for_test", PIPELINE / "update_project_manifest.py")


def load_example_brief() -> dict:
    return json.loads((TEMPLATES / "project_brief.draft.example.json").read_text(encoding="utf-8"))


def test_validate_project_brief_example() -> None:
    data = load_example_brief()
    ok, errors, warnings = validate_project_brief.validate(data, TEMPLATES / "project_brief.draft.example.json")
    assert ok, errors


def test_create_project_folder_uses_project_suffix_for_chinese_numeric_title(tmp_path: Path, monkeypatch) -> None:
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
    assert project_dir.name.endswith("_project")
    assert not project_dir.name.endswith("_20")
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


def test_validate_script_example_final() -> None:
    data = json.loads((TEMPLATES / "script.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_script.validate(data, mode="final")
    assert ok, errors


def test_new_script_template_passes_draft_validation_but_not_final(tmp_path: Path) -> None:
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
    ok, errors, warnings = validate_script.validate(script_data, mode="draft")
    assert ok, errors
    assert warnings

    ok, errors, warnings = validate_script.validate(script_data, mode="final")
    assert not ok
    assert any("title must not be blank" in e for e in errors)



def test_validate_storyboard_example_final() -> None:
    data = json.loads((TEMPLATES / "storyboard.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_storyboard.validate(data, mode="final")
    assert ok, errors


def test_new_storyboard_template_passes_draft_validation_but_not_final(tmp_path: Path) -> None:
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
    assert warnings

    ok, errors, warnings = validate_storyboard.validate(storyboard_data, mode="final")
    assert not ok
    assert any("shots must not be empty" in e for e in errors)



def test_validate_character_bible_example_final() -> None:
    data = json.loads((TEMPLATES / "character_bible.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_character_bible.validate(data, mode="final")
    assert ok, errors


def test_new_character_bible_template_passes_draft_validation_but_not_final(tmp_path: Path) -> None:
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
    assert warnings

    ok, errors, warnings = validate_character_bible.validate(character_data, mode="final")
    assert not ok
    assert any("characters must not be empty" in e for e in errors)

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
    assert data["keyframe_prompts_confirmed"] is True
    assert data["keyframe_images_confirmed"] is False
    assert data["video_clips_confirmed"] is True
    assert data["audio_confirmed"] is True
    assert data["assembly_confirmed"] is False



def test_validate_keyframe_prompts_example_final() -> None:
    data = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_prompts.validate(data, mode="final")
    assert ok, errors


def test_new_keyframe_prompts_template_passes_draft_validation_but_not_final(tmp_path: Path) -> None:
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
    assert warnings
    assert len(keyframe_data["shot_prompts"]) == len(storyboard["shots"])

    ok, errors, warnings = validate_keyframe_prompts.validate(keyframe_data, mode="final")
    assert not ok
    assert any("start_keyframe_prompt must not be blank" in e for e in errors)


def test_validate_keyframe_image_manifest_example_final() -> None:
    data = json.loads((TEMPLATES / "keyframe_image_manifest.example.json").read_text(encoding="utf-8"))
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
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    keyframe = json.loads((TEMPLATES / "keyframe_prompts.example.json").read_text(encoding="utf-8"))
    keyframe["project_id"] = project_dir.name
    keyframe["source_brief"] = str(locked_brief).replace("\\", "/")
    keyframe_json = keyframe_dir / "keyframe_prompts.json"
    keyframe_json.write_text(json.dumps(keyframe, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_json = images_dir / "keyframe_image_manifest.json"
    assert new_keyframe_image_jobs.main(["new_keyframe_image_jobs.py", str(locked_brief), str(keyframe_json), str(manifest_json)]) == 0
    data = json.loads(manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_keyframe_image_manifest.validate(data, manifest_json, mode="draft")
    assert ok, errors
    assert warnings
    assert len(data["jobs"]) == 2 * len(keyframe["shot_prompts"])

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


def test_new_assembly_manifest_passes_draft_then_placeholder_passes_final(tmp_path: Path) -> None:
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
    assert ok, errors



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
    locked_brief = intake_dir / "project_brief.locked.json"
    locked_brief.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    # Create a minimal Stage 08 assembly manifest with real rough_cut evidence.
    rough_cut = assembly_dir / "rough_cut" / "rough_cut.mp4"
    rough_cut.parent.mkdir(parents=True, exist_ok=True)
    rough_cut.write_bytes(b"PLACEHOLDER ROUGH CUT FOR QA TEST")
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
        "ffmpeg_commands": [],
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
    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="draft")
    assert ok, errors
    assert warnings

    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="final")
    assert not ok
    assert any("qa_checks" in e or "delivery_package" in e for e in errors)

    assert package_delivery.main(["package_delivery.py", str(qa_manifest_json)]) == 0
    data = json.loads(qa_manifest_json.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_qa_manifest.validate(data, qa_manifest_json, mode="final")
    assert ok, errors
