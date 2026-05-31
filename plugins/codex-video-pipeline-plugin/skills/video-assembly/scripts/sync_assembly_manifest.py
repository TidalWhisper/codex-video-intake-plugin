#!/usr/bin/env python3
"""Sync Stage 08 final rough-cut output evidence into assembly_manifest.json."""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.media_evidence import MIN_PRODUCTION_VIDEO_BYTES, assembly_output_ready, clip_output_ready  # noqa: E402
from pipeline_core.project_state import annotate_evidence_origin, update_project_manifest_for_stage  # noqa: E402
from pipeline_core.story_continuity import has_template_leak, pick_story_anchors, shot_anchor_bundle  # noqa: E402


def resolve_path(base_json: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    base_abs = base_json if base_json.is_absolute() else (Path.cwd() / base_json).resolve()

    def plugin_root_candidates() -> list[Path]:
        candidates: list[Path] = []
        seen: set[str] = set()

        def add(path: Path) -> None:
            resolved = path.resolve()
            if resolved.name != "codex-video-pipeline-plugin":
                return
            key = str(resolved).lower()
            if key not in seen:
                candidates.append(resolved)
                seen.add(key)

        for anchor in [base_abs.parent, *base_abs.parents]:
            add(anchor)
        cwd = Path.cwd().resolve()
        for anchor in [cwd, *cwd.parents]:
            add(anchor)
        add(ROOT)
        return candidates

    plugin_roots = plugin_root_candidates()
    special_roots: list[Path] = []
    repo_roots: list[Path] = []
    for plugin_root in plugin_roots:
        if plugin_root.parent.name == "plugins":
            repo_root = plugin_root.parent.parent.resolve()
            if repo_root not in repo_roots:
                repo_roots.append(repo_root)
    if p.parts:
        first = p.parts[0].lower()
        if first == "plugins":
            special_roots.extend(repo_roots)
        elif first in KNOWN_PLUGIN_ROOT_CHILDREN:
            special_roots.extend(plugin_roots)
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [*special_roots, *repo_roots, *plugin_roots, Path.cwd().resolve(), base_abs.parent, *base_abs.parents]:
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
    return (base_abs.parent / p).resolve()


def maybe_load_json(path: Path | None) -> dict:
    if path is None or not path.exists() or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def clip_manifest_ready(manifest_path: Path | None, clip_manifest: dict) -> bool:
    if manifest_path is None or not clip_manifest:
        return False
    if not bool((clip_manifest.get("self_check") or {}).get("ready_for_audio_stage")):
        return False
    jobs = clip_manifest.get("jobs") if isinstance(clip_manifest.get("jobs"), list) else []
    if not jobs:
        return False
    for job in jobs:
        if not isinstance(job, dict):
            return False
        raw = job.get("output_path") or (job.get("evidence") or {}).get("file_path")
        if not raw:
            return False
        clip_path = resolve_path(manifest_path, str(raw))
        if not clip_output_ready(clip_path, job.get("provider")):
            return False
    return True


def timeline_note_for_shot(shot: dict, bundle: dict[str, str]) -> str:
    composition = str(shot.get("composition") or "").strip()
    action = bundle.get("action") or str(shot.get("action") or "").strip() or "推进故事"
    emotion = bundle.get("emotion") or str(shot.get("emotion") or "").strip() or "当前情绪变化"
    location = bundle.get("location") or str(shot.get("scene") or shot.get("location") or "").strip() or "当前场景"
    weather = bundle.get("weather") or str(shot.get("weather") or "").strip()
    scene_label = f"{weather}{location}".strip() or location
    key_prop = bundle.get("key_prop") or str(shot.get("key_prop") or "").strip()
    if composition and not has_template_leak(composition):
        return composition
    prop_clause = f"，保留{key_prop}线索" if key_prop else ""
    return f"{scene_label}里，{action}，情绪落在{emotion}{prop_clause}。"


def fallback_visual_payload(base_json: Path, clip_job: dict) -> dict[str, object]:
    keyframes = clip_job.get("source_keyframes") if isinstance(clip_job.get("source_keyframes"), dict) else {}
    payload: dict[str, object] = {
        "fallback_strategy": "stage05_keyframe_reel",
        "source_clip_ready": False,
        "start_image_path": "",
        "mid_image_path": "",
        "end_image_path": "",
        "preferred_image_path": "",
    }
    for role in ["start", "mid", "end"]:
        raw = keyframes.get(role)
        if not isinstance(raw, str) or not raw.strip():
            continue
        resolved = resolve_path(base_json, raw)
        if resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0:
            payload[f"{role}_image_path"] = str(resolved).replace("\\", "/")
    for candidate_key in ["mid_image_path", "end_image_path", "start_image_path"]:
        candidate = str(payload.get(candidate_key) or "").strip()
        if candidate:
            payload["preferred_image_path"] = candidate
            break
    clip_path = resolve_path(base_json, clip_job.get("output_path") or (clip_job.get("evidence") or {}).get("file_path") or "")
    if clip_output_ready(clip_path, clip_job.get("provider")):
        payload["source_clip_ready"] = True
    return payload


def normalize_manifest_contracts(base_json: Path, data: dict) -> None:
    brief = maybe_load_json(resolve_path(base_json, data.get("source_brief") or ""))
    storyboard = maybe_load_json(resolve_path(base_json, data.get("source_storyboard") or ""))
    clip_manifest = maybe_load_json(resolve_path(base_json, data.get("source_video_clip_manifest") or ""))
    audio_manifest = maybe_load_json(resolve_path(base_json, data.get("source_audio_manifest") or ""))

    shot_lookup = {
        shot.get("shot_id"): shot
        for shot in (storyboard.get("shots") or [])
        if isinstance(shot, dict) and shot.get("shot_id")
    }
    clip_lookup = {
        job.get("clip_id"): job
        for job in (clip_manifest.get("jobs") or [])
        if isinstance(job, dict) and job.get("clip_id")
    }
    audio_lookup = {
        job.get("audio_id"): job
        for job in (audio_manifest.get("jobs") or [])
        if isinstance(job, dict) and job.get("audio_id")
    }

    if brief and storyboard:
        anchors = pick_story_anchors(brief, max(1, len(shot_lookup) or len(data.get("timeline") or [])), storyboard, clip_manifest)
        data["story_anchors"] = anchors
        for idx, item in enumerate(data.get("timeline") or []):
            if not isinstance(item, dict):
                continue
            clip_job = clip_lookup.get(item.get("source_clip_id")) or {}
            candidate_clip = clip_job.get("output_path") or (clip_job.get("evidence") or {}).get("file_path")
            if candidate_clip:
                item["clip_path"] = str(resolve_path(base_json, candidate_clip)).replace("\\", "/")
            item["fallback_visual"] = fallback_visual_payload(base_json, clip_job)
            if has_template_leak(item.get("notes")):
                shot = shot_lookup.get(item.get("shot_id")) or {}
                bundle = shot_anchor_bundle(anchors, idx, shot=shot)
                item["notes"] = timeline_note_for_shot(shot, bundle)

    for item in data.get("audio_tracks") or []:
        if not isinstance(item, dict):
            continue
        audio_job = audio_lookup.get(item.get("source_audio_id")) or {}
        candidate_audio = audio_job.get("output_path") or (audio_job.get("evidence") or {}).get("file_path")
        if candidate_audio:
            item["audio_path"] = str(resolve_path(base_json, candidate_audio)).replace("\\", "/")


def upstream_blocking_state(base_json: Path, data: dict) -> tuple[str, dict[str, bool], list[str]]:
    clip_manifest_path = resolve_path(base_json, data.get("source_video_clip_manifest") or "")
    audio_manifest_path = resolve_path(base_json, data.get("source_audio_manifest") or "")
    clip_manifest = maybe_load_json(clip_manifest_path)
    audio_manifest = maybe_load_json(audio_manifest_path)
    blockers: list[str] = []
    clip_ready = clip_manifest_ready(clip_manifest_path, clip_manifest) if clip_manifest else True
    audio_ready = bool((audio_manifest.get("self_check") or {}).get("ready_for_assembly_stage")) if audio_manifest else True
    if not clip_ready:
        blockers.append("source_video_clip_manifest not ready_for_audio_stage or contains non-production clip evidence")
        return "STAGE_06_VIDEO_CLIPS", {"video_clips_confirmed": False, "audio_confirmed": False, "assembly_confirmed": False}, blockers
    if not audio_ready:
        blockers.append("source_audio_manifest not ready_for_assembly_stage")
        return "STAGE_07_AUDIO", {"audio_confirmed": False, "assembly_confirmed": False}, blockers
    return "STAGE_08_ASSEMBLY", {"assembly_confirmed": False}, blockers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    normalize_manifest_contracts(path, data)
    out = resolve_path(path, data.get("final_output_path") or data.get("evidence", {}).get("file_path") or "")
    mix_plan = resolve_path(path, data.get("audio_mix_plan_path") or "audio_mix_plan.json")
    edit_list = resolve_path(path, data.get("edit_decision_list_path") or "edit_decision_list.json")
    exists = out.exists() and out.is_file()
    size = out.stat().st_size if exists else 0
    data.setdefault("evidence", {})
    data["evidence"].update({
        "file_path": str(out).replace("\\", "/"),
        "file_exists": bool(exists),
        "file_size_bytes": size,
        "created_at": datetime.now(timezone.utc).isoformat() if exists else None
    })
    production_ready = assembly_output_ready(data, out, min_bytes=MIN_PRODUCTION_VIDEO_BYTES)
    origin = annotate_evidence_origin(
        data["evidence"],
        provider=data.get("assembly_provider") or "ffmpeg",
        file_exists=bool(exists),
        file_size_bytes=size,
        primary_provider="ffmpeg",
        fallback_providers=["manual"],
        production_ready=production_ready,
    )
    fallback_stage, fallback_flags, blockers = upstream_blocking_state(path, data)
    data.setdefault("self_check", {})
    data["self_check"].update({
        "has_timeline_from_confirmed_clips": bool(data.get("timeline")),
        "has_audio_mix_plan": mix_plan.exists(),
        "has_edit_decision_list": edit_list.exists(),
        "has_final_output_file": production_ready,
        "ready_for_qa_stage": production_ready,
        "source_video_clips_ready": fallback_stage != "STAGE_06_VIDEO_CLIPS",
        "source_audio_ready": fallback_stage not in {"STAGE_06_VIDEO_CLIPS", "STAGE_07_AUDIO"},
    })
    data["self_check"]["notes"] = [
        note for note in (data["self_check"].get("notes") or [])
        if isinstance(note, str) and not note.startswith("upstream_blocker:")
    ]
    data["self_check"]["notes"].extend([f"upstream_blocker:{item}" for item in blockers])
    data.setdefault("summary", {})
    timeline = data.get("timeline") if isinstance(data.get("timeline"), list) else []
    fallback_segments = sum(
        1
        for item in timeline
        if isinstance(item, dict)
        and isinstance(item.get("fallback_visual"), dict)
        and not bool(item["fallback_visual"].get("source_clip_ready"))
        and str(item["fallback_visual"].get("preferred_image_path") or "").strip()
    )
    data["summary"]["fallback_visual_segment_count"] = fallback_segments
    data["summary"]["evidence_origin_summary"] = {
        "provider_output": 1 if origin == "provider_output" else 0,
        "fallback_output": 1 if origin == "fallback_output" else 0,
        "manual_import": 1 if origin == "manual_import" else 0,
        "placeholder_or_incomplete": 1 if origin == "placeholder_or_incomplete" else 0,
    }
    if production_ready:
        data["status"] = "generated"
        data["allowed_next_stage"] = next_stage_after("STAGE_08_ASSEMBLY", routing, "STAGE_09_QA")
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_08_ASSEMBLY_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"assembly_confirmed": True},
            status="active",
        )
    else:
        data["status"] = "in_progress"
        data["allowed_next_stage"] = None
        update_project_manifest_for_stage(
            path,
            current_stage=fallback_stage,
            allowed_next_stage=None,
            flags=fallback_flags,
            status="active",
        )
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ASSEMBLY MANIFEST SYNCED: {path}")
    print(f"OUTPUT EXISTS: {exists}, SIZE: {size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
