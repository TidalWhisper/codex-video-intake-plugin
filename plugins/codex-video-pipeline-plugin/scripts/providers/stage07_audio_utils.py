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


def upsert_error(job: dict[str, Any], provider_name: str, message: str, *, status: str = "failed") -> None:
    job["status"] = status
    job["provider"] = provider_name
    job.setdefault("errors", [])
    for item in job["errors"]:
        if not isinstance(item, dict):
            continue
        if item.get("provider") == provider_name and item.get("message") == message:
            item["created_at"] = utc_now()
            break
    else:
        job["errors"].append({
            "type": "provider_error",
            "provider": provider_name,
            "message": message,
            "created_at": utc_now(),
        })
    job.setdefault("evidence", {})
    job["evidence"]["created_at"] = None


def remove_error_messages(job: dict[str, Any], provider_name: str, startswith: tuple[str, ...]) -> None:
    errors = job.get("errors")
    if not isinstance(errors, list):
        return
    filtered: list[dict[str, Any]] = []
    for item in errors:
        if not isinstance(item, dict):
            filtered.append(item)
            continue
        if item.get("provider") != provider_name:
            filtered.append(item)
            continue
        message = str(item.get("message") or "")
        if any(message.startswith(prefix) for prefix in startswith):
            continue
        filtered.append(item)
    job["errors"] = filtered


def update_manifest_state(data: dict[str, Any], manifest_path: Path) -> None:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    generated_voice = generated_music = generated_total = 0
    voice_jobs = music_jobs = 0
    has_active = False
    has_terminal_non_success = False
    for job in jobs:
        if not isinstance(job, dict):
            continue
        audio_type = job.get("audio_type")
        job_status = str(job.get("status") or "").strip().lower()
        if audio_type in {"voiceover", "dialogue"}:
            voice_jobs += 1
        if audio_type == "music":
            music_jobs += 1
        if job_status in {"queued", "running", "awaiting_sync"}:
            has_active = True
        elif job_status in {"failed", "cancelled"}:
            has_terminal_non_success = True
        output_path = job.get("output_path") or job.get("evidence", {}).get("file_path")
        resolved = resolve_path(manifest_path, output_path)
        exists = resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0
        job.setdefault("evidence", {})
        job["evidence"]["file_path"] = str(resolved).replace("\\", "/")
        job["evidence"]["file_exists"] = exists
        job["evidence"]["file_size_bytes"] = resolved.stat().st_size if exists else 0
        if exists and job_status == "succeeded":
            generated_total += 1
            if audio_type in {"voiceover", "dialogue"}:
                generated_voice += 1
            if audio_type == "music":
                generated_music += 1
    requirements = data.get("requirements") if isinstance(data.get("requirements"), dict) else {}
    all_audio = generated_total == len(jobs) and (len(jobs) > 0 or (not requirements.get("voice_required") and not requirements.get("music_required")))
    data.setdefault("summary", {})
    data["summary"].update({
        "expected_voice_count": voice_jobs,
        "generated_voice_count": generated_voice,
        "expected_music_count": music_jobs,
        "generated_music_count": generated_music,
        "required_audio_count": len(jobs),
        "generated_audio_count": generated_total,
    })
    data.setdefault("self_check", {})
    data["self_check"].update({
        "has_voice_tracks_for_required_lines": (not requirements.get("voice_required")) or voice_jobs > 0,
        "has_music_when_required": (not requirements.get("music_required")) or music_jobs > 0,
        "all_required_audio_files_exist": all_audio,
        "ready_for_assembly_stage": all_audio,
    })
    if all_audio:
        data["status"] = "generated"
    elif has_active or generated_total > 0 or has_terminal_non_success:
        data["status"] = "in_progress"
    else:
        data["status"] = "draft"
    data["allowed_next_stage"] = next_stage_after("STAGE_07_AUDIO", routing, "STAGE_08_ASSEMBLY") if all_audio else None
    data["updated_at"] = utc_now()


def missing_audio_jobs(data: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        output_path = job.get("output_path") or (job.get("evidence") or {}).get("file_path")
        resolved = resolve_path(manifest_path, output_path)
        exists = resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0
        if exists:
            continue
        missing.append({
            "audio_id": str(job.get("audio_id") or ""),
            "audio_type": str(job.get("audio_type") or ""),
            "shot_id": str(job.get("shot_id") or ""),
            "provider_priority": [str(item) for item in (job.get("provider_priority") or []) if str(item).strip()],
            "output_path": str(resolved).replace("\\", "/"),
            "status": str(job.get("status") or ""),
        })
    return missing


def write_audio_recovery_artifacts(
    manifest_path: Path,
    data: dict[str, Any],
    *,
    reason: str,
    provider_health: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    recovery_path = manifest_path.parent / "audio_recovery.md"
    runtime_status_path = manifest_path.parent / "audio_runtime_status.json"
    missing = missing_audio_jobs(data, manifest_path)
    manifest_arg = str(manifest_path).replace("\\", "/")
    health = provider_health if isinstance(provider_health, dict) else {}
    lines = [
        "# Stage 07 Audio Recovery",
        "",
        f"- Project: `{data.get('project_id')}`",
        f"- Manifest: `{manifest_arg}`",
        f"- Reason: {reason}",
        f"- Missing audio jobs: {len(missing)}",
        "",
        "## Next Actions",
        "",
        f"1. `python plugins/codex-video-pipeline-plugin/scripts/providers/check_provider_health.py --json`",
        f"2. `python plugins/codex-video-pipeline-plugin/scripts/providers/run_comfyui_indextts2.py {manifest_arg} --poll-interval 1 --max-wait-seconds 240`",
        f"3. `python plugins/codex-video-pipeline-plugin/scripts/providers/run_comfyui_music.py {manifest_arg} --poll-interval 1 --max-wait-seconds 240`",
        f"4. `python plugins/codex-video-pipeline-plugin/skills/video-audio/scripts/sync_audio_manifest.py {manifest_arg}`",
        "",
    ]
    if health:
        lines.extend([
            "## Provider Health",
            "",
            f"- ComfyUI: `{health.get('comfyui_status') or health.get('status') or 'unknown'}`",
            f"- Detail: `{health.get('comfyui_error') or health.get('error') or ''}`",
            "",
        ])
    if missing:
        lines.extend(["## Missing Jobs", ""])
        for item in missing:
            provider_text = " -> ".join(item["provider_priority"]) if item["provider_priority"] else "manual"
            lines.append(
                f"- `{item['audio_id']}` `{item['audio_type']}` target=`{item['output_path']}` providers=`{provider_text}` status=`{item['status'] or 'pending'}`"
            )
        lines.append("")
    recovery_path.write_text("\n".join(lines), encoding="utf-8")
    write_json(runtime_status_path, {
        "project_id": data.get("project_id"),
        "stage": "STAGE_07_AUDIO",
        "status": "ready_for_assembly" if not missing else "recovery_required",
        "reason": reason,
        "missing_jobs": missing,
        "provider_health": health,
        "updated_at": utc_now(),
        "recovery_doc_path": str(recovery_path).replace("\\", "/"),
    })
    return recovery_path, runtime_status_path
