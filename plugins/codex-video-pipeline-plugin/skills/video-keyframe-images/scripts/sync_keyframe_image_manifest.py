#!/usr/bin/env python3
"""Sync Stage 05 manifest evidence from files on disk."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "providers"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402
from pipeline_core.stage05_quality_gates import build_quality_gate  # noqa: E402
from stage05_image_utils import update_manifest_state  # noqa: E402


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


def _clean_non_empty_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_job_field_from_top_level(data: dict, field_name: str) -> None:
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return

    top_level_value = _clean_non_empty_str(data.get(field_name))
    job_values: list[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_value = _clean_non_empty_str(job.get(field_name))
        if top_level_value and not job_value:
            job[field_name] = top_level_value
            job_value = top_level_value
        if job_value:
            job_values.append(job_value)

    if top_level_value:
        data[field_name] = top_level_value
        return

    unique_values = {value for value in job_values if value}
    if len(unique_values) == 1:
        data[field_name] = next(iter(unique_values))


def _normalize_style_metadata_fields(data: dict) -> None:
    jobs = data.get("jobs")
    if not isinstance(jobs, list):
        return

    style_fields = [
        "comfyui_style_preset_key",
        "comfyui_style_preset_label",
        "comfyui_style_positive_anchor",
        "comfyui_style_negative_anchor",
    ]
    for field_name in style_fields:
        top_level_value = _clean_non_empty_str(data.get(field_name))
        collected_jobs: list[dict] = [job for job in jobs if isinstance(job, dict)]
        job_values = [_clean_non_empty_str(job.get(field_name)) for job in collected_jobs]
        normalized_values = [value for value in job_values if value]
        unique_values = {value for value in normalized_values}
        has_blank_values = any(value is None for value in job_values)
        if top_level_value and not normalized_values:
            for job, job_value in zip(collected_jobs, job_values):
                if job_value is None:
                    job[field_name] = top_level_value
            job_values = [_clean_non_empty_str(job.get(field_name)) for job in collected_jobs]
            normalized_values = [value for value in job_values if value]
            unique_values = {value for value in normalized_values}
            has_blank_values = any(value is None for value in job_values)
        if len(unique_values) == 1 and not has_blank_values:
            data[field_name] = next(iter(unique_values))
        else:
            data[field_name] = None


def normalize_stage05_route_fields(data: dict) -> None:
    route_fields = [
        "stage05_route_key",
        "comfyui_workflow_mapping_key",
        "comfyui_model_id",
        "preferred_comfyui_workflow_candidate",
        "preferred_comfyui_model_candidate",
        "route_migration_state",
        "preferred_comfyui_workflow_source_ref",
        "preferred_comfyui_workflow_format",
    ]
    route_resolution_field_map = {
        "stage05_route_key": "route_key",
        "comfyui_workflow_mapping_key": "comfyui_workflow_mapping_key",
        "comfyui_model_id": "comfyui_model_id",
        "preferred_comfyui_workflow_candidate": "preferred_comfyui_workflow_candidate",
        "preferred_comfyui_model_candidate": "preferred_comfyui_model_candidate",
        "route_migration_state": "route_migration_state",
        "preferred_comfyui_workflow_source_ref": "preferred_comfyui_workflow_source_ref",
        "preferred_comfyui_workflow_format": "preferred_comfyui_workflow_format",
    }
    route_resolution = data.get("route_resolution")
    for field_name in route_fields:
        route_key = route_resolution_field_map[field_name]
        if not _clean_non_empty_str(data.get(field_name)) and isinstance(route_resolution, dict):
            route_value = _clean_non_empty_str(route_resolution.get(route_key))
            if route_value:
                data[field_name] = route_value
        _normalize_job_field_from_top_level(data, field_name)
    for field_name in [
        "preferred_comfyui_workflow_custom_node_dependencies",
        "preferred_comfyui_workflow_import_blockers",
    ]:
        top_level_value = data.get(field_name)
        if not isinstance(top_level_value, list) and isinstance(route_resolution, dict):
            route_value = route_resolution.get(field_name)
            if isinstance(route_value, list):
                data[field_name] = route_value
                top_level_value = route_value
        jobs = data.get("jobs")
        if isinstance(jobs, list) and isinstance(top_level_value, list):
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                if not isinstance(job.get(field_name), list):
                    job[field_name] = list(top_level_value)
    _normalize_style_metadata_fields(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--provider", default=None, help="Optional provider to set for existing images, e.g. openai_image or comfyui_txt2img")
    parser.add_argument("--approve-risky-jobs", action="store_true", help="Approve all risky jobs that already have image files.")
    parser.add_argument("--approve-image-id", action="append", default=[], help="Approve one specific risky image_id. May be passed multiple times.")
    args = parser.parse_args(argv)
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    normalize_stage05_route_fields(data)
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    generated = 0
    failed = 0
    approve_image_ids = {str(item).strip() for item in args.approve_image_id if str(item).strip()}
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        raw = job.get("output_path") or job.get("evidence", {}).get("file_path")
        if not raw:
            continue
        img = resolve(path, str(raw))
        ev = job.setdefault("evidence", {})
        ev["file_path"] = str(img).replace("\\", "/")
        if img.exists() and img.is_file() and img.stat().st_size > 0:
            ev["file_exists"] = True
            ev["file_size_bytes"] = img.stat().st_size
            ev["created_at"] = datetime.fromtimestamp(img.stat().st_mtime, timezone.utc).isoformat()
            job["status"] = "succeeded"
            if args.provider and not job.get("provider"):
                job["provider"] = args.provider
            gate = build_quality_gate(job)
            if gate["requires_manual_review"] and (args.approve_risky_jobs or str(job.get("image_id") or "").strip() in approve_image_ids):
                gate["manual_review_status"] = "approved"
                gate["approved_at"] = datetime.now(timezone.utc).isoformat()
            job["quality_gate"] = gate
            generated += 1
        else:
            ev["file_exists"] = False
            ev["file_size_bytes"] = 0
            if job.get("status") == "succeeded":
                job["status"] = "failed"
            job["quality_gate"] = build_quality_gate(job)
            failed += 1
    update_manifest_state(data, path)
    data.setdefault("summary", {})
    data["summary"]["expected_image_count"] = len(data.get("jobs") or [])
    data["summary"]["generated_image_count"] = generated
    data["summary"]["failed_image_count"] = failed
    if data.get("self_check", {}).get("ready_for_video_clip_generation") is True:
        data["allowed_next_stage"] = next_stage_after("STAGE_05_KEYFRAME_IMAGES", routing, "STAGE_06_VIDEO_CLIPS")
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"keyframe_images_confirmed": True},
            status="active",
        )
    else:
        data["allowed_next_stage"] = None
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"KEYFRAME IMAGE MANIFEST SYNCED: {path}")
    print(f"GENERATED_IMAGES: {generated}")
    print(f"FAILED_OR_MISSING_IMAGES: {failed}")
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    if quality_review.get("pending_count"):
        print(f"PENDING_MANUAL_REVIEW: {quality_review['pending_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
