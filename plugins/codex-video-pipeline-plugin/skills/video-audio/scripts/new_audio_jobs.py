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


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
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


def parse_requirements(brief: dict) -> dict:
    n = norm(brief)
    voice_mode = str(n.get("voice_mode") or brief.get("voice_mode") or "")
    music_mode = str(n.get("music_mode") or brief.get("music_mode") or "")
    voice_required = is_truthy(n.get("voice_required", brief.get("voice_required", False)))
    music_required = is_truthy(n.get("music_required", brief.get("music_required", False)))
    include_voiceover = voice_required and ("旁白" in voice_mode or "voiceover" in voice_mode.lower() or not voice_mode)
    include_dialogue = voice_required and ("对白" in voice_mode or "dialogue" in voice_mode.lower())
    return {
        "voice_required": voice_required,
        "music_required": music_required,
        "voice_mode": voice_mode,
        "music_mode": music_mode,
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


def parse_dialogue_lines(raw: str) -> list[str]:
    raw = safe_text(raw)
    if not raw:
        return []
    # Split common separators but keep simple single-line dialogue intact.
    parts = [p.strip() for p in re.split(r"[\n；;]+", raw) if p.strip()]
    return parts or [raw]


def request_record(job: dict, provider: str) -> dict:
    return {
        "request_id": f"REQ_{provider.upper()}_{job['audio_id']}",
        "audio_id": job["audio_id"],
        "audio_type": job["audio_type"],
        "shot_id": job.get("shot_id"),
        "provider": provider,
        "text": job.get("text"),
        "music_prompt": job.get("music_prompt"),
        "emotion": job.get("emotion"),
        "target_start": job.get("target_start"),
        "target_end": job.get("target_end"),
        "duration_sec": job.get("duration_sec"),
        "output_path": job.get("output_path"),
        "status": "planned"
    }


def main(argv: list[str]) -> int:
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
    if clip_manifest.get("stage") != "STAGE_06_VIDEO_CLIPS":
        print("ERROR: video_clip_manifest.stage must be STAGE_06_VIDEO_CLIPS", file=sys.stderr)
        return 1
    if not (clip_manifest.get("self_check") or {}).get("ready_for_audio_stage"):
        print("ERROR: video_clip_manifest.self_check.ready_for_audio_stage must be true before Stage 07", file=sys.stderr)
        return 1

    requirements = parse_requirements(brief)
    project_id = brief.get("project_id") or storyboard.get("project_id") or clip_manifest.get("project_id") or out_path.parents[1].name
    voice_dir = out_path.parent / "voice"
    music_dir = out_path.parent / "music"
    voice_dir.mkdir(parents=True, exist_ok=True)
    music_dir.mkdir(parents=True, exist_ok=True)

    profiles = character_voice_profile(character_bible)
    narrator = pick_narrator_profile(profiles)
    jobs = []

    if requirements["voice_required"]:
        for shot in storyboard.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            shot_id = shot.get("shot_id") or "S000"
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
                        "source_storyboard_ref": f"{str(storyboard_path).replace('\\', '/') }#{shot_id}",
                        "source_script_ref": str(script_path).replace("\\", "/"),
                        "speaker_id": narrator.get("character_id") or "NARRATOR",
                        "speaker_name": narrator.get("name") or "旁白",
                        "text": vo,
                        "emotion": emotion,
                        "voice_profile": narrator.get("voice_profile") or {},
                        "target_start": shot.get("start"),
                        "target_end": shot.get("end"),
                        "duration_sec": duration,
                        "provider_priority": ["indextts2", "manual"],
                        "provider": None,
                        "status": "pending",
                        "output_path": str(out).replace("\\", "/"),
                        "evidence": {"file_path": str(out).replace("\\", "/"), "file_exists": out.exists(), "file_size_bytes": out.stat().st_size if out.exists() else 0, "created_at": None},
                        "errors": [],
                        "notes": ""
                    })
            if requirements["include_dialogue"]:
                for idx, line in enumerate(parse_dialogue_lines(shot.get("dialogue")), start=1):
                    out = voice_dir / f"{shot_id}_dialogue_{idx:03d}.wav"
                    jobs.append({
                        "audio_id": job_id("dialogue", shot_id, idx),
                        "audio_type": "dialogue",
                        "shot_id": shot_id,
                        "source_storyboard_ref": f"{str(storyboard_path).replace('\\', '/') }#{shot_id}",
                        "source_script_ref": str(script_path).replace("\\", "/"),
                        "speaker_id": "CHAR_001",
                        "speaker_name": "角色对白",
                        "text": line,
                        "emotion": emotion,
                        "voice_profile": next(iter(profiles.values())).get("voice_profile") or {},
                        "target_start": shot.get("start"),
                        "target_end": shot.get("end"),
                        "duration_sec": duration,
                        "provider_priority": ["indextts2", "manual"],
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
            "source_storyboard_ref": str(storyboard_path).replace("\\", "/"),
            "source_script_ref": str(script_path).replace("\\", "/"),
            "speaker_id": None,
            "speaker_name": None,
            "text": "",
            "music_prompt": music_prompt,
            "emotion": "整体背景音乐",
            "voice_profile": {},
            "target_start": "00:00",
            "target_end": None,
            "duration_sec": float(target_duration or 0),
            "provider_priority": ["local_music_library", "comfyui_music", "manual"],
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
        "voice_provider_strategy": {"primary": "indextts2", "fallback": ["manual"], "execution_mode": "provider_or_manual"},
        "music_provider_strategy": {"primary": "local_music_library", "fallback": ["comfyui_music", "manual"], "execution_mode": "provider_or_manual"},
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
        f"Expected voice jobs: {len(voice_jobs)}\n\n"
        f"Expected music jobs: {len(music_jobs)}\n\n"
        "Do not mark Stage 07 complete until `audio_manifest.json` passes final validation.\n",
        encoding="utf-8"
    )
    (out_path.parent / "audio_review.md").write_text(
        "# Stage 07 Audio Review\n\nPending generation. After voice/music files are created, run `sync_audio_manifest.py` and final validation.\n",
        encoding="utf-8"
    )
    print(f"AUDIO JOBS CREATED: {out_path}")
    print(f"EXPECTED_AUDIO_JOBS: {len(jobs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
