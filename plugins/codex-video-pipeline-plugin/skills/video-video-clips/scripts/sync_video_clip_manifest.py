#!/usr/bin/env python3
"""Sync Stage 06 video clip manifest evidence from files on disk."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.media_evidence import clip_output_ready  # noqa: E402
from pipeline_core.project_state import annotate_evidence_origin, update_project_manifest_for_stage  # noqa: E402


def resolve(base: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [Path.cwd(), base.parent, *base.parents]:
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
    return (base.parent / p).resolve()


def resolve_from_source(base_json: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    p = Path(str(raw))
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [Path.cwd(), base_json.parent, *base_json.parents]:
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


def stage05_formal_progression_ready(base_json: Path, data: dict[str, object]) -> bool:
    source_manifest_path = resolve_from_source(base_json, str(data.get("source_keyframe_image_manifest") or ""))
    if source_manifest_path is None or not source_manifest_path.exists() or not source_manifest_path.is_file():
        return False
    try:
        source_data = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    self_check = source_data.get("self_check") if isinstance(source_data.get("self_check"), dict) else {}
    return bool(self_check.get("ready_for_video_clip_generation"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--provider", default=None, help="Optional provider to set for existing clips, e.g. comfyui_ltx_i2v or manual")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    strategy = data.get("video_provider_strategy") if isinstance(data.get("video_provider_strategy"), dict) else {}
    primary_provider = str(strategy.get("primary") or "").strip() or None
    fallback_providers = [str(item).strip() for item in (strategy.get("fallback") or []) if str(item).strip()]
    generated = 0
    failed = 0
    blocked = 0
    source_ok = 0
    stage05_ready = stage05_formal_progression_ready(path, data)
    evidence_origin_summary = {
        "provider_output": 0,
        "fallback_output": 0,
        "manual_import": 0,
        "placeholder_or_incomplete": 0,
    }
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        # Source keyframe evidence
        keyframes = job.get("source_keyframes") if isinstance(job.get("source_keyframes"), dict) else {}
        start = resolve_from_source(path, keyframes.get("start"))
        end = resolve_from_source(path, keyframes.get("end"))
        if start and end and start.exists() and end.exists() and start.stat().st_size > 0 and end.stat().st_size > 0:
            source_ok += 1
        # Clip evidence
        raw = job.get("output_path") or job.get("evidence", {}).get("file_path")
        if job.get("status") == "blocked":
            blocked += 1
        if not raw:
            continue
        clip = resolve(path, str(raw))
        ev = job.setdefault("evidence", {})
        ev["file_path"] = str(clip).replace("\\", "/")
        if clip.exists() and clip.is_file():
            ev["file_exists"] = True
            ev["file_size_bytes"] = clip.stat().st_size
            ev["created_at"] = datetime.fromtimestamp(clip.stat().st_mtime, timezone.utc).isoformat()
            ready = clip_output_ready(clip, job.get("provider"))
            origin = annotate_evidence_origin(
                ev,
                provider=job.get("provider"),
                file_exists=True,
                file_size_bytes=ev["file_size_bytes"],
                primary_provider=primary_provider,
                fallback_providers=fallback_providers,
                production_ready=ready,
            )
            evidence_origin_summary[origin] += 1
            if ready:
                job["status"] = "succeeded"
                if args.provider and not job.get("provider"):
                    job["provider"] = args.provider
                generated += 1
            else:
                if job.get("status") == "succeeded":
                    job["status"] = "failed"
                failed += 1
                job["notes"] = f"{job.get('notes') or ''}".strip()
                if "non-production clip evidence" not in job["notes"]:
                    job["notes"] = (job["notes"] + " | " if job["notes"] else "") + "non-production clip evidence; regenerate with a real Stage 06 provider run"
        else:
            ev["file_exists"] = False
            ev["file_size_bytes"] = 0
            origin = annotate_evidence_origin(
                ev,
                provider=job.get("provider"),
                file_exists=False,
                file_size_bytes=0,
                primary_provider=primary_provider,
                fallback_providers=fallback_providers,
                production_ready=False,
            )
            evidence_origin_summary[origin] += 1
            if job.get("status") == "succeeded":
                job["status"] = "failed"
            if job.get("status") != "blocked":
                failed += 1
    jobs = data.get("jobs") or []
    summary = data.setdefault("summary", {})
    summary["expected_clip_count"] = len(jobs)
    summary["generated_clip_count"] = generated
    summary["failed_clip_count"] = failed
    summary["blocked_clip_count"] = blocked
    summary["shot_count"] = len({j.get("shot_id") for j in jobs if isinstance(j, dict) and j.get("shot_id")})
    summary["total_duration_sec"] = sum(float(j.get("duration_sec") or 0) for j in jobs if isinstance(j, dict))
    summary["evidence_origin_summary"] = evidence_origin_summary
    self_check = data.setdefault("self_check", {})
    all_clips = generated == len(jobs) and generated > 0
    self_check["all_required_clips_exist"] = all_clips
    self_check["source_stage05_ready_for_video_clip_generation"] = stage05_ready
    self_check["formal_progression_ready"] = all_clips and stage05_ready
    self_check["ready_for_audio_stage"] = all_clips and stage05_ready
    self_check["has_source_start_and_end_keyframes_for_each_shot"] = source_ok == len(jobs) and bool(jobs)
    self_check.setdefault("covers_all_storyboard_shots", bool(jobs))
    self_check["notes"] = [
        note
        for note in (self_check.get("notes") or [])
        if isinstance(note, str) and not note.startswith("formal_progression_blocker:")
    ]
    if all_clips and not stage05_ready:
        self_check["notes"].append(
            "formal_progression_blocker:source Stage 05 still requires review or missing evidence; Stage 06 remains draft_only."
        )
    data["formal_promotion_status"] = "ready_for_formal_progression" if all_clips and stage05_ready else ("draft_only" if generated > 0 else "pending")
    data["status"] = "generated" if all_clips else ("in_progress" if generated > 0 else "draft")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if all_clips and stage05_ready:
        data["allowed_next_stage"] = next_stage_after("STAGE_06_VIDEO_CLIPS", routing, "STAGE_07_AUDIO")
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_06_VIDEO_CLIPS_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"video_clips_confirmed": True},
            status="active",
        )
    else:
        data["allowed_next_stage"] = None
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_06_VIDEO_CLIPS",
            allowed_next_stage=None,
            flags={"video_clips_confirmed": False},
            status="active",
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"VIDEO CLIP MANIFEST SYNCED: {path}")
    print(f"GENERATED_CLIPS: {generated}")
    print(f"FAILED_OR_MISSING_CLIPS: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
