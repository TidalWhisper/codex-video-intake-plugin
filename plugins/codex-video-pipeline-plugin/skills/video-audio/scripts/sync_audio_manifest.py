#!/usr/bin/env python3
"""Sync Stage 07 audio manifest evidence from files on disk."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def resolve(base: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p
    return (base.parent / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--provider", default=None, help="Optional provider to set for existing audio, e.g. indextts2 or manual")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    generated_voice = generated_music = generated_total = failed = 0
    voice_jobs = music_jobs = 0
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        audio_type = job.get("audio_type")
        if audio_type in {"voiceover", "dialogue"}:
            voice_jobs += 1
        if audio_type == "music":
            music_jobs += 1
        raw = job.get("output_path") or job.get("evidence", {}).get("file_path")
        if not raw:
            failed += 1
            continue
        audio = resolve(path, str(raw))
        ev = job.setdefault("evidence", {})
        ev["file_path"] = str(audio).replace("\\", "/")
        if audio.exists() and audio.is_file() and audio.stat().st_size > 0:
            ev["file_exists"] = True
            ev["file_size_bytes"] = audio.stat().st_size
            ev["created_at"] = datetime.fromtimestamp(audio.stat().st_mtime, timezone.utc).isoformat()
            job["status"] = "succeeded"
            if args.provider and not job.get("provider"):
                job["provider"] = args.provider
            generated_total += 1
            if audio_type in {"voiceover", "dialogue"}:
                generated_voice += 1
            if audio_type == "music":
                generated_music += 1
        else:
            ev["file_exists"] = False
            ev["file_size_bytes"] = 0
            if job.get("status") == "succeeded":
                job["status"] = "failed"
            failed += 1
    jobs = data.get("jobs") or []
    summary = data.setdefault("summary", {})
    summary["expected_voice_count"] = voice_jobs
    summary["generated_voice_count"] = generated_voice
    summary["expected_music_count"] = music_jobs
    summary["generated_music_count"] = generated_music
    summary["required_audio_count"] = len(jobs)
    summary["generated_audio_count"] = generated_total
    req = data.get("requirements") if isinstance(data.get("requirements"), dict) else {}
    self_check = data.setdefault("self_check", {})
    self_check["has_voice_tracks_for_required_lines"] = (not req.get("voice_required")) or voice_jobs > 0
    self_check["has_music_when_required"] = (not req.get("music_required")) or music_jobs > 0
    all_audio = generated_total == len(jobs) and (len(jobs) > 0 or (not req.get("voice_required") and not req.get("music_required")))
    self_check["all_required_audio_files_exist"] = all_audio
    self_check["ready_for_assembly_stage"] = all_audio
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if all_audio:
        data["allowed_next_stage"] = "STAGE_08_ASSEMBLY"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"AUDIO MANIFEST SYNCED: {path}")
    print(f"GENERATED_AUDIO: {generated_total}")
    print(f"FAILED_OR_MISSING_AUDIO: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
