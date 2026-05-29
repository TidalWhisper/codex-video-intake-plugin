#!/usr/bin/env python3
"""Validate Stage 07 audio manifest.

Final mode requires every required voice/music job to have status=succeeded and a real existing non-empty audio file.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

KNOWN_PLUGIN_ROOT_CHILDREN = {
    "video_projects",
    "templates",
    "config",
    "workflows",
    "skills",
    "scripts",
    "tests",
    "docs",
    "prompts",
}

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_script", "source_storyboard",
    "source_character_bible", "source_video_clip_manifest", "requirements", "voice_provider_strategy", "music_provider_strategy",
    "output_root", "voice_dir", "music_dir", "jobs", "summary", "self_check", "allowed_next_stage"
]
REQUIRED_JOB = [
    "audio_id", "audio_type", "shot_id", "text", "provider_priority", "provider", "status", "output_path", "evidence", "errors", "notes"
]
AUDIO_ID_RE = re.compile(r"^AUD_(VOICEOVER|DIALOGUE|MUSIC)_[A-Z0-9_]+$")
SHOT_ID_RE = re.compile(r"^S\d{3}$")
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def detect_audio_container(path: Path) -> str | None:
    try:
        header = path.read_bytes()[:16]
    except OSError:
        return None
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return "wav"
    if header[:4] == b"fLaC":
        return "flac"
    if header[:4] == b"OggS":
        return "ogg"
    if header[:3] == b"ID3":
        return "mp3"
    if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return "mp3_or_aac"
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "mp4_family"
    return None


def resolve_path(base_json: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    special_roots: list[Path] = []
    plugin_root = next(
        (anchor.resolve() for anchor in [base_json.parent, *base_json.parents] if anchor.name == "codex-video-pipeline-plugin"),
        None,
    )
    repo_root = plugin_root.parent.parent.resolve() if plugin_root and plugin_root.parent.name == "plugins" else None
    if p.parts:
        first = p.parts[0].lower()
        if first == "plugins" and repo_root is not None:
            special_roots.append(repo_root)
        elif first in KNOWN_PLUGIN_ROOT_CHILDREN and plugin_root is not None:
            special_roots.append(plugin_root)
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [*special_roots, Path.cwd(), base_json.parent, *base_json.parents]:
        key = str(anchor.resolve()).lower()
        if key not in seen:
            anchors.append(anchor)
            seen.add(key)
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.exists():
            return candidate
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.parent.exists():
            return candidate
    return (base_json.parent / p).resolve()


def validate(data: dict[str, Any], path: Path | None = None, mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = path or Path("audio_manifest.json")

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_07_AUDIO":
        errors.append("stage must be STAGE_07_AUDIO")
    if data.get("status") not in {"draft", "in_progress", "generated", "confirmed"}:
        errors.append("status must be draft, in_progress, generated, or confirmed")
    if is_blank(data.get("project_id")):
        errors.append("project_id must not be blank")

    requirements = data.get("requirements") if isinstance(data.get("requirements"), dict) else {}
    voice_required = requirements.get("voice_required") is True
    music_required = requirements.get("music_required") is True
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    if not isinstance(data.get("jobs"), list):
        errors.append("jobs must be a list")
    if mode == "final" and (voice_required or music_required) and not jobs:
        errors.append("jobs must not be empty in final mode when voice or music is required")

    generated_voice = generated_music = generated_total = 0
    voice_jobs = music_jobs = 0
    for idx, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"jobs[{idx}] must be an object")
            continue
        for key in REQUIRED_JOB:
            if key not in job:
                errors.append(f"jobs[{idx}] missing key: {key}")
        audio_id = job.get("audio_id")
        audio_type = job.get("audio_type")
        if not isinstance(audio_id, str) or not AUDIO_ID_RE.match(audio_id):
            errors.append(f"jobs[{idx}].audio_id has invalid format")
        if audio_type not in {"voiceover", "dialogue", "music", "ambient"}:
            errors.append(f"jobs[{idx}].audio_type must be voiceover, dialogue, music, or ambient")
        if audio_type in {"voiceover", "dialogue"}:
            voice_jobs += 1
            shot_id = job.get("shot_id")
            if not isinstance(shot_id, str) or not SHOT_ID_RE.match(shot_id):
                errors.append(f"jobs[{idx}].shot_id must match S### for voice jobs")
            if mode == "final" and is_blank(job.get("text")):
                errors.append(f"jobs[{idx}].text must not be blank for voice jobs in final mode")
        if audio_type == "music":
            music_jobs += 1
            if mode == "final" and is_blank(job.get("music_prompt")):
                errors.append(f"jobs[{idx}].music_prompt must not be blank for music jobs in final mode")
        if not isinstance(job.get("provider_priority"), list) or not job.get("provider_priority"):
            errors.append(f"jobs[{idx}].provider_priority must be a non-empty list")
        try:
            duration = float(job.get("duration_sec") or 0)
        except Exception:
            errors.append(f"jobs[{idx}].duration_sec must be numeric")
            duration = 0
        if mode == "final" and audio_type in {"voiceover", "dialogue", "music"} and duration <= 0:
            errors.append(f"jobs[{idx}].duration_sec must be positive in final mode")
        if mode == "final":
            if is_blank(job.get("provider")):
                errors.append(f"jobs[{idx}].provider must not be blank in final mode")
            if job.get("status") != "succeeded":
                errors.append(f"jobs[{idx}].status must be succeeded in final mode")
            evidence = job.get("evidence")
            if not isinstance(evidence, dict):
                errors.append(f"jobs[{idx}].evidence must be an object")
                continue
            file_path = evidence.get("file_path") or job.get("output_path")
            resolved = resolve_path(manifest_path, file_path)
            if resolved is None:
                errors.append(f"jobs[{idx}].evidence.file_path must not be blank")
                continue
            if resolved.suffix.lower() not in AUDIO_EXTS:
                errors.append(f"jobs[{idx}] audio file extension must be one of {sorted(AUDIO_EXTS)}: {resolved}")
            if not resolved.exists():
                errors.append(f"jobs[{idx}] audio file does not exist: {resolved}")
            elif not resolved.is_file():
                errors.append(f"jobs[{idx}] audio path is not a file: {resolved}")
            else:
                size = resolved.stat().st_size
                if size <= 0:
                    errors.append(f"jobs[{idx}] audio file is empty: {resolved}")
                else:
                    detected_container = detect_audio_container(resolved)
                    if resolved.suffix.lower() == ".wav" and detected_container not in {None, "wav"}:
                        errors.append(
                            f"jobs[{idx}] audio file has .wav extension but detected container is {detected_container}: {resolved}"
                        )
                    generated_total += 1
                    if audio_type in {"voiceover", "dialogue"}:
                        generated_voice += 1
                    if audio_type == "music":
                        generated_music += 1
                if evidence.get("file_exists") is not True:
                    errors.append(f"jobs[{idx}].evidence.file_exists must be true")
                if not isinstance(evidence.get("file_size_bytes"), int) or evidence.get("file_size_bytes") <= 0:
                    errors.append(f"jobs[{idx}].evidence.file_size_bytes must be a positive integer")

    if voice_required and mode == "final" and voice_jobs == 0:
        errors.append("voice_required=true but no voice jobs exist")
    if music_required and mode == "final" and music_jobs == 0:
        errors.append("music_required=true but no music jobs exist")

    summary = data.get("summary")
    if isinstance(summary, dict):
        if summary.get("expected_voice_count") != voice_jobs:
            errors.append("summary.expected_voice_count must equal number of voice jobs")
        if summary.get("expected_music_count") != music_jobs:
            errors.append("summary.expected_music_count must equal number of music jobs")
        if summary.get("required_audio_count") != len(jobs):
            errors.append("summary.required_audio_count must equal len(jobs)")
        if mode == "final":
            if summary.get("generated_voice_count") != generated_voice:
                errors.append("summary.generated_voice_count must equal generated voice file count")
            if summary.get("generated_music_count") != generated_music:
                errors.append("summary.generated_music_count must equal generated music file count")
            if summary.get("generated_audio_count") != generated_total:
                errors.append("summary.generated_audio_count must equal generated audio file count")
    self_check = data.get("self_check")
    if isinstance(self_check, dict) and mode == "final":
        checks = ["all_required_audio_files_exist", "ready_for_assembly_stage"]
        if voice_required:
            checks.append("has_voice_tracks_for_required_lines")
        if music_required:
            checks.append("has_music_when_required")
        for key in checks:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")
    quality_signals = data.get("quality_signals")
    if mode == "final":
        if not isinstance(quality_signals, dict):
            errors.append("quality_signals must be an object in final mode")
        else:
            for key in ["intent_route_matches_strategy", "voice_direction_present", "music_profile_matches_strategy", "quality_targets_defined"]:
                if quality_signals.get(key) is not True:
                    errors.append(f"quality_signals.{key} must be true in final mode")
    if mode == "draft" and jobs:
        warnings.append("draft audio manifest contains planned jobs; final mode still requires generated audio files")
    return not errors, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--mode", choices=["draft", "final"], default="final")
    args = parser.parse_args(argv)
    path = Path(args.manifest_json)
    data = load_json(path)
    ok, errors, warnings = validate(data, path, args.mode)
    if warnings:
        print("AUDIO MANIFEST VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"AUDIO MANIFEST VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"AUDIO MANIFEST VALIDATION PASSED ({args.mode} mode): {args.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
