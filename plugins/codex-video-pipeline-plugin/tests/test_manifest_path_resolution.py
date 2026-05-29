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
        "self_check": {
            "covers_all_keyframe_prompts": True,
            "has_start_and_end_for_each_shot": True,
            "all_required_images_exist": True,
            "ready_for_video_clip_generation": True,
        },
        "allowed_next_stage": "STAGE_06_VIDEO_CLIPS",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.chdir(plugin_root)
    ok, errors, warnings = validate_keyframe_image_manifest.validate(manifest, manifest_path, mode="final")

    assert ok, errors
    assert warnings == []
