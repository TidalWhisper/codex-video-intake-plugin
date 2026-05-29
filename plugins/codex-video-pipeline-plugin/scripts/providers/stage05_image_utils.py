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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_provider_prompt(job: dict[str, Any]) -> str:
    sections: list[str] = []
    base_prompt = str(job.get("prompt") or "").strip()
    if base_prompt:
        sections.append(base_prompt)
    for label, key in [
        ("Style", "style_prompt"),
        ("Consistency", "consistency_prompt"),
        ("Camera", "camera_prompt"),
    ]:
        value = str(job.get(key) or "").strip()
        if value:
            sections.append(f"{label}: {value}")
    negative = str(job.get("negative_prompt") or "").strip()
    if negative:
        sections.append(f"Avoid: {negative}")
    return "\n".join(sections).strip()


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
    shots: dict[str, set[str]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        shot_id = job.get("shot_id")
        frame_role = job.get("frame_role")
        if isinstance(shot_id, str) and isinstance(frame_role, str):
            shots.setdefault(shot_id, set()).add(frame_role)
        output_path = job.get("output_path") or job.get("evidence", {}).get("file_path")
        resolved = resolve_path(manifest_path, output_path)
        exists = resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0
        job.setdefault("evidence", {})
        job["evidence"]["file_path"] = str(resolved).replace("\\", "/")
        job["evidence"]["file_exists"] = exists
        job["evidence"]["file_size_bytes"] = resolved.stat().st_size if exists else 0
        if exists:
            generated += 1
        elif job.get("status") == "failed":
            failed += 1
    expected = len(jobs)
    all_exist = expected > 0 and generated == expected
    data.setdefault("summary", {})
    data["summary"].update({
        "shot_count": len(shots),
        "expected_image_count": expected,
        "generated_image_count": generated,
        "failed_image_count": failed if failed else max(0, expected - generated),
    })
    data.setdefault("self_check", {})
    data["self_check"].update({
        "covers_all_keyframe_prompts": expected > 0,
        "has_start_and_end_for_each_shot": all(roles == {"start", "end"} for roles in shots.values()) if shots else False,
        "all_required_images_exist": all_exist,
        "ready_for_video_clip_generation": all_exist,
    })
    if all_exist:
        data["status"] = "generated"
    elif generated > 0:
        data["status"] = "in_progress"
    data["allowed_next_stage"] = next_stage_after("STAGE_05_KEYFRAME_IMAGES", routing, "STAGE_06_VIDEO_CLIPS") if all_exist else None
    data["updated_at"] = utc_now()
