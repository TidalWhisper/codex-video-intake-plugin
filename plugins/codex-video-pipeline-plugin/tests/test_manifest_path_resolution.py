#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "scripts" / "providers"
IMAGES = ROOT / "skills" / "video-keyframe-images" / "scripts"
ASSEMBLY = ROOT / "skills" / "video-assembly" / "scripts"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


stage05_image_utils = load_module("stage05_image_utils_path_test", PROVIDERS / "stage05_image_utils.py")
stage06_video_utils = load_module("stage06_video_utils_path_test", PROVIDERS / "stage06_video_utils.py")
stage07_audio_utils = load_module("stage07_audio_utils_path_test", PROVIDERS / "stage07_audio_utils.py")
validate_keyframe_image_manifest = load_module("validate_keyframe_image_manifest_path_test", IMAGES / "validate_keyframe_image_manifest.py")
new_assembly_manifest = load_module("new_assembly_manifest_path_test", ASSEMBLY / "new_assembly_manifest.py")
validate_assembly_manifest = load_module("validate_assembly_manifest_path_test", ASSEMBLY / "validate_assembly_manifest.py")
assemble_with_ffmpeg = load_module("assemble_with_ffmpeg_path_test", ASSEMBLY / "assemble_with_ffmpeg.py")
sync_assembly_manifest = load_module("sync_assembly_manifest_path_test", ASSEMBLY / "sync_assembly_manifest.py")


def _project_layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo_root = tmp_path / "repo"
    plugin_root = repo_root / "plugins" / "codex-video-pipeline-plugin"
    project_dir = plugin_root / "video_projects" / "real_smoke"
    return repo_root, plugin_root, project_dir


@pytest.mark.parametrize(
    ("module", "relative_target"),
    [
        (stage05_image_utils, "05_images/keyframes/S001_start.png"),
        (stage06_video_utils, "06_video_clips/clips/S001.mp4"),
        (stage07_audio_utils, "07_audio/voice/S001_voiceover.wav"),
    ],
)
def test_provider_resolve_path_accepts_repo_relative_paths_from_plugin_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    relative_target: str,
) -> None:
    repo_root, plugin_root, project_dir = _project_layout(tmp_path)
    manifest_dir = project_dir / relative_target.split("/", 1)[0]
    manifest_path = manifest_dir / "manifest.json"
    expected = project_dir / relative_target
    expected.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    repo_relative = str(expected.relative_to(repo_root)).replace("\\", "/")

    monkeypatch.chdir(plugin_root)
    resolved = module.resolve_path(manifest_path, repo_relative)

    assert resolved == expected.resolve()


@pytest.mark.parametrize(
    ("module", "relative_target"),
    [
        (stage05_image_utils, "05_images/keyframes/S001_start.png"),
        (stage06_video_utils, "06_video_clips/clips/S001.mp4"),
    ],
)
def test_provider_resolve_path_accepts_plugin_relative_paths_without_duplication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    relative_target: str,
) -> None:
    repo_root, plugin_root, project_dir = _project_layout(tmp_path)
    manifest_dir = project_dir / relative_target.split("/", 1)[0]
    manifest_path = manifest_dir / "manifest.json"
    expected = project_dir / relative_target
    expected.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    plugin_relative = str(expected.relative_to(repo_root)).replace("\\", "/")

    monkeypatch.chdir(plugin_root)
    resolved = module.resolve_path(manifest_path, plugin_relative)

    assert resolved == expected.resolve()


def test_stage07_provider_resolve_path_prefers_repo_root_for_planned_repo_relative_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, plugin_root, project_dir = _project_layout(tmp_path)
    manifest_path = project_dir / "07_audio" / "audio_manifest.json"
    expected = project_dir / "07_audio" / "voice" / "S001_voiceover.wav"
    expected.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    repo_relative = str(expected.relative_to(repo_root)).replace("\\", "/")

    monkeypatch.chdir(plugin_root)
    resolved = stage07_audio_utils.resolve_path(manifest_path, repo_relative)

    assert resolved == expected.resolve()


def test_stage05_validator_accepts_repo_relative_paths_from_plugin_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, plugin_root, project_dir = _project_layout(tmp_path)
    manifest_dir = project_dir / "05_images"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "keyframe_image_manifest.json"
    start_file = manifest_dir / "keyframes" / "S001_start.png"
    end_file = manifest_dir / "keyframes" / "S001_end.png"
    start_file.parent.mkdir(parents=True, exist_ok=True)
    start_file.write_bytes(b"png-start")
    end_file.write_bytes(b"png-end")

    def repo_rel(path: Path) -> str:
        return str(path.relative_to(repo_root)).replace("\\", "/")

    manifest = {
        "schema_version": "0.6.0",
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "generated",
        "project_id": "real_smoke",
        "source_brief": repo_rel(project_dir / "00_intake" / "project_brief.locked.json"),
        "source_keyframe_prompts": repo_rel(project_dir / "04_keyframes" / "keyframe_prompts.json"),
        "image_provider_strategy": {"primary": "comfyui_txt2img", "fallback": ["manual"]},
        "output_root": repo_rel(manifest_dir),
        "keyframes_dir": repo_rel(manifest_dir / "keyframes"),
        "jobs": [
            {
                "image_id": "IMG_S001_START",
                "shot_id": "S001",
                "frame_role": "start",
                "prompt": "start",
                "negative_prompt": "neg",
                "aspect_ratio": "9:16",
                "resolution": "1080P",
                "provider_priority": ["comfyui_txt2img"],
                "provider": "comfyui_txt2img",
                "status": "succeeded",
                "output_path": repo_rel(start_file),
                "evidence": {
                    "file_path": repo_rel(start_file),
                    "file_exists": True,
                    "file_size_bytes": start_file.stat().st_size,
                    "created_at": "2026-05-28T00:00:00+00:00",
                },
                "errors": [],
                "notes": "",
            },
            {
                "image_id": "IMG_S001_END",
                "shot_id": "S001",
                "frame_role": "end",
                "prompt": "end",
                "negative_prompt": "neg",
                "aspect_ratio": "9:16",
                "resolution": "1080P",
                "provider_priority": ["comfyui_txt2img"],
                "provider": "comfyui_txt2img",
                "status": "succeeded",
                "output_path": repo_rel(end_file),
                "evidence": {
                    "file_path": repo_rel(end_file),
                    "file_exists": True,
                    "file_size_bytes": end_file.stat().st_size,
                    "created_at": "2026-05-28T00:00:00+00:00",
                },
                "errors": [],
                "notes": "",
            },
        ],
        "summary": {
            "shot_count": 1,
            "expected_image_count": 2,
            "generated_image_count": 2,
            "failed_image_count": 0,
        },
        "quality_signals": {
            "intent_route_matches_strategy": True,
            "style_route_matches_strategy": True,
            "consistency_prompts_present": True,
            "quality_targets_defined": True,
        },
        "quality_review": {
            "risky_image_count": 0,
            "risky_image_ids": [],
            "required_count": 0,
            "approved_count": 0,
            "pending_count": 0,
            "waived_count": 0,
            "blocking_image_ids": [],
            "manual_review_cleared": True,
        },
        "self_check": {
            "covers_all_keyframe_prompts": True,
            "has_start_and_end_for_each_shot": True,
            "all_required_images_exist": True,
            "manual_review_cleared": True,
            "ready_for_video_clip_generation": True,
        },
        "allowed_next_stage": "STAGE_06_VIDEO_CLIPS",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.chdir(plugin_root)
    ok, errors, warnings = validate_keyframe_image_manifest.validate(manifest, manifest_path, mode="final")

    assert ok, errors
    assert warnings == []


@pytest.mark.parametrize(
    ("module", "relative_target"),
    [
        (new_assembly_manifest, "06_video_clips/clips/S001.mp4"),
        (new_assembly_manifest, "07_audio/voice/S001_voiceover.wav"),
        (validate_assembly_manifest, "07_audio/music/BGM_MAIN.wav"),
        (assemble_with_ffmpeg, "08_assembly/rough_cut/rough_cut.mp4"),
        (sync_assembly_manifest, "08_assembly/rough_cut/rough_cut.mp4"),
    ],
)
def test_stage08_resolve_path_prefers_repo_root_for_repo_relative_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    relative_target: str,
) -> None:
    repo_root, plugin_root, project_dir = _project_layout(tmp_path)
    manifest_dir = project_dir / "08_assembly"
    manifest_path = Path("video_projects/real_smoke/08_assembly/assembly_manifest.json")
    expected = project_dir / relative_target
    expected.parent.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    expected.write_bytes(b"path-resolution-test")
    repo_relative = str(expected.relative_to(repo_root)).replace("\\", "/")

    monkeypatch.chdir(plugin_root)
    resolved = module.resolve_path(manifest_path, repo_relative)

    assert resolved == expected.resolve()


def test_sync_assembly_manifest_repairs_template_notes_and_audio_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root, plugin_root, project_dir = _project_layout(tmp_path)
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    video_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assembly_dir = project_dir / "08_assembly"
    for path in [intake_dir, storyboard_dir, video_dir / "clips", audio_dir / "voice", assembly_dir / "rough_cut"]:
        path.mkdir(parents=True, exist_ok=True)

    brief_path = intake_dir / "project_brief.locked.json"
    brief_path.write_text(json.dumps({
        "project_id": "real_smoke",
        "status": "locked",
        "confirmed_by_user": True,
        "normalized": {
            "idea": "一位20岁出头的女孩在雨夜便利店门口把最后一把伞留给陌生人，自己淋着雨走远，回头发现门口多了一杯热可可"
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    storyboard_path = storyboard_dir / "storyboard.json"
    storyboard_path.write_text(json.dumps({
        "shots": [{
            "shot_id": "S001",
            "scene": "雨夜便利店门口",
            "location": "便利店门口",
            "weather": "雨夜",
            "key_prop": "最后一把伞",
            "action": "20岁出头的女孩把最后一把伞留给陌生人",
            "emotion": "克制善意",
        }],
        "story_anchors": {
            "subject": "20岁出头的女孩",
            "location": "便利店门口",
            "weather": "雨夜",
            "scene_label": "雨夜便利店门口",
            "key_props": ["最后一把伞", "热可可"],
            "action_beats": ["把最后一把伞留给陌生人"],
            "emotion_beats": ["克制善意"],
            "composition_beats": ["先用竖屏建立镜头交代雨夜便利店门口与雨夜，人物与最后一把伞同框。"],
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    clip_path = video_dir / "clips" / "S001.mp4"
    clip_path.write_bytes(b"\x00\x00\x00\x18ftypmp42CLIP" + (b"0" * 512))
    clip_manifest_path = video_dir / "video_clip_manifest.json"
    clip_manifest_path.write_text(json.dumps({
        "self_check": {"ready_for_audio_stage": True},
        "jobs": [{
            "clip_id": "CLIP_S001",
            "shot_id": "S001",
            "output_path": str(clip_path.relative_to(repo_root)).replace("\\", "/"),
        }]
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    voice_path = audio_dir / "voice" / "S001_voiceover.wav"
    voice_path.write_bytes(b"voice-output")
    audio_manifest_path = audio_dir / "audio_manifest.json"
    audio_manifest_path.write_text(json.dumps({
        "self_check": {"ready_for_assembly_stage": False},
        "jobs": [{
            "audio_id": "AUD_VOICEOVER_S001",
            "audio_type": "voiceover",
            "output_path": str(voice_path.relative_to(repo_root)).replace("\\", "/"),
        }]
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    rough_cut = assembly_dir / "rough_cut" / "rough_cut.mp4"
    rough_cut.write_bytes(b"\x00\x00\x00\x18ftypmp42tiny")
    assembly_manifest_path = assembly_dir / "assembly_manifest.json"
    assembly_manifest_path.write_text(json.dumps({
        "stage": "STAGE_08_ASSEMBLY",
        "status": "generated",
        "project_id": "real_smoke",
        "source_brief": str(brief_path.relative_to(repo_root)).replace("\\", "/"),
        "source_storyboard": str(storyboard_path.relative_to(repo_root)).replace("\\", "/"),
        "source_video_clip_manifest": str(clip_manifest_path.relative_to(repo_root)).replace("\\", "/"),
        "source_audio_manifest": str(audio_manifest_path.relative_to(repo_root)).replace("\\", "/"),
        "timeline": [{
            "shot_id": "S001",
            "source_clip_id": "CLIP_S001",
            "clip_path": "stale/clip.mp4",
            "start_sec": 0.0,
            "duration_sec": 4.0,
            "notes": "核心场景中，海边女孩 的动作与情绪逐步变化。",
        }],
        "audio_tracks": [{
            "audio_id": "ASM_AUD_VOICEOVER_S001",
            "audio_type": "voiceover",
            "source_audio_id": "AUD_VOICEOVER_S001",
            "audio_path": "video_projects/real_smoke/07_audio/video_projects/real_smoke/07_audio/voice/S001_voiceover.wav",
            "duration_sec": 4.0,
        }],
        "ffmpeg_commands": [{
            "command": ["ffmpeg"],
            "provider": "ffmpeg",
            "strategy": "reencode_mix",
            "return_code": 0,
            "ran_at": "2026-05-30T00:00:00+00:00",
        }],
        "assembly_provider": "ffmpeg",
        "final_output_path": str(rough_cut.relative_to(repo_root)).replace("\\", "/"),
        "audio_mix_plan_path": str((assembly_dir / "audio_mix_plan.json").relative_to(repo_root)).replace("\\", "/"),
        "edit_decision_list_path": str((assembly_dir / "edit_decision_list.json").relative_to(repo_root)).replace("\\", "/"),
        "routing": {"legacy_mode": False},
        "evidence": {"file_path": str(rough_cut.relative_to(repo_root)).replace("\\", "/")},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (assembly_dir / "audio_mix_plan.json").write_text("{}", encoding="utf-8")
    (assembly_dir / "edit_decision_list.json").write_text("{}", encoding="utf-8")
    (project_dir / "project_manifest.json").write_text(json.dumps({
        "project_id": "real_smoke",
        "project_dir": str(project_dir).replace("\\", "/"),
        "current_stage": "STAGE_08_ASSEMBLY_CONFIRMED",
        "assembly_confirmed": True,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.chdir(plugin_root)
    old_argv = sys.argv[:]
    try:
        sys.argv = ["sync_assembly_manifest.py", str(assembly_manifest_path.relative_to(plugin_root)).replace("\\", "/")]
        assert sync_assembly_manifest.main() == 0
    finally:
        sys.argv = old_argv

    synced = json.loads(assembly_manifest_path.read_text(encoding="utf-8"))
    assert "海边女孩" not in synced["timeline"][0]["notes"]
    assert "核心场景" not in synced["timeline"][0]["notes"]
    assert "雨夜便利店门口" in synced["timeline"][0]["notes"]
    assert synced["timeline"][0]["clip_path"] == clip_path.resolve().as_posix()
    assert synced["audio_tracks"][0]["audio_path"] == voice_path.resolve().as_posix()
    assert synced["self_check"]["ready_for_qa_stage"] is False
    assert synced["status"] == "in_progress"
    project_manifest = json.loads((project_dir / "project_manifest.json").read_text(encoding="utf-8"))
    assert project_manifest["current_stage"] == "STAGE_07_AUDIO"
    assert project_manifest["audio_confirmed"] is False
    assert project_manifest["assembly_confirmed"] is False
