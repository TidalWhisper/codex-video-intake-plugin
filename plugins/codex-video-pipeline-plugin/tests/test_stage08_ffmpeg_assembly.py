#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
ASSEMBLY = ROOT / "skills" / "video-assembly" / "scripts"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new_assembly_manifest = load_module("new_assembly_manifest_stage08_test", ASSEMBLY / "new_assembly_manifest.py")
assemble_with_ffmpeg = load_module("assemble_with_ffmpeg_stage08_test", ASSEMBLY / "assemble_with_ffmpeg.py")
validate_assembly_manifest = load_module("validate_assembly_manifest_stage08_test", ASSEMBLY / "validate_assembly_manifest.py")


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _prepare_manifest(
    tmp_path: Path,
    *,
    burn_in: bool = False,
    add_fallback_visual: bool = False,
    clip_ready: bool = True,
) -> Path:
    assembly_dir = tmp_path / "video_projects" / "video_20260528_103000_sunset_beach_girl" / "08_assembly"
    clips_dir = assembly_dir.parent / "06_video_clips" / "clips"
    voice_dir = assembly_dir.parent / "07_audio" / "voice"
    music_dir = assembly_dir.parent / "07_audio" / "music"
    keyframe_dir = assembly_dir.parent / "05_images" / "keyframes"
    rough_cut = assembly_dir / "rough_cut" / "rough_cut.mp4"
    concat_list = assembly_dir / "ffmpeg_concat_list.txt"
    edl_path = assembly_dir / "edit_decision_list.json"
    mix_path = assembly_dir / "audio_mix_plan.json"
    subtitle_path = assembly_dir / "subtitles.srt"
    clip_manifest_path = assembly_dir.parent / "06_video_clips" / "video_clip_manifest.json"
    audio_manifest_path = assembly_dir.parent / "07_audio" / "audio_manifest.json"

    clip_path = clips_dir / "S001.mp4"
    voice_path = voice_dir / "S001_voiceover.wav"
    music_path = music_dir / "BGM_MAIN.wav"
    clip_payload = b"\x00\x00\x00\x18ftypmp42CLIP" + (b"0" * (512 if clip_ready else 16))
    _write_bytes(clip_path, clip_payload)
    _write_bytes(voice_path, b"RIFFVOICEWAVE")
    _write_bytes(music_path, b"RIFFMUSICWAVE")
    fallback_mid = keyframe_dir / "S001_mid.png"
    fallback_end = keyframe_dir / "S001_end.png"
    if add_fallback_visual:
        _write_bytes(fallback_mid, b"\x89PNG\r\n\x1a\n" + (b"1" * 256))
        _write_bytes(fallback_end, b"\x89PNG\r\n\x1a\n" + (b"2" * 256))
    concat_list.parent.mkdir(parents=True, exist_ok=True)
    concat_list.write_text(f"file '{str(clip_path).replace(chr(92), '/')}'\n", encoding="utf-8")
    edl_path.write_text(json.dumps({"project_id": "video_test", "events": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    mix_path.write_text(json.dumps({"project_id": "video_test", "audio_tracks": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    subtitle_path.write_text("1\n00:00:00,000 --> 00:00:05,000\n字幕测试\n", encoding="utf-8")
    clip_manifest = {
        "stage": "STAGE_06_VIDEO_CLIPS",
        "project_id": "video_test",
        "self_check": {"ready_for_audio_stage": clip_ready},
        "jobs": [{
            "clip_id": "CLIP_S001",
            "shot_id": "S001",
            "duration_sec": 5.0,
            "provider": "comfyui_ltx",
            "output_path": str(clip_path).replace("\\", "/"),
            "evidence": {"file_path": str(clip_path).replace("\\", "/")},
        }],
    }
    if add_fallback_visual:
        clip_manifest["jobs"][0]["source_keyframes"] = {
            "mid": str(fallback_mid).replace("\\", "/"),
            "end": str(fallback_end).replace("\\", "/"),
        }
    clip_manifest_path.write_text(json.dumps(clip_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    audio_manifest_path.write_text(json.dumps({
        "stage": "STAGE_07_AUDIO",
        "project_id": "video_test",
        "self_check": {"ready_for_assembly_stage": True},
        "jobs": [
            {
                "audio_id": "AUD_VOICEOVER_S001",
                "audio_type": "voiceover",
                "duration_sec": 5.0,
                "provider": "local",
                "output_path": str(voice_path).replace("\\", "/"),
                "evidence": {"file_path": str(voice_path).replace("\\", "/")},
            },
            {
                "audio_id": "AUD_MUSIC_BGM_MAIN",
                "audio_type": "music",
                "duration_sec": 30.0,
                "provider": "local",
                "output_path": str(music_path).replace("\\", "/"),
                "evidence": {"file_path": str(music_path).replace("\\", "/")},
            },
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "schema_version": "0.9.0",
        "stage": "STAGE_08_ASSEMBLY",
        "status": "draft",
        "project_id": "video_test",
        "source_brief": "brief.json",
        "source_storyboard": "storyboard.json",
        "source_video_clip_manifest": str(clip_manifest_path).replace("\\", "/"),
        "source_audio_manifest": str(audio_manifest_path).replace("\\", "/"),
        "created_at": "2026-05-28T10:40:00+08:00",
        "assembly_provider_strategy": {"primary": "ffmpeg", "fallback": ["manual"], "execution_mode": "provider_or_manual"},
        "output_root": str(assembly_dir).replace("\\", "/"),
        "rough_cut_dir": str(rough_cut.parent).replace("\\", "/"),
        "temp_dir": str((assembly_dir / "temp")).replace("\\", "/"),
        "concat_list_path": str(concat_list).replace("\\", "/"),
        "edit_decision_list_path": str(edl_path).replace("\\", "/"),
        "audio_mix_plan_path": str(mix_path).replace("\\", "/"),
        "subtitle_path": str(subtitle_path).replace("\\", "/"),
        "final_output_path": str(rough_cut).replace("\\", "/"),
        "timeline": [
            {
                "shot_id": "S001",
                "source_clip_id": "CLIP_S001",
                "clip_path": str(clip_path).replace("\\", "/"),
                "fallback_visual": {
                    "fallback_strategy": "stage05_keyframe_reel",
                    "source_clip_ready": clip_ready,
                    "start_image_path": "",
                    "mid_image_path": str(fallback_mid).replace("\\", "/") if add_fallback_visual else "",
                    "end_image_path": str(fallback_end).replace("\\", "/") if add_fallback_visual else "",
                    "preferred_image_path": str(fallback_mid).replace("\\", "/") if add_fallback_visual else "",
                },
                "start_sec": 0.0,
                "duration_sec": 5.0,
                "transition_in": "cut",
                "transition_out": "cut",
                "notes": "",
            }
        ],
        "audio_tracks": [
            {
                "audio_id": "ASM_AUD_VOICEOVER_S001",
                "audio_type": "voiceover",
                "source_audio_id": "AUD_VOICEOVER_S001",
                "audio_path": str(voice_path).replace("\\", "/"),
                "start_sec": 0.0,
                "duration_sec": 5.0,
                "volume": -6,
                "notes": "voice",
            },
            {
                "audio_id": "ASM_AUD_MUSIC_BGM_MAIN",
                "audio_type": "music",
                "source_audio_id": "AUD_MUSIC_BGM_MAIN",
                "audio_path": str(music_path).replace("\\", "/"),
                "start_sec": 0.0,
                "duration_sec": 30.0,
                "volume": -18,
                "notes": "music",
            },
        ],
        "subtitle_tracks": [
            {
                "subtitle_id": "SUB_MAIN",
                "path": str(subtitle_path).replace("\\", "/"),
                "format": "srt",
                "language": "zh-CN",
                "burn_in": burn_in,
            }
        ],
        "ffmpeg_commands": [],
        "evidence": {
            "file_path": str(rough_cut).replace("\\", "/"),
            "file_exists": False,
            "file_size_bytes": 0,
            "created_at": None,
        },
        "summary": {
            "timeline_clip_count": 1,
            "audio_track_count": 2,
            "rough_cut_duration_sec": 5.0,
        },
        "quality_signals": {
            "intent_route_matches_strategy": True,
            "timeline_matches_storyboard_order": True,
            "audio_tracks_match_strategy": True,
            "quality_targets_defined": True,
        },
        "self_check": {
            "has_timeline_from_confirmed_clips": True,
            "has_audio_mix_plan": True,
            "has_edit_decision_list": True,
            "has_final_output_file": False,
            "ready_for_qa_stage": False,
            "notes": [],
        },
        "errors": [],
        "allowed_next_stage": None,
    }
    manifest_path = assembly_dir / "assembly_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def test_build_ffmpeg_attempts_include_mix_and_optional_subtitles(tmp_path: Path) -> None:
    manifest_path = _prepare_manifest(tmp_path, burn_in=True)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    attempts = assemble_with_ffmpeg.build_ffmpeg_attempts(data, manifest_path, "ffmpeg")
    assert attempts
    first = attempts[0]["command"]
    joined = " ".join(first)
    assert "-filter_complex" in first
    assert "amix=inputs=2" in joined
    assert "subtitles='" in joined
    assert "libx264" in joined
    assert "aac" in joined


def test_new_assembly_manifest_resolves_repo_relative_media_paths_for_concat_and_audio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    plugin_root = repo_root / "plugins" / "codex-video-pipeline-plugin"
    project_dir = plugin_root / "video_projects" / "real_smoke"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    clip_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    assembly_dir = project_dir / "08_assembly"
    for path in [intake_dir, storyboard_dir, clip_dir / "clips", audio_dir / "voice", audio_dir / "music", assembly_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief_path = intake_dir / "project_brief.locked.json"
    brief_path.write_text(json.dumps({"status": "locked", "confirmed_by_user": True, "project_id": "real_smoke"}, ensure_ascii=False), encoding="utf-8")
    storyboard_path = storyboard_dir / "storyboard.json"
    storyboard_path.write_text(json.dumps({"shots": [{"shot_id": "S001", "duration_sec": 5, "voiceover": "line"}]}, ensure_ascii=False), encoding="utf-8")
    clip_path = clip_dir / "clips" / "S001.mp4"
    voice_path = audio_dir / "voice" / "S001_voiceover.wav"
    music_path = audio_dir / "music" / "BGM_MAIN.wav"
    _write_bytes(clip_path, b"\x00\x00\x00\x18ftypmp42CLIP" + (b"0" * 512))
    _write_bytes(voice_path, b"RIFFVOICEWAVE")
    _write_bytes(music_path, b"RIFFMUSICWAVE")

    def repo_rel(path: Path) -> str:
        return str(path.relative_to(repo_root)).replace("\\", "/")

    clip_manifest_path = clip_dir / "video_clip_manifest.json"
    clip_manifest_path.write_text(json.dumps({
        "stage": "STAGE_06_VIDEO_CLIPS",
        "project_id": "real_smoke",
        "self_check": {"ready_for_audio_stage": True},
        "jobs": [{
            "clip_id": "CLIP_S001",
            "shot_id": "S001",
            "duration_sec": 5.0,
            "output_path": repo_rel(clip_path),
            "evidence": {"file_path": repo_rel(clip_path)},
        }],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    audio_manifest_path = audio_dir / "audio_manifest.json"
    audio_manifest_path.write_text(json.dumps({
        "stage": "STAGE_07_AUDIO",
        "project_id": "real_smoke",
        "self_check": {"ready_for_assembly_stage": True},
        "jobs": [
            {
                "audio_id": "AUD_VOICEOVER_S001",
                "audio_type": "voiceover",
                "duration_sec": 5.0,
                "output_path": repo_rel(voice_path),
                "evidence": {"file_path": repo_rel(voice_path)},
            },
            {
                "audio_id": "AUD_MUSIC_BGM_MAIN",
                "audio_type": "music",
                "duration_sec": 30.0,
                "output_path": repo_rel(music_path),
                "evidence": {"file_path": repo_rel(music_path)},
            },
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = assembly_dir / "assembly_manifest.json"
    monkeypatch.chdir(plugin_root)
    assert new_assembly_manifest.main([
        "new_assembly_manifest.py",
        str(brief_path),
        str(storyboard_path),
        str(clip_manifest_path),
        str(audio_manifest_path),
        str(manifest_path),
    ]) == 0

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    concat_list = Path(data["concat_list_path"])
    assert clip_path.as_posix() in concat_list.read_text(encoding="utf-8")
    assert data["timeline"][0]["clip_path"] == clip_path.as_posix()
    assert {track["audio_path"] for track in data["audio_tracks"]} == {voice_path.as_posix(), music_path.as_posix()}


def test_assemble_with_ffmpeg_retries_and_records_attempts(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest(tmp_path)
    output_path = Path(json.loads(manifest_path.read_text(encoding="utf-8"))["final_output_path"])
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], text: bool, stdout: int, stderr: int) -> SimpleNamespace:
        calls.append(cmd)
        if len(calls) == 1:
            return SimpleNamespace(returncode=1, stdout="", stderr="first attempt failed")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42ROUGH" + (b"0" * 5000))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(assemble_with_ffmpeg, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(assemble_with_ffmpeg.subprocess, "run", fake_run)
    assert assemble_with_ffmpeg.main([str(manifest_path)]) == 0

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, manifest_path, mode="final")
    assert ok, errors
    assert warnings == []
    assert len(data["ffmpeg_commands"]) == 2
    assert data["ffmpeg_commands"][0]["return_code"] == 1
    assert data["ffmpeg_commands"][1]["return_code"] == 0
    assert data["assembly_provider"] == "ffmpeg"
    assert data["self_check"]["ready_for_qa_stage"] is True
    assert data["summary"]["output_video_spec"]["fps"] == 24


def test_assemble_with_ffmpeg_missing_binary_records_error(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest(tmp_path)
    monkeypatch.setattr(assemble_with_ffmpeg, "find_ffmpeg", lambda: None)
    assert assemble_with_ffmpeg.main([str(manifest_path)]) == 1
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["status"] == "in_progress"
    assert data["errors"]
    assert "ffmpeg executable not found" in data["errors"][-1]["message"]


def test_assemble_with_ffmpeg_blocks_nonproduction_source_clips(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    clip_path = Path(data["timeline"][0]["clip_path"])
    clip_path.write_bytes(b"\x00\x00\x00\x18ftypmp42tiny")
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(assemble_with_ffmpeg, "find_ffmpeg", lambda: "ffmpeg")

    assert assemble_with_ffmpeg.main([str(manifest_path)]) == 1

    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert updated["status"] == "in_progress"
    assert updated["errors"]
    assert "non-production or too small" in updated["errors"][-1]["message"]


def test_new_assembly_manifest_writes_fallback_visual_from_stage05_keyframes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    plugin_root = repo_root / "plugins" / "codex-video-pipeline-plugin"
    project_dir = plugin_root / "video_projects" / "real_smoke_fallback"
    intake_dir = project_dir / "00_intake"
    storyboard_dir = project_dir / "02_storyboard"
    clip_dir = project_dir / "06_video_clips"
    audio_dir = project_dir / "07_audio"
    images_dir = project_dir / "05_images" / "keyframes"
    assembly_dir = project_dir / "08_assembly"
    for path in [intake_dir, storyboard_dir, clip_dir / "clips", audio_dir / "voice", audio_dir / "music", images_dir, assembly_dir]:
        path.mkdir(parents=True, exist_ok=True)

    brief_path = intake_dir / "project_brief.locked.json"
    brief_path.write_text(json.dumps({"status": "locked", "confirmed_by_user": True, "project_id": "real_smoke_fallback"}, ensure_ascii=False), encoding="utf-8")
    storyboard_path = storyboard_dir / "storyboard.json"
    storyboard_path.write_text(json.dumps({"shots": [{"shot_id": "S001", "duration_sec": 5, "voiceover": "line"}]}, ensure_ascii=False), encoding="utf-8")
    clip_path = clip_dir / "clips" / "S001.mp4"
    voice_path = audio_dir / "voice" / "S001_voiceover.wav"
    music_path = audio_dir / "music" / "BGM_MAIN.wav"
    keyframe_mid = images_dir / "S001_mid.png"
    keyframe_end = images_dir / "S001_end.png"
    _write_bytes(clip_path, b"\x00\x00\x00\x18ftypmp42tiny")
    _write_bytes(voice_path, b"RIFFVOICEWAVE")
    _write_bytes(music_path, b"RIFFMUSICWAVE")
    _write_bytes(keyframe_mid, b"\x89PNG\r\n\x1a\n" + (b"3" * 256))
    _write_bytes(keyframe_end, b"\x89PNG\r\n\x1a\n" + (b"4" * 256))

    def repo_rel(path: Path) -> str:
        return str(path.relative_to(repo_root)).replace("\\", "/")

    clip_manifest_path = clip_dir / "video_clip_manifest.json"
    clip_manifest_path.write_text(json.dumps({
        "stage": "STAGE_06_VIDEO_CLIPS",
        "project_id": "real_smoke_fallback",
        "self_check": {"ready_for_audio_stage": True},
        "jobs": [{
            "clip_id": "CLIP_S001",
            "shot_id": "S001",
            "duration_sec": 5.0,
            "provider": "comfyui_ltx",
            "output_path": repo_rel(clip_path),
            "evidence": {"file_path": repo_rel(clip_path)},
            "source_keyframes": {
                "mid": repo_rel(keyframe_mid),
                "end": repo_rel(keyframe_end),
            },
        }],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    audio_manifest_path = audio_dir / "audio_manifest.json"
    audio_manifest_path.write_text(json.dumps({
        "stage": "STAGE_07_AUDIO",
        "project_id": "real_smoke_fallback",
        "self_check": {"ready_for_assembly_stage": True},
        "jobs": [
            {"audio_id": "AUD_VOICEOVER_S001", "audio_type": "voiceover", "duration_sec": 5.0, "output_path": repo_rel(voice_path), "evidence": {"file_path": repo_rel(voice_path)}},
            {"audio_id": "AUD_MUSIC_BGM_MAIN", "audio_type": "music", "duration_sec": 30.0, "output_path": repo_rel(music_path), "evidence": {"file_path": repo_rel(music_path)}},
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = assembly_dir / "assembly_manifest.json"
    monkeypatch.chdir(plugin_root)
    assert new_assembly_manifest.main([
        "new_assembly_manifest.py",
        str(brief_path),
        str(storyboard_path),
        str(clip_manifest_path),
        str(audio_manifest_path),
        str(manifest_path),
    ]) == 0

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    fallback_visual = data["timeline"][0]["fallback_visual"]
    assert fallback_visual["preferred_image_path"] == keyframe_mid.as_posix()
    assert fallback_visual["end_image_path"] == keyframe_end.as_posix()
    assert fallback_visual["source_clip_ready"] is False


def test_assemble_with_ffmpeg_uses_keyframe_fallback_segments_for_tiny_clips(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest(tmp_path, add_fallback_visual=True, clip_ready=False)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_path = Path(data["final_output_path"])
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], text: bool, stdout: int, stderr: int) -> SimpleNamespace:
        calls.append(cmd)
        output_file = Path(cmd[-1])
        output_file.parent.mkdir(parents=True, exist_ok=True)
        if "-loop" in cmd:
            output_file.write_bytes(b"\x00\x00\x00\x18ftypmp42FALLBACK" + (b"1" * 4096))
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42ROUGH" + (b"2" * 8192))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(assemble_with_ffmpeg, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(assemble_with_ffmpeg.subprocess, "run", fake_run)
    assert assemble_with_ffmpeg.main([str(manifest_path)]) == 0

    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(updated, manifest_path, mode="final")
    assert ok, errors
    assert warnings == []
    assert updated["status"] == "generated"
    assert updated["self_check"]["ready_for_qa_stage"] is True
    assert updated["summary"]["fallback_visual_segment_count"] == 1
    assert updated["fallback_visual_segments"][0]["shot_id"] == "S001"
    assert updated["fallback_visual_segments"][0]["source_image_path"].endswith("S001_mid.png")
    runtime_concat = Path(updated["runtime_concat_list_path"])
    assert runtime_concat.exists()
    concat_text = runtime_concat.read_text(encoding="utf-8")
    assert "fallback_visual_clips/S001.mp4" in concat_text.replace("\\", "/")
    assert updated["self_check"]["source_video_clips_ready"] is False
    assert updated["self_check"]["notes"].count("fallback_visual_segments:1") == 1
    assert output_path.exists() and output_path.stat().st_size > 128
    assert any("-loop" in call for call in calls)


def test_assemble_with_ffmpeg_replaces_placeholder_history_after_real_render(tmp_path: Path, monkeypatch) -> None:
    manifest_path = _prepare_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["assembly_provider"] = "placeholder_test_assembly_generator"
    data["ffmpeg_commands"] = [{
        "command": ["placeholder_test"],
        "provider": "placeholder_test_assembly_generator",
        "strategy": "placeholder_test",
        "return_code": 0,
        "stdout_excerpt": "placeholder rough cut generated",
        "stderr_excerpt": "",
        "ran_at": "2026-05-31T00:00:00+00:00",
    }]
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    output_path = Path(data["final_output_path"])

    def fake_run(cmd: list[str], text: bool, stdout: int, stderr: int) -> SimpleNamespace:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"\x00\x00\x00\x18ftypmp42ROUGH" + (b"9" * 4096))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(assemble_with_ffmpeg, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(assemble_with_ffmpeg.subprocess, "run", fake_run)
    assert assemble_with_ffmpeg.main([str(manifest_path)]) == 0

    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(updated, manifest_path, mode="final")
    assert ok, errors
    assert warnings == []
    assert updated["status"] == "generated"
    assert updated["assembly_provider"] == "ffmpeg"
    assert len(updated["ffmpeg_commands"]) == 1
    assert updated["ffmpeg_commands"][0]["provider"] == "ffmpeg"
    review_text = (manifest_path.parent / "assembly_review.md").read_text(encoding="utf-8")
    assert "状态：`generated`" in review_text
    assert "fallback 关键帧补段数" in review_text


def test_placeholder_mode_records_final_evidence_and_command(tmp_path: Path) -> None:
    manifest_path = _prepare_manifest(tmp_path)
    assert assemble_with_ffmpeg.main([str(manifest_path), "--placeholder-test"]) == 0
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    ok, errors, warnings = validate_assembly_manifest.validate(data, manifest_path, mode="final")
    assert not ok
    assert any("placeholder" in error or "too small" in error for error in errors)
    assert data["ffmpeg_commands"][0]["strategy"] == "placeholder_test"
    assert data["self_check"]["ready_for_qa_stage"] is False


def test_assemble_with_ffmpeg_blocks_when_requested_scope_stops_earlier(tmp_path: Path) -> None:
    manifest_path = _prepare_manifest(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["compiled_requirements"] = {"requested_output_scope": "video_clips"}
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    assert assemble_with_ffmpeg.main([str(manifest_path), "--placeholder-test"]) == 1
    assert assemble_with_ffmpeg.main([str(manifest_path), "--placeholder-test", "--allow-beyond-requested-scope"]) == 0
