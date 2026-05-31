#!/usr/bin/env python3
"""Create Stage 07 voice/music audio jobs from brief, script, storyboard, characters, and video clips.

Usage:
  python new_audio_jobs.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json> <video_clip_manifest.json> <audio_manifest.json>
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402
from pipeline_core.quality_contracts import build_quality_contract, build_stage_quality_targets  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage, stage_meets_requested_output  # noqa: E402
from pipeline_core.story_continuity import build_continuity_anchor_text, pick_story_anchors, shot_anchor_bundle, style_label_from_sources  # noqa: E402


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def norm(brief: dict) -> dict:
    n = brief.get("normalized")
    return n if isinstance(n, dict) else brief


def is_truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "yes", "y", "1", "需要", "是", "旁白", "对白"}
    return bool(v)


MUSIC_PROFILE_ALIASES = {
    "song": "song",
    "vocal": "song",
    "lyrics": "song",
    "instrumental": "instrumental",
    "pure_music": "instrumental",
    "underscore": "underscore",
    "bgm": "underscore",
}

SONG_PROFILE_HINTS = ("歌词", "演唱", "人声", "主唱", "歌曲", "主题曲", "song", "vocal", "lyrics")
INSTRUMENTAL_PROFILE_HINTS = ("纯音乐", "纯器乐", "器乐", "instrumental", "pure music", "no vocal")
UNDERSCORE_PROFILE_HINTS = ("配乐", "铺底", "背景", "bgm", "underscore", "score")


def normalize_music_profile(value) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return MUSIC_PROFILE_ALIASES.get(raw, "")


def infer_music_profile(*values) -> str:
    joined = " ".join(str(value or "") for value in values).lower()
    if any(keyword in joined for keyword in SONG_PROFILE_HINTS):
        return "song"
    if any(keyword in joined for keyword in INSTRUMENTAL_PROFILE_HINTS):
        return "instrumental"
    if any(keyword in joined for keyword in UNDERSCORE_PROFILE_HINTS):
        return "underscore"
    return "underscore"


def parse_requirements(brief: dict) -> dict:
    n = norm(brief)
    voice_mode = str(n.get("voice_mode") or brief.get("voice_mode") or "")
    music_mode = str(n.get("music_mode") or brief.get("music_mode") or "")
    voice_required = is_truthy(n.get("voice_required", brief.get("voice_required", False)))
    music_required = is_truthy(n.get("music_required", brief.get("music_required", False)))
    explicit_music_profile = (
        normalize_music_profile(n.get("music_profile"))
        or normalize_music_profile(brief.get("music_profile"))
        or normalize_music_profile(n.get("acestep_profile"))
        or normalize_music_profile(brief.get("acestep_profile"))
    )
    music_profile = explicit_music_profile or infer_music_profile(music_mode)
    include_voiceover = voice_required and ("旁白" in voice_mode or "voiceover" in voice_mode.lower() or not voice_mode)
    include_dialogue = voice_required and ("对白" in voice_mode or "dialogue" in voice_mode.lower())
    return {
        "voice_required": voice_required,
        "music_required": music_required,
        "voice_mode": voice_mode,
        "music_mode": music_mode,
        "music_profile": music_profile,
        "include_voiceover": include_voiceover,
        "include_dialogue": include_dialogue,
        "target_duration_sec": n.get("target_duration_sec") or brief.get("target_duration_sec") or 0,
    }


def character_voice_profile(character_bible: dict) -> dict:
    profiles = {}
    for ch in character_bible.get("characters") or []:
        if not isinstance(ch, dict):
            continue
        cid = ch.get("character_id") or ch.get("name") or "CHAR_UNKNOWN"
        profiles[cid] = {
            "character_id": cid,
            "name": ch.get("name") or cid,
            "voice_profile": ch.get("voice_profile") or {},
            "emotional_arc": ch.get("emotional_arc") or [],
            "performance_profile": ch.get("performance_profile") or {},
        }
    if not profiles:
        profiles["NARRATOR"] = {"character_id": "NARRATOR", "name": "旁白", "voice_profile": {"suggested_voice": "清晰、自然、贴合影片情绪"}, "emotional_arc": []}
    return profiles


def pick_narrator_profile(profiles: dict) -> dict:
    for p in profiles.values():
        vp = p.get("voice_profile") or {}
        if vp.get("needed") is True:
            return p
    return {"character_id": "NARRATOR", "name": "旁白", "voice_profile": {"suggested_voice": "自然、清晰、贴合影片情绪"}, "emotional_arc": []}


def safe_text(s) -> str:
    return str(s or "").strip()


def job_id(kind: str, shot_id: str, index: int | None = None) -> str:
    if index is None:
        return f"AUD_{kind.upper()}_{shot_id}"
    return f"AUD_{kind.upper()}_{shot_id}_{index:03d}"


def parse_dialogue_lines(raw: str) -> list[dict]:
    raw = safe_text(raw)
    if not raw:
        return []
    # Split common separators but keep simple single-line dialogue intact.
    parts = [p.strip() for p in re.split(r"[\n；;]+", raw) if p.strip()]
    lines = parts or [raw]
    result = []
    for line in lines:
        speaker_hint = ""
        text = line
        if "：" in line:
            prefix, suffix = line.split("：", 1)
            if suffix.strip():
                speaker_hint = prefix.strip()
                text = suffix.strip()
        elif ":" in line:
            prefix, suffix = line.split(":", 1)
            if suffix.strip():
                speaker_hint = prefix.strip()
                text = suffix.strip()
        result.append({"speaker_hint": speaker_hint, "text": text})
    return result


def pick_speaker_profile(speaker_hint: str, profiles: dict, narrator: dict) -> dict:
    hint = safe_text(speaker_hint).lower()
    if hint:
        for profile in profiles.values():
            name = safe_text(profile.get("name")).lower()
            if not name:
                continue
            if hint == name or hint in name or name in hint:
                return profile
    for profile in profiles.values():
        if profile.get("character_id") != "NARRATOR":
            return profile
    return narrator


def request_record(job: dict, provider: str) -> dict:
    return {
        "request_id": f"REQ_{provider.upper()}_{job['audio_id']}",
        "audio_id": job["audio_id"],
        "audio_type": job["audio_type"],
        "shot_id": job.get("shot_id"),
        "provider": provider,
        "speaker_hint": job.get("speaker_hint"),
        "text": job.get("text"),
        "music_prompt": job.get("music_prompt"),
        "music_profile": job.get("music_profile"),
        "emotion": job.get("emotion"),
        "performance_prompt": job.get("performance_prompt"),
        "target_start": job.get("target_start"),
        "target_end": job.get("target_end"),
        "duration_sec": job.get("duration_sec"),
        "output_path": job.get("output_path"),
        "status": "planned"
    }


def performance_profile_for_bundle(profile: dict, anchors: dict, bundle: dict[str, str], style_label: str) -> dict:
    result = dict(profile or {})
    result["baseline_expression"] = bundle.get("emotion") or result.get("baseline_expression") or "平静"
    scene_label = f"{bundle.get('weather') or ''}{bundle.get('location') or anchors.get('scene_label') or ''}".strip() or anchors.get("scene_label") or "当前场景"
    key_props = [bundle.get("key_prop")] if bundle.get("key_prop") else (anchors.get("key_props") or [])
    result["continuity_anchor"] = build_continuity_anchor_text(
        anchors.get("subject") or "主体",
        scene_label,
        style_label,
        key_props,
    )
    return result


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 7:
        print("Usage: python new_audio_jobs.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json> <video_clip_manifest.json> <audio_manifest.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    character_path = Path(argv[4])
    clip_manifest_path = Path(argv[5])
    out_path = Path(argv[6])

    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    character_bible = load_json(character_path)
    clip_manifest = load_json(clip_manifest_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_07", compiled):
        print("ERROR: requested output scope does not allow Stage 07. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if clip_manifest.get("stage") != "STAGE_06_VIDEO_CLIPS":
        print("ERROR: video_clip_manifest.stage must be STAGE_06_VIDEO_CLIPS", file=sys.stderr)
        return 1
    if not (clip_manifest.get("self_check") or {}).get("ready_for_audio_stage"):
        print("ERROR: video_clip_manifest.self_check.ready_for_audio_stage must be true before Stage 07", file=sys.stderr)
        print(
            "CREATOR_HINT: 当前视频片段还只是草稿、占位结果，或者上游 Stage 05 还没正式过审。"
            " 请先把 Stage 06 补成真实可用 clip，再继续音频阶段。",
            file=sys.stderr,
        )
        return 1

    requirements = parse_requirements(brief)
    routing = routing_from_brief(brief)
    quality_contract = build_quality_contract(brief, compiled)
    quality_targets = build_stage_quality_targets("STAGE_07", quality_contract)
    anchors = pick_story_anchors(brief, max(1, len(storyboard.get("shots") or [])), character_bible, storyboard)
    style_label = style_label_from_sources(brief, character_bible, storyboard, clip_manifest)
    voice_provider_priority = list((compiled.get("provider_preferences") or {}).get("stage07_voice_provider_priority") or ["indextts2", "manual"])
    music_provider_priority = list((compiled.get("provider_preferences") or {}).get("stage07_music_provider_priority") or ["comfyui_music", "local_music_library", "manual"])
    project_id = brief.get("project_id") or storyboard.get("project_id") or clip_manifest.get("project_id") or out_path.parents[1].name
    voice_dir = out_path.parent / "voice"
    music_dir = out_path.parent / "music"
    voice_dir.mkdir(parents=True, exist_ok=True)
    music_dir.mkdir(parents=True, exist_ok=True)

    profiles = character_voice_profile(character_bible)
    narrator = pick_narrator_profile(profiles)
    jobs = []
    storyboard_ref = str(storyboard_path).replace("\\", "/")
    script_ref = str(script_path).replace("\\", "/")

    if requirements["voice_required"]:
        for shot in storyboard.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            shot_id = shot.get("shot_id") or "S000"
            bundle = shot_anchor_bundle(anchors, len(jobs), shot=shot)
            emotion = safe_text(shot.get("emotion"))
            duration = shot.get("duration_sec") or 0
            try:
                duration = float(duration)
            except Exception:
                duration = 0
            if requirements["include_voiceover"]:
                vo = safe_text(shot.get("voiceover"))
                if vo:
                    out = voice_dir / f"{shot_id}_voiceover.wav"
                    jobs.append({
                        "audio_id": job_id("voiceover", shot_id),
                        "audio_type": "voiceover",
                        "shot_id": shot_id,
                        "source_storyboard_ref": f"{storyboard_ref}#{shot_id}",
                        "source_script_ref": script_ref,
                        "speaker_id": "NARRATOR",
                        "speaker_name": "旁白",
                        "text": vo,
                        "emotion": emotion,
                        "voice_profile": narrator.get("voice_profile") or {},
                        "performance_prompt": performance_profile_for_bundle(narrator.get("performance_profile") or {}, anchors, bundle, style_label),
                        "story_anchor_bundle": bundle,
                        "target_start": shot.get("start"),
                        "target_end": shot.get("end"),
                        "duration_sec": duration,
                        "provider_priority": voice_provider_priority,
                        "provider": None,
                        "status": "pending",
                        "output_path": str(out).replace("\\", "/"),
                        "evidence": {"file_path": str(out).replace("\\", "/"), "file_exists": out.exists(), "file_size_bytes": out.stat().st_size if out.exists() else 0, "created_at": None},
                        "errors": [],
                        "notes": ""
                    })
            if requirements["include_dialogue"]:
                for idx, line in enumerate(parse_dialogue_lines(shot.get("dialogue")), start=1):
                    speaker = pick_speaker_profile(line.get("speaker_hint") or "", profiles, narrator)
                    out = voice_dir / f"{shot_id}_dialogue_{idx:03d}.wav"
                    jobs.append({
                        "audio_id": job_id("dialogue", shot_id, idx),
                        "audio_type": "dialogue",
                        "shot_id": shot_id,
                        "source_storyboard_ref": f"{storyboard_ref}#{shot_id}",
                        "source_script_ref": script_ref,
                        "speaker_id": speaker.get("character_id") or "CHAR_001",
                        "speaker_name": speaker.get("name") or "角色对白",
                        "speaker_hint": line.get("speaker_hint") or "",
                        "text": line.get("text") or "",
                        "emotion": emotion,
                        "voice_profile": speaker.get("voice_profile") or {},
                        "performance_prompt": performance_profile_for_bundle(speaker.get("performance_profile") or {}, anchors, bundle, style_label),
                        "story_anchor_bundle": bundle,
                        "target_start": shot.get("start"),
                        "target_end": shot.get("end"),
                        "duration_sec": duration,
                        "provider_priority": voice_provider_priority,
                        "provider": None,
                        "status": "pending",
                        "output_path": str(out).replace("\\", "/"),
                        "evidence": {"file_path": str(out).replace("\\", "/"), "file_exists": out.exists(), "file_size_bytes": out.stat().st_size if out.exists() else 0, "created_at": None},
                        "errors": [],
                        "notes": ""
                    })

    if requirements["music_required"]:
        target_duration = requirements.get("target_duration_sec") or storyboard.get("target_duration_sec") or clip_manifest.get("summary", {}).get("total_duration_sec") or 0
        sound_notes = [safe_text(s.get("sound_music")) for s in storyboard.get("shots") or [] if isinstance(s, dict) and safe_text(s.get("sound_music"))]
        music_prompt = "；".join(sound_notes[:6]) or "根据影片情绪生成背景音乐"
        out = music_dir / "BGM_MAIN.wav"
        jobs.append({
            "audio_id": "AUD_MUSIC_BGM_MAIN",
            "audio_type": "music",
            "shot_id": None,
            "source_storyboard_ref": storyboard_ref,
            "source_script_ref": script_ref,
            "speaker_id": None,
            "speaker_name": None,
            "text": "",
            "music_prompt": music_prompt,
            "emotion": "整体背景音乐",
            "voice_profile": {},
            "target_start": "00:00",
            "target_end": None,
            "duration_sec": float(target_duration or 0),
            "music_profile": requirements["music_profile"],
            "provider_priority": music_provider_priority,
            "provider": None,
            "status": "pending",
            "output_path": str(out).replace("\\", "/"),
            "evidence": {"file_path": str(out).replace("\\", "/"), "file_exists": out.exists(), "file_size_bytes": out.stat().st_size if out.exists() else 0, "created_at": None},
            "errors": [],
            "notes": ""
        })

    voice_jobs = [j for j in jobs if j["audio_type"] in {"voiceover", "dialogue"}]
    music_jobs = [j for j in jobs if j["audio_type"] == "music"]
    manifest = {
        "schema_version": "0.8.0",
        "stage": "STAGE_07_AUDIO",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_script": str(script_path).replace("\\", "/"),
        "source_storyboard": str(storyboard_path).replace("\\", "/"),
        "source_character_bible": str(character_path).replace("\\", "/"),
        "source_video_clip_manifest": str(clip_manifest_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "requirements": requirements,
        "story_anchors": anchors,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing,
        "voice_provider_strategy": {"primary": voice_provider_priority[0], "fallback": voice_provider_priority[1:], "execution_mode": "provider_or_manual"},
        "music_provider_strategy": {
            "primary": music_provider_priority[0] if music_provider_priority else "manual",
            "fallback": music_provider_priority[1:] if len(music_provider_priority) > 1 else [],
            "execution_mode": "provider_or_manual",
            "default_profile": requirements["music_profile"],
            "prompt_builder": "acestep",
        },
        "output_root": str(out_path.parent).replace("\\", "/"),
        "voice_dir": str(voice_dir).replace("\\", "/"),
        "music_dir": str(music_dir).replace("\\", "/"),
        "jobs": jobs,
        "summary": {
            "expected_voice_count": len(voice_jobs),
            "generated_voice_count": sum(1 for j in voice_jobs if j["evidence"]["file_exists"]),
            "expected_music_count": len(music_jobs),
            "generated_music_count": sum(1 for j in music_jobs if j["evidence"]["file_exists"]),
            "required_audio_count": len(jobs),
            "generated_audio_count": sum(1 for j in jobs if j["evidence"]["file_exists"]),
            "total_voice_duration_sec": sum(float(j.get("duration_sec") or 0) for j in voice_jobs),
            "target_total_duration_sec": requirements.get("target_duration_sec") or storyboard.get("target_duration_sec") or 0,
        },
        "quality_signals": {
            "intent_route_matches_strategy": routing.get("legacy_mode") or requested_output_allows_stage("STAGE_07", compiled),
            "voice_direction_present": all(bool(j.get("voice_profile")) or bool(j.get("performance_prompt")) for j in voice_jobs) if voice_jobs else True,
            "music_profile_matches_strategy": (not music_jobs) or all(j.get("music_profile") == requirements["music_profile"] for j in music_jobs),
            "quality_targets_defined": bool(quality_targets),
        },
        "self_check": {
            "has_voice_tracks_for_required_lines": (not requirements["voice_required"]) or bool(voice_jobs),
            "has_music_when_required": (not requirements["music_required"]) or bool(music_jobs),
            "all_required_audio_files_exist": False if jobs else True,
            "ready_for_assembly_stage": False if jobs else True,
            "notes": []
        },
        "allowed_next_stage": None
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "audio_jobs.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "indextts2_requests.json").write_text(json.dumps({"provider": "indextts2", "requests": [request_record(j, "indextts2") for j in voice_jobs]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "music_requests.json").write_text(json.dumps({"provider": "music", "requests": [request_record(j, j["provider_priority"][0]) for j in music_jobs]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "audio_plan.md").write_text(
        "# Stage 07 Audio Plan\n\n"
        f"Project: `{project_id}`\n\n"
        f"Voice required: {requirements['voice_required']} ({requirements['voice_mode']})\n\n"
        f"Music required: {requirements['music_required']} ({requirements['music_mode']})\n\n"
        f"AceStep music profile: {requirements['music_profile']}\n\n"
        f"Expected voice jobs: {len(voice_jobs)}\n\n"
        f"Expected music jobs: {len(music_jobs)}\n\n"
        "Do not mark Stage 07 complete until `audio_manifest.json` passes final validation.\n",
        encoding="utf-8"
    )
    (out_path.parent / "audio_review.md").write_text(
        "# Stage 07 Audio Review\n\nPending generation. After voice/music files are created, run `sync_audio_manifest.py` and final validation.\n",
        encoding="utf-8"
    )
    update_project_manifest_for_stage(
        out_path,
        current_stage="STAGE_07_AUDIO",
        allowed_next_stage=None,
        flags={"audio_confirmed": False},
        status="active",
    )
    print(f"AUDIO JOBS CREATED: {out_path}")
    print(f"EXPECTED_AUDIO_JOBS: {len(jobs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
