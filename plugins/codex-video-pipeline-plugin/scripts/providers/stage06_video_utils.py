#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.media_evidence import clip_output_ready  # noqa: E402

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


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_path(base_json: Path, raw: Any) -> Path:
    p = Path(str(raw))
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _nonempty_lines(values: list[Any]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        lines.append(text)
    return lines


def _job_prompt_constraints(job: dict[str, Any]) -> list[str]:
    raw = job.get("prompt_constraints")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item or "").strip()]


def _job_route_hint(job: dict[str, Any]) -> str:
    return str(job.get("route_hint") or "").strip()


def _expected_subject_count(job: dict[str, Any]) -> int:
    try:
        return max(1, int(job.get("expected_subject_count") or 1))
    except Exception:
        return 1


def _camera_lock_required(job: dict[str, Any]) -> bool:
    return bool(job.get("camera_lock_required"))


def build_motion_prompt(job: dict[str, Any]) -> str:
    sections: list[str] = []
    base_motion = _clean_text(job.get("motion_prompt"))
    if base_motion:
        sections.append(base_motion)
    for label, key in [
        ("Performance", "performance_prompt"),
        ("Style", "style_prompt"),
        ("Consistency", "consistency_prompt"),
        ("Camera", "camera_prompt"),
    ]:
        value = _clean_text(job.get(key))
        if value:
            sections.append(f"{label}: {value}")
    continuity_anchor = _clean_text(job.get("story_continuity_anchor"))
    if continuity_anchor:
        sections.append(f"Anchor: {continuity_anchor}")
    if _job_route_hint(job):
        sections.append(f"Route: {_job_route_hint(job)}")
    constraints = _job_prompt_constraints(job)
    if constraints:
        sections.append(f"Hard constraints: {' '.join(constraints)}")
    negative = _clean_text(job.get("negative_prompt"))
    if negative:
        sections.append(f"Avoid: {negative}")
    return "\n".join(sections).strip()


def build_prompt_relay_global_prompt(job: dict[str, Any]) -> str:
    bundle = job.get("story_anchor_bundle") if isinstance(job.get("story_anchor_bundle"), dict) else {}
    location = _clean_text(bundle.get("location"))
    weather = _clean_text(bundle.get("weather"))
    key_prop = _clean_text(bundle.get("key_prop"))
    scene_anchor = f"{weather}{location}".strip()
    anchor_line = ""
    if scene_anchor or key_prop:
        anchor_parts = []
        if scene_anchor:
            anchor_parts.append(f"scene anchor: {scene_anchor}")
        if key_prop:
            anchor_parts.append(f"key prop: {key_prop}")
        anchor_line = ", ".join(anchor_parts)
    return "\n".join(_nonempty_lines([
        job.get("consistency_prompt"),
        job.get("story_continuity_anchor"),
        job.get("style_prompt"),
        anchor_line,
        f"route hint: {_job_route_hint(job)}" if _job_route_hint(job) else "",
        "camera must stay locked on the established axis" if _camera_lock_required(job) else "",
        " ".join(_job_prompt_constraints(job)),
    ])).strip()


def build_prompt_relay_local_prompts(job: dict[str, Any]) -> str:
    bundle = job.get("story_anchor_bundle") if isinstance(job.get("story_anchor_bundle"), dict) else {}
    action = _clean_text(bundle.get("action")) or _clean_text(job.get("motion_prompt")) or "Advance the shot with clear action."
    emotion = _clean_text(bundle.get("emotion"))
    location = _clean_text(bundle.get("location"))
    weather = _clean_text(bundle.get("weather"))
    key_prop = _clean_text(bundle.get("key_prop"))
    scene_anchor = f"{weather}{location}".strip()
    negative = _clean_text(job.get("negative_prompt"))
    avoid_line = f"Avoid: {negative}" if negative else ""
    constraints_line = " ".join(_job_prompt_constraints(job))
    route_hint = _job_route_hint(job)
    expected_subjects = _expected_subject_count(job)
    if route_hint == "interaction_handoff":
        start_lines = _nonempty_lines([
            action,
            job.get("performance_prompt"),
            "Lock the camera to a stable frontal wide shot with no orbit, push-in, zoom, or handheld jitter.",
            f"Begin from the exact start keyframe pose in {scene_anchor} with exactly two readable subjects and exactly one shared {key_prop}." if scene_anchor and key_prop else "",
            "The giver still controls the prop at the start; the receiver is already present and readable in frame.",
            "Show one clean handoff only, with readable grip transition, clear body shift, and no extra bystander occlusion.",
            constraints_line,
            avoid_line,
        ])
        end_lines = _nonempty_lines([
            action,
            "Land on the exact end keyframe composition with both subjects still readable and stable.",
            f"Keep exactly two subjects and exactly one shared {key_prop}; no duplicate props, no extra limbs, no wrong holder." if key_prop else "Keep exactly two subjects with clean hand contact and no duplicate limbs.",
            "The giver-receiver relationship must remain unambiguous all the way to the final frame.",
            f"End on the emotion beat: {emotion}." if emotion else "",
            constraints_line,
            avoid_line,
        ])
        return " | ".join([
            "; ".join(start_lines).strip(),
            "; ".join(end_lines).strip(),
        ]).strip(" |")
    start_lines = _nonempty_lines([
        action,
        job.get("performance_prompt"),
        job.get("camera_prompt"),
        f"Begin from the exact start keyframe pose in {scene_anchor}." if scene_anchor else "Begin from the exact start keyframe pose.",
        f"Show immediate visible body displacement and readable contact with {key_prop}." if key_prop else "Show immediate visible body displacement and readable hand contact.",
        "Do not drift into static micro-motion.",
        f"Keep exactly {expected_subjects} clear subject in frame." if expected_subjects == 1 else f"Keep exactly {expected_subjects} readable subjects in frame.",
        constraints_line,
        avoid_line,
    ])
    end_lines = _nonempty_lines([
        action,
        f"Complete the movement and land on the exact end keyframe pose with clear spatial change.",
        f"Keep exactly {expected_subjects} subject and one {key_prop}, with correct grip and prop count." if key_prop and expected_subjects == 1 else "",
        f"Keep exactly {expected_subjects} readable subjects, correct limb count, and stable hand-object relationships." if not key_prop or expected_subjects != 1 else "",
        f"End on the emotion beat: {emotion}." if emotion else "",
        constraints_line,
        avoid_line,
    ])
    return " | ".join([
        "; ".join(start_lines).strip(),
        "; ".join(end_lines).strip(),
    ]).strip(" |")


def prompt_relay_segment_lengths(frame_count: int, route_hint: str | None = None) -> str:
    total = max(2, int(frame_count))
    if str(route_hint or "").strip() == "interaction_handoff":
        first = max(1, int(round(total * 0.7)))
    else:
        first = max(1, int(round(total * 0.55)))
    second = max(1, total - first)
    return f"{first},{second}"


def end_guide_frame_for_clip(frame_count: int, fps: int) -> int:
    _ = frame_count, fps
    # Community FFLF workflows pin the closing guide to the true last frame.
    return -1


def append_error(job: dict[str, Any], provider_name: str, message: str) -> None:
    job["status"] = "failed"
    job["provider"] = provider_name
    job.setdefault("errors", [])
    job["errors"].append({
        "type": "provider_error",
        "provider": provider_name,
        "message": message,
        "created_at": utc_now(),
    })
    job.setdefault("evidence", {})
    job["evidence"]["created_at"] = None


def update_manifest_state(data: dict[str, Any], manifest_path: Path) -> None:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    generated = 0
    failed = 0
    blocked = 0
    active = 0
    source_ok = 0
    shots: set[str] = set()
    total_duration = 0.0
    for job in jobs:
        if not isinstance(job, dict):
            continue
        shot_id = job.get("shot_id")
        if isinstance(shot_id, str):
            shots.add(shot_id)
        try:
            total_duration += float(job.get("duration_sec") or 0)
        except Exception:
            pass
        keyframes = job.get("source_keyframes") if isinstance(job.get("source_keyframes"), dict) else {}
        start = resolve_path(manifest_path, keyframes.get("start")) if keyframes.get("start") else None
        end = resolve_path(manifest_path, keyframes.get("end")) if keyframes.get("end") else None
        if start and end and start.exists() and end.exists() and start.stat().st_size > 0 and end.stat().st_size > 0:
            source_ok += 1
        output_path = job.get("output_path") or job.get("evidence", {}).get("file_path")
        resolved = resolve_path(manifest_path, output_path)
        raw_exists = resolved.exists() and resolved.is_file()
        exists = clip_output_ready(resolved, job.get("provider"))
        job.setdefault("evidence", {})
        job["evidence"]["file_path"] = str(resolved).replace("\\", "/")
        job["evidence"]["file_exists"] = raw_exists
        job["evidence"]["file_size_bytes"] = resolved.stat().st_size if raw_exists else 0
        if exists:
            generated += 1
        elif str(job.get("status") or "").strip().lower() == "blocked":
            blocked += 1
        elif job.get("status") == "succeeded":
            job["status"] = "failed"
        elif job.get("status") == "failed":
            failed += 1
        elif str(job.get("status") or "").strip().lower() in {"queued", "running", "submitting", "in_progress"}:
            active += 1
    expected = len(jobs)
    all_exist = expected > 0 and generated == expected
    data.setdefault("summary", {})
    unresolved_nonblocked = max(0, expected - generated - blocked)
    data["summary"].update({
        "shot_count": len(shots),
        "expected_clip_count": expected,
        "generated_clip_count": generated,
        "blocked_clip_count": blocked,
        "failed_clip_count": failed if active > 0 else (failed if failed else unresolved_nonblocked),
        "pending_clip_count": active,
        "total_duration_sec": total_duration,
    })
    data.setdefault("self_check", {})
    data["self_check"].update({
        "covers_all_storyboard_shots": expected > 0,
        "has_source_start_and_end_keyframes_for_each_shot": source_ok == expected and expected > 0,
        "all_required_clips_exist": all_exist,
        "ready_for_audio_stage": all_exist,
    })
    if all_exist:
        data["status"] = "generated"
    elif blocked and generated == 0 and active == 0:
        data["status"] = "blocked"
    elif active > 0 or generated > 0:
        data["status"] = "in_progress"
    data["allowed_next_stage"] = next_stage_after("STAGE_06_VIDEO_CLIPS", routing, "STAGE_07_AUDIO") if all_exist else None
    data["updated_at"] = utc_now()
