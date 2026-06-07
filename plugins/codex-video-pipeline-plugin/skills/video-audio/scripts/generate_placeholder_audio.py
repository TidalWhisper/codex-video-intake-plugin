#!/usr/bin/env python3
"""Generate small placeholder WAV files for Stage 07 local pipeline testing.

This is only for testing the pipeline and validators. It is not a production voice/music generator.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402


def write_wav(path: Path, duration_sec: float, frequency: float = 440.0, sample_rate: int = 8000) -> None:
    duration_sec = max(0.25, min(float(duration_sec or 1.0), 3.0))
    frames = int(sample_rate * duration_sec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(frames):
            sample = int(32767 * 0.08 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wf.writeframesraw(sample.to_bytes(2, "little", signed=True))


def resolve_output_path(manifest_path: Path, raw: str) -> Path:
    path = Path(str(raw))
    if path.is_absolute():
        return path
    if path.exists():
        return path
    return (manifest_path.parent / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    generated = generated_voice = generated_music = 0
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        out = resolve_output_path(path, job.get("output_path") or job.get("evidence", {}).get("file_path") or "")
        audio_type = job.get("audio_type")
        freq = 330.0 if audio_type == "music" else 520.0
        write_wav(out, job.get("duration_sec") or 1.0, freq)
        job["provider"] = "placeholder_test_audio_generator"
        job["status"] = "succeeded"
        job.setdefault("evidence", {})
        job["evidence"].update({
            "file_path": str(out).replace("\\", "/"),
            "file_exists": True,
            "file_size_bytes": out.stat().st_size,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        generated += 1
        if audio_type in {"voiceover", "dialogue"}:
            generated_voice += 1
        if audio_type == "music":
            generated_music += 1
    jobs = data.get("jobs") or []
    data.setdefault("summary", {})
    data["summary"].update({
        "expected_voice_count": sum(1 for j in jobs if isinstance(j, dict) and j.get("audio_type") in {"voiceover", "dialogue"}),
        "generated_voice_count": generated_voice,
        "expected_music_count": sum(1 for j in jobs if isinstance(j, dict) and j.get("audio_type") == "music"),
        "generated_music_count": generated_music,
        "required_audio_count": len(jobs),
        "generated_audio_count": generated,
    })
    req = data.get("requirements") if isinstance(data.get("requirements"), dict) else {}
    data.setdefault("self_check", {})
    all_generated = generated == len(jobs)
    data["self_check"].update({
        "has_voice_tracks_for_required_lines": (not req.get("voice_required")) or data["summary"]["expected_voice_count"] > 0,
        "has_music_when_required": (not req.get("music_required")) or data["summary"]["expected_music_count"] > 0,
        "all_required_audio_files_exist": all_generated,
        "ready_for_assembly_stage": all_generated,
    })
    data["status"] = "generated" if all_generated else ("in_progress" if generated > 0 else "draft")
    data["allowed_next_stage"] = next_stage_after("STAGE_07_AUDIO", routing, "STAGE_08_ASSEMBLY") if all_generated else None
    data["confirmed_by_user"] = False
    if all_generated:
        data["formal_promotion_status"] = "pending_confirmation"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if all_generated:
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_07_AUDIO",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"audio_confirmed": False},
            status="active",
        )
    print(f"PLACEHOLDER AUDIO GENERATED: {generated}/{len(jobs)}")
    print(f"MANIFEST UPDATED: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
