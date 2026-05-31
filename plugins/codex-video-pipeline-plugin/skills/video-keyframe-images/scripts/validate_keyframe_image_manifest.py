#!/usr/bin/env python3
"""Validate Stage 05 keyframe image manifest.

Final mode requires every required image job to have status=succeeded and a real existing non-empty file.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_keyframe_prompts",
    "image_provider_strategy", "output_root", "keyframes_dir", "jobs", "summary", "self_check", "allowed_next_stage"
]
REQUIRED_JOB = [
    "image_id", "shot_id", "frame_role", "prompt", "negative_prompt", "aspect_ratio", "resolution",
    "provider_priority", "provider", "status", "output_path", "evidence", "errors", "notes"
]
SHOT_ID_RE = re.compile(r"^S\d{3}$")
IMAGE_ID_RE = re.compile(r"^IMG_S\d{3}_(START|MID|END)$")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def resolve_path(base_json: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = Path(raw)
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


def validate(data: dict[str, Any], path: Path | None = None, mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = path or Path("keyframe_image_manifest.json")

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_05_KEYFRAME_IMAGES":
        errors.append("stage must be STAGE_05_KEYFRAME_IMAGES")
    if data.get("status") not in {"draft", "in_progress", "generated", "confirmed"}:
        errors.append("status must be draft, in_progress, generated, or confirmed")
    for key in ["project_id", "source_brief", "source_keyframe_prompts", "output_root", "keyframes_dir"]:
        if is_blank(data.get(key)):
            errors.append(f"{key} must not be blank")
    if not isinstance(data.get("image_provider_strategy"), dict):
        errors.append("image_provider_strategy must be an object")
    route_key = data.get("stage05_route_key")
    if route_key is not None and is_blank(route_key):
        errors.append("stage05_route_key must not be blank when present")
    workflow_mapping_key = data.get("comfyui_workflow_mapping_key")
    if workflow_mapping_key is not None and is_blank(workflow_mapping_key):
        errors.append("comfyui_workflow_mapping_key must not be blank when present")
    model_id = data.get("comfyui_model_id")
    if model_id is not None and is_blank(model_id):
        errors.append("comfyui_model_id must not be blank when present")
    preferred_workflow_candidate = data.get("preferred_comfyui_workflow_candidate")
    if preferred_workflow_candidate is not None and is_blank(preferred_workflow_candidate):
        errors.append("preferred_comfyui_workflow_candidate must not be blank when present")
    for field_name in [
        "comfyui_style_preset_key",
        "comfyui_style_preset_label",
        "comfyui_style_positive_anchor",
        "comfyui_style_negative_anchor",
        "comfyui_control_mode",
        "comfyui_optimization_profile",
        "comfyui_optimization_profile_label",
    ]:
        if data.get(field_name) is not None and is_blank(data.get(field_name)):
            errors.append(f"{field_name} must not be blank when present")
    preferred_model_candidate = data.get("preferred_comfyui_model_candidate")
    if preferred_model_candidate is not None and is_blank(preferred_model_candidate):
        errors.append("preferred_comfyui_model_candidate must not be blank when present")
    route_migration_state = data.get("route_migration_state")
    if route_migration_state is not None and is_blank(route_migration_state):
        errors.append("route_migration_state must not be blank when present")
    preferred_workflow_source_ref = data.get("preferred_comfyui_workflow_source_ref")
    if preferred_workflow_source_ref is not None and is_blank(preferred_workflow_source_ref):
        errors.append("preferred_comfyui_workflow_source_ref must not be blank when present")
    preferred_workflow_format = data.get("preferred_comfyui_workflow_format")
    if preferred_workflow_format is not None and is_blank(preferred_workflow_format):
        errors.append("preferred_comfyui_workflow_format must not be blank when present")
    for field_name in [
        "preferred_comfyui_workflow_custom_node_dependencies",
        "preferred_comfyui_workflow_import_blockers",
    ]:
        value = data.get(field_name)
        if value is not None and (not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value)):
            errors.append(f"{field_name} must be a list of non-empty strings when present")
    route_resolution = data.get("route_resolution")
    if route_resolution is not None and not isinstance(route_resolution, dict):
        errors.append("route_resolution must be an object when present")
    shot_frame_requirements = data.get("shot_frame_requirements")
    if shot_frame_requirements is not None:
        if not isinstance(shot_frame_requirements, dict):
            errors.append("shot_frame_requirements must be an object when present")
        else:
            for shot_id, roles in shot_frame_requirements.items():
                if not isinstance(shot_id, str) or not SHOT_ID_RE.match(shot_id):
                    errors.append("shot_frame_requirements keys must look like S001")
                    continue
                if not isinstance(roles, list) or not roles:
                    errors.append(f"shot_frame_requirements.{shot_id} must be a non-empty list")
                    continue
                normalized_roles = [str(role).strip() for role in roles]
                if any(role not in {"start", "mid", "end"} for role in normalized_roles):
                    errors.append(f"shot_frame_requirements.{shot_id} may only contain start, mid, or end")
                if "start" not in normalized_roles or "end" not in normalized_roles:
                    errors.append(f"shot_frame_requirements.{shot_id} must include start and end")
    optimization = data.get("comfyui_optimization")
    if optimization is not None:
        if not isinstance(optimization, dict):
            errors.append("comfyui_optimization must be an object when present")
        else:
            if is_blank(optimization.get("workflow_mapping_key")):
                errors.append("comfyui_optimization.workflow_mapping_key must not be blank")
            if is_blank(optimization.get("profile_key")):
                errors.append("comfyui_optimization.profile_key must not be blank")
            if is_blank(optimization.get("profile_label")):
                errors.append("comfyui_optimization.profile_label must not be blank")
            if not isinstance(optimization.get("dimension_scale"), (int, float)):
                errors.append("comfyui_optimization.dimension_scale must be numeric")
            if not isinstance(optimization.get("round_to_multiple"), int) or optimization.get("round_to_multiple") <= 0:
                errors.append("comfyui_optimization.round_to_multiple must be a positive integer")
            for key in ["max_width", "max_height"]:
                value = optimization.get(key)
                if value is not None and (not isinstance(value, int) or value <= 0):
                    errors.append(f"comfyui_optimization.{key} must be a positive integer when present")
            workflow_replacements = optimization.get("workflow_replacements")
            if not isinstance(workflow_replacements, dict):
                errors.append("comfyui_optimization.workflow_replacements must be an object")
            notes = optimization.get("notes")
            if notes is not None and (not isinstance(notes, list) or not all(isinstance(item, str) and item.strip() for item in notes)):
                errors.append("comfyui_optimization.notes must be a list of non-empty strings when present")
    if not isinstance(data.get("jobs"), list):
        errors.append("jobs must be a list")
    if not isinstance(data.get("summary"), dict):
        errors.append("summary must be an object")
    if data.get("quality_review") is not None and not isinstance(data.get("quality_review"), dict):
        errors.append("quality_review must be an object when present")
    if not isinstance(data.get("self_check"), dict):
        errors.append("self_check must be an object")

    if mode == "draft":
        jobs = data.get("jobs")
        if isinstance(jobs, list) and not jobs:
            warnings.append("draft manifest has no jobs yet")
        if isinstance(jobs, list):
            pending = [j for j in jobs if isinstance(j, dict) and j.get("status") == "pending"]
            if pending:
                warnings.append(f"draft manifest has {len(pending)} pending image jobs")
        return not errors, errors, warnings

    jobs = data.get("jobs")
    seen: set[str] = set()
    by_shot: dict[str, set[str]] = {}
    generated = 0
    if isinstance(jobs, list):
        if not jobs:
            errors.append("jobs must not be empty in final mode")
        for idx, job in enumerate(jobs):
            if not isinstance(job, dict):
                errors.append(f"jobs[{idx}] must be an object")
                continue
            for key in REQUIRED_JOB:
                if key not in job:
                    errors.append(f"jobs[{idx}] missing field: {key}")
            image_id = job.get("image_id")
            if not isinstance(image_id, str) or not IMAGE_ID_RE.match(image_id):
                errors.append(f"jobs[{idx}].image_id must look like IMG_S001_START, IMG_S001_MID, or IMG_S001_END")
            elif image_id in seen:
                errors.append(f"duplicate image_id: {image_id}")
            else:
                seen.add(image_id)
            shot_id = job.get("shot_id")
            if not isinstance(shot_id, str) or not SHOT_ID_RE.match(shot_id):
                errors.append(f"jobs[{idx}].shot_id must look like S001")
            else:
                by_shot.setdefault(shot_id, set()).add(str(job.get("frame_role")))
            if job.get("frame_role") not in {"start", "mid", "end"}:
                errors.append(f"jobs[{idx}].frame_role must be start, mid, or end")
            if "stage05_route_key" in job and is_blank(job.get("stage05_route_key")):
                errors.append(f"jobs[{idx}].stage05_route_key must not be blank when present")
            if route_key is not None and job.get("stage05_route_key") != route_key:
                errors.append(f"jobs[{idx}].stage05_route_key must match top-level stage05_route_key")
            if "comfyui_workflow_mapping_key" in job and is_blank(job.get("comfyui_workflow_mapping_key")):
                errors.append(f"jobs[{idx}].comfyui_workflow_mapping_key must not be blank when present")
            if workflow_mapping_key is not None and job.get("comfyui_workflow_mapping_key") != workflow_mapping_key:
                errors.append(f"jobs[{idx}].comfyui_workflow_mapping_key must match top-level comfyui_workflow_mapping_key")
            if "comfyui_model_id" in job and is_blank(job.get("comfyui_model_id")):
                errors.append(f"jobs[{idx}].comfyui_model_id must not be blank when present")
            if model_id is not None and job.get("comfyui_model_id") != model_id:
                errors.append(f"jobs[{idx}].comfyui_model_id must match top-level comfyui_model_id")
            if "preferred_comfyui_workflow_candidate" in job and is_blank(job.get("preferred_comfyui_workflow_candidate")):
                errors.append(f"jobs[{idx}].preferred_comfyui_workflow_candidate must not be blank when present")
            if preferred_workflow_candidate is not None and job.get("preferred_comfyui_workflow_candidate") != preferred_workflow_candidate:
                errors.append(f"jobs[{idx}].preferred_comfyui_workflow_candidate must match top-level preferred_comfyui_workflow_candidate")
            for field_name in [
                "comfyui_style_preset_key",
                "comfyui_style_preset_label",
                "comfyui_style_positive_anchor",
                "comfyui_style_negative_anchor",
                "comfyui_control_mode",
                "comfyui_optimization_profile",
                "comfyui_optimization_profile_label",
            ]:
                if job.get(field_name) is not None and is_blank(job.get(field_name)):
                    errors.append(f"jobs[{idx}].{field_name} must not be blank when present")
                top_level_value = data.get(field_name)
                if top_level_value is not None and job.get(field_name) != top_level_value:
                    errors.append(f"jobs[{idx}].{field_name} must match top-level {field_name}")
            if "preferred_comfyui_model_candidate" in job and is_blank(job.get("preferred_comfyui_model_candidate")):
                errors.append(f"jobs[{idx}].preferred_comfyui_model_candidate must not be blank when present")
            if preferred_model_candidate is not None and job.get("preferred_comfyui_model_candidate") != preferred_model_candidate:
                errors.append(f"jobs[{idx}].preferred_comfyui_model_candidate must match top-level preferred_comfyui_model_candidate")
            if "route_migration_state" in job and is_blank(job.get("route_migration_state")):
                errors.append(f"jobs[{idx}].route_migration_state must not be blank when present")
            if route_migration_state is not None and job.get("route_migration_state") != route_migration_state:
                errors.append(f"jobs[{idx}].route_migration_state must match top-level route_migration_state")
            if "preferred_comfyui_workflow_source_ref" in job and is_blank(job.get("preferred_comfyui_workflow_source_ref")):
                errors.append(f"jobs[{idx}].preferred_comfyui_workflow_source_ref must not be blank when present")
            if preferred_workflow_source_ref is not None and job.get("preferred_comfyui_workflow_source_ref") != preferred_workflow_source_ref:
                errors.append(f"jobs[{idx}].preferred_comfyui_workflow_source_ref must match top-level preferred_comfyui_workflow_source_ref")
            if job.get("preferred_comfyui_workflow_format") is not None and is_blank(job.get("preferred_comfyui_workflow_format")):
                errors.append(f"jobs[{idx}].preferred_comfyui_workflow_format must not be blank when present")
            if preferred_workflow_format is not None and job.get("preferred_comfyui_workflow_format") != preferred_workflow_format:
                errors.append(f"jobs[{idx}].preferred_comfyui_workflow_format must match top-level preferred_comfyui_workflow_format")
            for field_name in [
                "preferred_comfyui_workflow_custom_node_dependencies",
                "preferred_comfyui_workflow_import_blockers",
            ]:
                value = job.get(field_name)
                if value is not None:
                    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                        errors.append(f"jobs[{idx}].{field_name} must be a list of non-empty strings when present")
                    elif isinstance(data.get(field_name), list) and value != data.get(field_name):
                        errors.append(f"jobs[{idx}].{field_name} must match top-level {field_name}")
            for key in ["prompt", "negative_prompt", "aspect_ratio", "resolution", "output_path"]:
                if is_blank(job.get(key)):
                    errors.append(f"jobs[{idx}].{key} must not be blank in final mode")
            if not isinstance(job.get("provider_priority"), list) or not job.get("provider_priority"):
                errors.append(f"jobs[{idx}].provider_priority must be a non-empty list")
            if is_blank(job.get("provider")):
                errors.append(f"jobs[{idx}].provider must not be blank in final mode")
            if job.get("status") != "succeeded":
                errors.append(f"jobs[{idx}].status must be succeeded in final mode")
            evidence = job.get("evidence")
            if not isinstance(evidence, dict):
                errors.append(f"jobs[{idx}].evidence must be an object")
                continue
            quality_gate = job.get("quality_gate")
            if quality_gate is not None:
                if not isinstance(quality_gate, dict):
                    errors.append(f"jobs[{idx}].quality_gate must be an object when present")
                elif quality_gate.get("requires_manual_review") is True:
                    status = str(quality_gate.get("manual_review_status") or "").strip().lower()
                    if status not in {"approved", "waived"}:
                        errors.append(
                            f"jobs[{idx}].quality_gate.manual_review_status must be approved or waived when manual review is required in final mode"
                        )
                    if status == "approved":
                        if quality_gate.get("content_text_alignment_confirmed") is not True:
                            errors.append(
                                f"jobs[{idx}].quality_gate.content_text_alignment_confirmed must be true when approving manual review in final mode"
                            )
                        if is_blank(quality_gate.get("content_text_alignment_note")):
                            errors.append(
                                f"jobs[{idx}].quality_gate.content_text_alignment_note must not be blank when approving manual review in final mode"
                            )
                        if is_blank(quality_gate.get("content_text_alignment_checked_at")):
                            errors.append(
                                f"jobs[{idx}].quality_gate.content_text_alignment_checked_at must not be blank when approving manual review in final mode"
                            )
            file_path = evidence.get("file_path") or job.get("output_path")
            resolved = resolve_path(manifest_path, file_path)
            if resolved is None:
                errors.append(f"jobs[{idx}].evidence.file_path must not be blank")
                continue
            if not resolved.exists():
                errors.append(f"jobs[{idx}] image file does not exist: {resolved}")
            elif not resolved.is_file():
                errors.append(f"jobs[{idx}] image path is not a file: {resolved}")
            else:
                size = resolved.stat().st_size
                if size <= 0:
                    errors.append(f"jobs[{idx}] image file is empty: {resolved}")
                else:
                    generated += 1
                if evidence.get("file_exists") is not True:
                    errors.append(f"jobs[{idx}].evidence.file_exists must be true")
                if not isinstance(evidence.get("file_size_bytes"), int) or evidence.get("file_size_bytes") <= 0:
                    errors.append(f"jobs[{idx}].evidence.file_size_bytes must be a positive integer")

    normalized_requirements: dict[str, set[str]] = {}
    if isinstance(shot_frame_requirements, dict):
        for shot_id, roles in shot_frame_requirements.items():
            if isinstance(roles, list):
                normalized_requirements[str(shot_id)] = {str(role).strip() for role in roles if str(role).strip()}

    for shot_id, roles in by_shot.items():
        required_roles = normalized_requirements.get(shot_id, {"start", "end"})
        if not {"start", "end"}.issubset(roles):
            errors.append(f"shot {shot_id} must have both start and end images")
            continue
        if not required_roles.issubset(roles):
            errors.append(
                f"shot {shot_id} is missing required frame roles: {', '.join(sorted(required_roles.difference(roles)))}"
            )

    summary = data.get("summary")
    if isinstance(summary, dict):
        if summary.get("expected_image_count") != len(jobs or []):
            errors.append("summary.expected_image_count must equal len(jobs)")
        if summary.get("generated_image_count") != generated:
            errors.append("summary.generated_image_count must equal count of existing non-empty image files")
    self_check = data.get("self_check")
    if isinstance(self_check, dict):
        for key in [
            "covers_all_keyframe_prompts",
            "has_start_and_end_for_each_shot",
            "all_required_images_exist",
            "manual_review_cleared",
            "ready_for_video_clip_generation",
        ]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")
    quality_review = data.get("quality_review")
    if mode == "final":
        if not isinstance(quality_review, dict):
            errors.append("quality_review must be an object in final mode")
        elif quality_review.get("manual_review_cleared") is not True:
            errors.append("quality_review.manual_review_cleared must be true in final mode")
    quality_signals = data.get("quality_signals")
    if mode == "final":
        if not isinstance(quality_signals, dict):
            errors.append("quality_signals must be an object in final mode")
        else:
            for key in ["intent_route_matches_strategy", "style_route_matches_strategy", "consistency_prompts_present", "quality_targets_defined"]:
                if quality_signals.get(key) is not True:
                    errors.append(f"quality_signals.{key} must be true in final mode")
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
        print("KEYFRAME IMAGE MANIFEST VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"KEYFRAME IMAGE MANIFEST VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"KEYFRAME IMAGE MANIFEST VALIDATION PASSED ({args.mode} mode): {args.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
