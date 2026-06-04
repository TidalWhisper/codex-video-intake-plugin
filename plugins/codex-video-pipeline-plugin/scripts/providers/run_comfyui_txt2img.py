#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(THIS_DIR.parent))

from comfyui_client import ComfyUIClient, ComfyUIError
import comfyui_ui_workflow
from comfyui_file_staging import stage_input_file
from openai_image_client import image_size_for_aspect_ratio
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from pipeline_core.stage05_optimization_profiles import (
    Stage05OptimizationError,
    load_stage05_optimization_profiles,
    resolve_stage05_workflow_optimization,
)
from pipeline_core.stage05_quality_gates import build_auto_repair_plan, build_creator_review_card
from provider_config import ConfigError, get_comfyui_settings, load_provider_config, validate_provider_config
from stage05_image_utils import (
    append_blocked,
    append_error,
    build_missing_reference_manual_recovery,
    build_provider_prompt,
    effective_negative_prompt,
    load_json,
    missing_character_reference_block,
    resolve_path,
    update_manifest_state,
    utc_now,
    write_json,
)
from workflow_mapping import apply_node_inputs, load_mapped_workflow, load_workflow_mapping


AUTO_ROUTED_WORKFLOW_NAMES = {"", "auto", "txt2img_keyframe"}
QWEN_NEXTSCENE_WORKFLOW_MAPPING_KEYS = {"stage05_realistic_cinematic_qwen_edit_nextscene_local"}
QWEN_REFERENCE_TARGET_SIZES = (512, 768, 1024, 1344, 1536, 2048)


def request_record(
    job: dict[str, Any],
    workflow_mapping_key: str,
    workflow_path: Path,
    *,
    optimization_profile: str | None,
    optimization_profile_label: str | None,
    width: int,
    height: int,
) -> dict[str, Any]:
    selected_workflow_name = resolve_workflow_display_name_for_job(job, workflow_mapping_key)
    return {
        "request_id": f"REQ_COMFYUI_TXT2IMG_{job['image_id']}",
        "image_id": job["image_id"],
        "shot_id": job["shot_id"],
        "frame_role": job["frame_role"],
        "provider": "comfyui_txt2img",
        "stage05_route_key": job.get("stage05_route_key"),
        "style_family": job.get("style_family"),
        "workflow_mapping_key": workflow_mapping_key,
        "workflow_name": selected_workflow_name,
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "comfyui_model_id": job.get("comfyui_model_id"),
        "preferred_comfyui_workflow_candidate": job.get("preferred_comfyui_workflow_candidate"),
        "preferred_comfyui_model_candidate": job.get("preferred_comfyui_model_candidate"),
        "route_migration_state": job.get("route_migration_state"),
        "preferred_comfyui_workflow_source_ref": job.get("preferred_comfyui_workflow_source_ref"),
        "preferred_comfyui_workflow_format": job.get("preferred_comfyui_workflow_format"),
        "preferred_comfyui_workflow_custom_node_dependencies": job.get("preferred_comfyui_workflow_custom_node_dependencies"),
        "preferred_comfyui_workflow_import_blockers": job.get("preferred_comfyui_workflow_import_blockers"),
        "comfyui_style_preset_key": job.get("comfyui_style_preset_key"),
        "comfyui_style_preset_label": job.get("comfyui_style_preset_label"),
        "comfyui_control_mode": job.get("comfyui_control_mode"),
        "comfyui_optimization_profile": optimization_profile,
        "comfyui_optimization_profile_label": optimization_profile_label,
        "prompt": job["prompt"],
        "resolved_prompt": build_provider_prompt(job),
        "negative_prompt": effective_negative_prompt(job),
        "quality_gate": job.get("quality_gate"),
        "seed": stable_seed(job),
        "width": width,
        "height": height,
        "output_path": job["output_path"],
        "status": "planned",
        "prompt_id": None,
        "selected_output": None,
        "error_message": None,
        "requested_at": None,
        "completed_at": None,
        "auto_repair_plan": job.get("auto_repair_plan"),
        "pass_history": [],
    }


def _record_provider_decision(
    data: dict[str, Any],
    *,
    provider: str,
    decision: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> None:
    data.setdefault("provider_decisions", [])
    data["provider_decisions"].append({
        "provider": provider,
        "decision": decision,
        "reason": reason,
        "details": details or {},
        "created_at": utc_now(),
    })

def stable_seed(job: dict[str, Any]) -> int:
    raw_seed = job.get("seed")
    if isinstance(raw_seed, int):
        return raw_seed
    return abs(hash(job.get("image_id") or "image")) % 2147483647


def dimensions_for_job(job: dict[str, Any]) -> tuple[int, int]:
    size = image_size_for_aspect_ratio(job.get("aspect_ratio"))
    width_raw, height_raw = size.split("x", 1)
    return int(width_raw), int(height_raw)


def _rounded_dimension(value: float, *, multiple: int) -> int:
    rounded = int(round(value / multiple) * multiple)
    return max(multiple, rounded)


def optimized_dimensions_for_job(job: dict[str, Any], optimization: dict[str, Any] | None = None) -> tuple[int, int]:
    width, height = dimensions_for_job(job)
    if not isinstance(optimization, dict):
        return width, height
    scale = float(optimization.get("dimension_scale") or 1.0)
    max_width = optimization.get("max_width")
    max_height = optimization.get("max_height")
    limit = 1.0
    if isinstance(max_width, int) and max_width > 0:
        limit = min(limit, max_width / width)
    if isinstance(max_height, int) and max_height > 0:
        limit = min(limit, max_height / height)
    scale = min(scale, limit)
    round_to_multiple = int(optimization.get("round_to_multiple") or 64)
    return (
        _rounded_dimension(width * scale, multiple=round_to_multiple),
        _rounded_dimension(height * scale, multiple=round_to_multiple),
    )


def _aspect_ratio_value(value: Any) -> float | None:
    text = str(value or "").strip()
    if ":" not in text:
        return None
    left, right = text.split(":", 1)
    try:
        numerator = float(left)
        denominator = float(right)
    except ValueError:
        return None
    if numerator <= 0 or denominator <= 0:
        return None
    return numerator / denominator


def _qwen_target_size_for_dimensions(width: int, height: int) -> int:
    target_area_side = math.sqrt(max(1, width) * max(1, height))
    return min(QWEN_REFERENCE_TARGET_SIZES, key=lambda candidate: abs(candidate - target_area_side))


def _qwen_target_vl_size_for_dimensions(width: int, height: int) -> int:
    if width <= 0 or height <= 0:
        return 384
    return 392 if width >= height else 384


def _qwen_crop_method_for_dimensions(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "center"
    return "center"


def _qwen_reference_canvas_size(width: int, height: int, target_ratio: float) -> tuple[int, int]:
    if width <= 0 or height <= 0 or target_ratio <= 0:
        return width, height
    current_ratio = width / height
    if abs(current_ratio - target_ratio) < 0.01:
        return width, height
    if current_ratio < target_ratio:
        return int(round(height * target_ratio)), height
    return width, int(round(width / target_ratio))


def _adapt_reference_image_to_aspect_ratio(
    source_path: Path,
    *,
    target_ratio: float,
    output_path: Path,
) -> tuple[Path, dict[str, Any]]:
    with Image.open(source_path) as image:
        base = image.convert("RGB")
        source_width, source_height = base.size
        canvas_width, canvas_height = _qwen_reference_canvas_size(source_width, source_height, target_ratio)
        if canvas_width == source_width and canvas_height == source_height:
            return source_path, {
                "adapted": False,
                "source_width": source_width,
                "source_height": source_height,
                "canvas_width": canvas_width,
                "canvas_height": canvas_height,
            }
        blurred_background = base.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        blur_radius = max(12, int(max(canvas_width, canvas_height) / 48))
        blurred_background = blurred_background.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        foreground_scale = min(canvas_width / source_width, canvas_height / source_height)
        foreground_width = max(1, int(round(source_width * foreground_scale)))
        foreground_height = max(1, int(round(source_height * foreground_scale)))
        foreground = base.resize((foreground_width, foreground_height), Image.Resampling.LANCZOS)
        offset_x = (canvas_width - foreground_width) // 2
        offset_y = (canvas_height - foreground_height) // 2
        blurred_background.paste(foreground, (offset_x, offset_y))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        blurred_background.save(output_path, format="PNG")
        return output_path, {
            "adapted": True,
            "source_width": source_width,
            "source_height": source_height,
            "canvas_width": canvas_width,
            "canvas_height": canvas_height,
            "offset_x": offset_x,
            "offset_y": offset_y,
        }


def copy_selected_output(selected_output: dict[str, Any], target_path: Path) -> None:
    resolved_path = selected_output.get("resolved_path")
    if not isinstance(resolved_path, str) or not resolved_path.strip():
        raise ComfyUIError("ComfyUI output did not resolve to a local file path", kind="output_missing", details=selected_output)
    source = Path(resolved_path)
    if not source.exists() or not source.is_file():
        raise ComfyUIError(f"ComfyUI output file does not exist: {source}", kind="output_missing", details=selected_output)
    if source.stat().st_size <= 0:
        raise ComfyUIError(f"ComfyUI output file is empty: {source}", kind="output_missing", details=selected_output)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target_path)


def _validate_rendered_output_dimensions(
    output_path: Path,
    *,
    requested_width: int,
    requested_height: int,
) -> dict[str, int]:
    with Image.open(output_path) as rendered:
        actual_width, actual_height = rendered.size
    if requested_width > requested_height and actual_width < actual_height:
        raise ComfyUIError(
            (
                "Rendered output fell back to portrait orientation despite a landscape request: "
                f"requested {requested_width}x{requested_height}, got {actual_width}x{actual_height}"
            ),
            kind="output_mismatch",
            details={
                "output_path": str(output_path).replace("\\", "/"),
                "requested_width": requested_width,
                "requested_height": requested_height,
                "actual_width": actual_width,
                "actual_height": actual_height,
            },
        )
    if requested_height > requested_width and actual_height < actual_width:
        raise ComfyUIError(
            (
                "Rendered output fell back to landscape orientation despite a portrait request: "
                f"requested {requested_width}x{requested_height}, got {actual_width}x{actual_height}"
            ),
            kind="output_mismatch",
            details={
                "output_path": str(output_path).replace("\\", "/"),
                "requested_width": requested_width,
                "requested_height": requested_height,
                "actual_width": actual_width,
                "actual_height": actual_height,
            },
        )
    return {
        "actual_width": actual_width,
        "actual_height": actual_height,
    }


def choose_output(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    images = [item for item in outputs if item.get("media_type") == "image"]
    if not images:
        raise ComfyUIError("ComfyUI workflow did not produce any image outputs", kind="output_missing", details=outputs)
    return images[0]


def resolve_workflow_mapping_key_for_job(job: dict[str, Any], explicit_workflow_name: str) -> str:
    if explicit_workflow_name not in AUTO_ROUTED_WORKFLOW_NAMES:
        return explicit_workflow_name
    mapped = str(job.get("comfyui_workflow_mapping_key") or "").strip()
    if mapped:
        return mapped
    routed = str(job.get("comfyui_workflow_name") or "").strip()
    return routed or "txt2img_keyframe"


def resolve_workflow_display_name_for_job(job: dict[str, Any], selected_workflow_mapping_key: str) -> str:
    current_mapping_key = str(job.get("comfyui_workflow_mapping_key") or "").strip()
    routed_name = str(job.get("comfyui_workflow_name") or "").strip()
    if selected_workflow_mapping_key and selected_workflow_mapping_key != current_mapping_key:
        return selected_workflow_mapping_key
    return routed_name or selected_workflow_mapping_key or "txt2img_keyframe"


def _is_qwen_nextscene_workflow(job: dict[str, Any], workflow_mapping_key: str) -> bool:
    if workflow_mapping_key in QWEN_NEXTSCENE_WORKFLOW_MAPPING_KEYS:
        return True
    source_ref = str(job.get("preferred_comfyui_workflow_source_ref") or "").replace("\\", "/").lower()
    return "qwenedit+nextscene" in source_ref


def _non_empty_prompt_lines(value: Any) -> list[str]:
    return [line.strip() for line in str(value or "").splitlines() if line.strip()]


def _nextscene_marker_count(value: Any) -> int:
    return len(re.findall(r"(?i)next\s*scene\s*[:：]", str(value or "")))


def _qwen_nextscene_preflight_block(job: dict[str, Any], workflow_mapping_key: str) -> dict[str, Any] | None:
    if not _is_qwen_nextscene_workflow(job, workflow_mapping_key):
        return None
    image_id = str(job.get("image_id") or "").strip() or None
    reference_images = [
        str(item).replace("\\", "/")
        for item in (job.get("reference_images") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    secondary_reference_images = [
        str(item).replace("\\", "/")
        for item in (job.get("secondary_reference_images") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    prompt_lines = _non_empty_prompt_lines(job.get("prompt"))
    nextscene_marker_count = _nextscene_marker_count(job.get("prompt"))
    route_hint = str(job.get("stage06_route_hint") or "").strip().lower()
    frame_role = str(job.get("frame_role") or "").strip().lower()

    if str(job.get("comfyui_control_mode") or "").strip() != "reference_guided" or job.get("reference_guidance_active") is not True:
        return {
            "image_id": image_id,
            "reason": "Blocked before generation: the local QwenEdit+NextScene workflow must run in reference_guided mode with an active primary character reference.",
            "creator_summary": "当前 Qwen NextScene 路线必须带主角参考图并按 reference_guided 模式执行，不能按 prompt-only 调。",
            "guardrail": "qwen_nextscene_reference_guided_required",
        }
    if len(reference_images) != 1:
        return {
            "image_id": image_id,
            "reason": "Blocked before generation: the local QwenEdit+NextScene workflow only supports one primary reference image in Stage 05 single-shot mode.",
            "creator_summary": "当前 Qwen NextScene 主流程只允许一张主角参考图，不支持零参考图，也不支持双参考图。",
            "guardrail": "qwen_nextscene_single_primary_reference_only",
            "reference_images": reference_images,
        }
    if secondary_reference_images or route_hint == "interaction_handoff" or job.get("stage06_requires_mid_guide") is True or frame_role == "mid":
        return {
            "image_id": image_id,
            "reason": "Blocked before generation: the local QwenEdit+NextScene workflow is restricted to single-subject Stage 06 routes and cannot be used for interaction handoff or mid-guide shots.",
            "creator_summary": "当前 Qwen NextScene 路线只适合 single_subject_motion，不适合 interaction_handoff 或需要 mid guide 的镜头。",
            "guardrail": "qwen_nextscene_single_subject_motion_only",
            "route_hint": route_hint,
            "frame_role": frame_role,
            "secondary_reference_images": secondary_reference_images,
        }
    if len(prompt_lines) > 1 or nextscene_marker_count > 1:
        return {
            "image_id": image_id,
            "reason": "Blocked before generation: the local QwenEdit+NextScene workflow must receive exactly one single-shot prompt, not multiple Next Scene lines.",
            "creator_summary": "当前 Qwen NextScene 主流程只能一次执行一个镜头帧，不能把多条 Next Scene 一起塞进去。",
            "guardrail": "qwen_nextscene_single_shot_prompt_only",
            "prompt_line_count": len(prompt_lines),
            "nextscene_marker_count": nextscene_marker_count,
        }
    return None


def workflow_replacements_for_job(
    job: dict[str, Any],
    nodes: dict[str, Any],
    *,
    width: int,
    height: int,
    seed: int,
    optimization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    style_selector = str(job.get("comfyui_style_selector") or job.get("comfyui_upstream_style_preset") or "").strip()
    candidate_replacements = {
        "positive_prompt": build_provider_prompt(job),
        "negative_prompt": effective_negative_prompt(job),
        "seed": seed,
        "aspect_ratio": str(job.get("aspect_ratio") or "").strip(),
        "width": width,
        "height": height,
        "short_side": min(width, height),
        "long_side": max(width, height),
        "output_prefix": f"Stage05/{job.get('image_id') or 'image'}",
    }
    if "target_size" in nodes:
        candidate_replacements["target_size"] = _qwen_target_size_for_dimensions(width, height)
    if "target_vl_size" in nodes:
        candidate_replacements["target_vl_size"] = _qwen_target_vl_size_for_dimensions(width, height)
    if "crop_method" in nodes:
        candidate_replacements["crop_method"] = _qwen_crop_method_for_dimensions(width, height)
    if style_selector:
        candidate_replacements["style_selector"] = style_selector
        candidate_replacements["upstream_style_preset"] = style_selector
    replacements = {
        field_name: value
        for field_name, value in candidate_replacements.items()
        if field_name in nodes
    }
    style_anchor = str(job.get("comfyui_style_positive_anchor") or "").strip()
    if style_anchor and "style_anchor" in nodes:
        replacements["style_anchor"] = style_anchor
    negative_style_anchor = str(job.get("comfyui_style_negative_anchor") or "").strip()
    if negative_style_anchor and "negative_style_anchor" in nodes:
        replacements["negative_style_anchor"] = negative_style_anchor
    workflow_replacements = optimization.get("workflow_replacements") if isinstance(optimization, dict) else None
    if isinstance(workflow_replacements, dict):
        for field_name, value in workflow_replacements.items():
            if field_name in {"style_selector", "upstream_style_preset"} and style_selector:
                continue
            if field_name in nodes:
                replacements[field_name] = value
    return replacements


def _reference_image_replacements_for_job(
    manifest_path: Path,
    job: dict[str, Any],
    *,
    width: int,
    height: int,
    input_dir: str | Path | None,
    workflow_mapping_key: str,
    nodes: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    reference_slots = [
        ("reference_image_path", 0, "ref_primary"),
        ("reference_image_path_2", 1, "ref_secondary"),
        ("reference_image_path_3", 2, "ref_tertiary"),
    ]
    if not any(field_name in nodes for field_name, _, _ in reference_slots) or job.get("reference_guidance_active") is not True:
        return {}, []
    reference_images = [
        str(item).replace("\\", "/")
        for item in (job.get("reference_images") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    if not reference_images:
        raise ComfyUIError(
            "reference-guided workflow was selected, but no reference_images were provided in the Stage 05 job",
            kind="input_missing",
            details={"image_id": job.get("image_id")},
        )
    replacements: dict[str, Any] = {}
    staged_records: list[dict[str, str]] = []
    for field_name, index, stem_suffix in reference_slots:
        if field_name not in nodes or index >= len(reference_images):
            continue
        source_path = resolve_path(manifest_path, reference_images[index])
        adapted_metadata: dict[str, Any] | None = None
        if index == 0 and workflow_mapping_key in QWEN_NEXTSCENE_WORKFLOW_MAPPING_KEYS:
            target_ratio = _aspect_ratio_value(job.get("aspect_ratio"))
            if target_ratio is None and width > 0 and height > 0:
                target_ratio = width / height
            if isinstance(target_ratio, float) and target_ratio > 0:
                runtime_dir = manifest_path.parent / ".runtime" / "qwen_nextscene_reference_adapt"
                adapted_source_path, adapted_metadata = _adapt_reference_image_to_aspect_ratio(
                    source_path,
                    target_ratio=target_ratio,
                    output_path=runtime_dir / f"{job.get('image_id')}_{stem_suffix}_canvas.png",
                )
                source_path = adapted_source_path
        staged_path = stage_input_file(
            source_path,
            input_dir,
            stem_prefix=f"{job.get('image_id')}_{stem_suffix}",
        )
        replacements[field_name] = staged_path
        record = {
            "source_path": reference_images[index],
            "staged_name": staged_path,
            "slot": field_name,
        }
        if adapted_metadata:
            record["adapted_canvas"] = adapted_metadata
        staged_records.append(record)
    if not replacements:
        raise ComfyUIError(
            "reference-guided workflow was selected, but the mapped workflow does not expose usable reference image inputs",
            kind="workflow_invalid",
            details={"image_id": job.get("image_id")},
        )
    return replacements, staged_records


def repair_preview_path_for_job(manifest_path: Path, job: dict[str, Any]) -> Path:
    runtime_dir = manifest_path.parent / ".runtime" / "stage05_repair_precheck"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / f"{job.get('image_id')}_pass1.png"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--mapping", default=None, help="Optional path to config/workflow_node_mapping.yaml")
    parser.add_argument("--workflow-name", default="txt2img_keyframe", help="Workflow mapping entry to use, or auto-route by Stage 05 route mapping when left as txt2img_keyframe")
    parser.add_argument("--image-id", default=None, help="Optional single image_id to generate")
    parser.add_argument("--dry-run", action="store_true", help="Only refresh comfyui_image_requests.json without calling ComfyUI")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--max-wait-seconds", type=float, default=None, help="Maximum time to wait for each prompt")
    parser.add_argument("--optimization-profile", default=None, help="Optional override for Stage 05 optimization profile, such as preview, balanced, or quality")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Allow this executor to run even when the project brief requested an earlier terminal output")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    if data.get("stage") != "STAGE_05_KEYFRAME_IMAGES":
        print("ERROR: manifest.stage must be STAGE_05_KEYFRAME_IMAGES", file=sys.stderr)
        return 1
    if not args.allow_beyond_requested_scope:
        scope_error = requested_output_scope_guard_message("STAGE_05", compiled_requirements_from_context(data))
        if scope_error:
            print(f"ERROR: {scope_error}", file=sys.stderr)
            return 1

    try:
        config, _ = load_provider_config(config_path=args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    config_errors = validate_provider_config(config)
    if config_errors:
        for error in config_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    settings = get_comfyui_settings(config)
    if not settings["enabled"]:
        print("ERROR: comfyui.enabled is false", file=sys.stderr)
        return 1

    try:
        mapping_data, mapping_path = load_workflow_mapping(mapping_path=args.mapping)
    except ComfyUIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        optimization_config, optimization_config_path = load_stage05_optimization_profiles()
    except Stage05OptimizationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    workflow_cache: dict[str, tuple[dict[str, Any], dict[str, Any], Path]] = {}

    def mapped_workflow_for_name(workflow_name: str) -> tuple[dict[str, Any], dict[str, Any], Path]:
        cached = workflow_cache.get(workflow_name)
        if cached is not None:
            return cached
        loaded = load_mapped_workflow(mapping_data, workflow_name)
        workflow_cache[workflow_name] = loaded
        return loaded

    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        print("ERROR: manifest.jobs must be a non-empty list", file=sys.stderr)
        return 1
    selected_jobs = [job for job in jobs if isinstance(job, dict) and (args.image_id is None or job.get("image_id") == args.image_id)]
    if args.image_id and not selected_jobs:
        print(f"ERROR: image_id not found in manifest: {args.image_id}", file=sys.stderr)
        return 1
    missing_reference_blocks_by_image_id: dict[str, dict[str, Any]] = {}
    preflight_blocks_by_image_id: dict[str, dict[str, Any]] = {}
    for job in selected_jobs:
        block = missing_character_reference_block(job)
        if block:
            missing_reference_blocks_by_image_id[str(job.get("image_id") or "")] = block

    request_records: list[dict[str, Any]] = []
    workflow_paths_used: list[str] = []
    workflow_mapping_keys_used: list[str] = []
    optimization_profiles_used: list[str] = []
    optimization_labels_used: list[str] = []
    for job in selected_jobs:
        workflow_name = resolve_workflow_mapping_key_for_job(job, str(args.workflow_name or ""))
        image_id = str(job.get("image_id") or "")
        if image_id not in missing_reference_blocks_by_image_id:
            preflight_block = _qwen_nextscene_preflight_block(job, workflow_name)
            if preflight_block:
                preflight_blocks_by_image_id[image_id] = preflight_block
        try:
            _, _, workflow_path = mapped_workflow_for_name(workflow_name)
        except ComfyUIError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        try:
            optimization = resolve_stage05_workflow_optimization(
                optimization_config,
                workflow_name,
                requested_profile=args.optimization_profile or job.get("comfyui_optimization_profile"),
            )
        except Stage05OptimizationError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        width, height = optimized_dimensions_for_job(job, optimization)
        job["auto_repair_plan"] = build_auto_repair_plan(job, job.get("quality_gate") if isinstance(job.get("quality_gate"), dict) else None)
        request_records.append(
            request_record(
                job,
                workflow_name,
                workflow_path,
                optimization_profile=optimization["profile_key"],
                optimization_profile_label=optimization["profile_label"],
                width=width,
                height=height,
            )
        )
        blocked = missing_reference_blocks_by_image_id.get(image_id) or preflight_blocks_by_image_id.get(image_id)
        if blocked:
            message = str(blocked["reason"])
            missing_reference_images = [str(item) for item in (blocked.get("missing_reference_images") or []) if str(item).strip()]
            if missing_reference_images:
                message = f"{message} Missing reference image(s): " + ", ".join(missing_reference_images)
            append_blocked(job, "comfyui_txt2img", message, details=blocked)
            request_records[-1].update({
                "status": "blocked",
                "error_message": message,
                "completed_at": utc_now(),
                "blocked_reason": blocked["reason"],
                "missing_reference_images": blocked.get("missing_reference_images") or [],
                "reference_images": blocked.get("reference_images") or [],
            })
        if workflow_name not in workflow_mapping_keys_used:
            workflow_mapping_keys_used.append(workflow_name)
        workflow_path_text = str(workflow_path).replace("\\", "/")
        if workflow_path_text not in workflow_paths_used:
            workflow_paths_used.append(workflow_path_text)
        if optimization["profile_key"] not in optimization_profiles_used:
            optimization_profiles_used.append(optimization["profile_key"])
        if optimization["profile_label"] and optimization["profile_label"] not in optimization_labels_used:
            optimization_labels_used.append(optimization["profile_label"])
    selected_workflow_mapping_key = workflow_mapping_keys_used[0] if len(workflow_mapping_keys_used) == 1 else None
    selected_optimization_profile = optimization_profiles_used[0] if len(optimization_profiles_used) == 1 else None
    selected_optimization_label = optimization_labels_used[0] if len(optimization_labels_used) == 1 else None
    selected_model_id = request_records[0]["comfyui_model_id"] if request_records and len({record.get("comfyui_model_id") for record in request_records}) == 1 else data.get("comfyui_model_id")
    selected_preferred_workflow_candidate = request_records[0]["preferred_comfyui_workflow_candidate"] if request_records and len({record.get("preferred_comfyui_workflow_candidate") for record in request_records}) == 1 else data.get("preferred_comfyui_workflow_candidate")
    selected_preferred_model_candidate = request_records[0]["preferred_comfyui_model_candidate"] if request_records and len({record.get("preferred_comfyui_model_candidate") for record in request_records}) == 1 else data.get("preferred_comfyui_model_candidate")
    selected_workflow_source_ref = request_records[0]["preferred_comfyui_workflow_source_ref"] if request_records and len({record.get("preferred_comfyui_workflow_source_ref") for record in request_records}) == 1 else data.get("preferred_comfyui_workflow_source_ref")
    selected_control_mode = request_records[0]["comfyui_control_mode"] if request_records and len({record.get("comfyui_control_mode") for record in request_records}) == 1 else data.get("comfyui_control_mode")

    requests_path = manifest_path.parent / "comfyui_image_requests.json"
    request_manifest = {
        "provider": "comfyui_txt2img",
        "workflow_name": "auto_style_family" if str(args.workflow_name or "") in AUTO_ROUTED_WORKFLOW_NAMES else args.workflow_name,
        "workflow_selection_mode": "stage05_route_registry" if str(args.workflow_name or "") in AUTO_ROUTED_WORKFLOW_NAMES else "explicit_workflow_override",
        "stage05_route_key": data.get("stage05_route_key"),
        "route_resolution_mode": (data.get("route_resolution") or {}).get("resolution_mode"),
        "workflow_mapping_key": selected_workflow_mapping_key,
        "workflow_mapping_keys": workflow_mapping_keys_used,
        "workflow_mapping_path": str(mapping_path).replace("\\", "/"),
        "optimization_profile": selected_optimization_profile,
        "optimization_profile_label": selected_optimization_label,
        "optimization_profile_source": str(optimization_config_path).replace("\\", "/"),
        "workflow_path": workflow_paths_used[0] if len(workflow_paths_used) == 1 else None,
        "workflow_paths": workflow_paths_used,
        "comfyui_model_id": selected_model_id,
        "preferred_comfyui_workflow_candidate": selected_preferred_workflow_candidate,
        "preferred_comfyui_model_candidate": selected_preferred_model_candidate,
        "route_migration_state": data.get("route_migration_state"),
        "preferred_comfyui_workflow_source_ref": selected_workflow_source_ref,
        "preferred_comfyui_workflow_format": data.get("preferred_comfyui_workflow_format"),
        "preferred_comfyui_workflow_custom_node_dependencies": data.get("preferred_comfyui_workflow_custom_node_dependencies"),
        "preferred_comfyui_workflow_import_blockers": data.get("preferred_comfyui_workflow_import_blockers"),
        "comfyui_style_preset_key": data.get("comfyui_style_preset_key"),
        "comfyui_style_preset_label": data.get("comfyui_style_preset_label"),
        "comfyui_control_mode": selected_control_mode,
        "creator_runtime_feedback": data.get("creator_runtime_status"),
        "generated_at": utc_now(),
        "requests": request_records,
    }
    requests_by_id = {record["image_id"]: record for record in request_manifest["requests"]}
    write_json(requests_path, request_manifest)
    runnable_jobs = [
        job
        for job in selected_jobs
        if isinstance(job, dict) and str(job.get("status") or "").strip().lower() != "blocked"
    ]
    if missing_reference_blocks_by_image_id:
        blocked_payload = list(missing_reference_blocks_by_image_id.values())
        _record_provider_decision(
            data,
            provider="manual",
            decision="manual_recovery_required",
            reason="missing_character_reference_before_generation",
            details={
                "blocked_image_ids": [item.get("image_id") for item in blocked_payload],
                "missing_reference_images": [
                    path_text
                    for item in blocked_payload
                    for path_text in item.get("missing_reference_images", [])
                ],
            },
        )
        data["manual_recovery"] = build_missing_reference_manual_recovery(manifest_path, blocked_payload)
        data["creator_runtime_status"] = {
            "headline": "已阻断高风险关键帧自动生成，先补角色参考图。",
            "detail": "当前镜头属于 character-locked 高风险镜头，缺少 Stage 03 参考图时继续生图最容易前后换人。",
            "source_provider": "comfyui_txt2img",
            "active_provider": "manual",
            "created_at": utc_now(),
        }
    if preflight_blocks_by_image_id:
        blocked_payload = list(preflight_blocks_by_image_id.values())
        _record_provider_decision(
            data,
            provider="comfyui_txt2img",
            decision="preflight_blocked",
            reason="qwen_nextscene_single_shot_guardrail",
            details={
                "blocked_image_ids": [item.get("image_id") for item in blocked_payload],
                "guardrails": [item.get("guardrail") for item in blocked_payload],
            },
        )
        data["creator_runtime_status"] = {
            "headline": "已阻断 Qwen NextScene 误调用。",
            "detail": "当前镜头命中了 Qwen NextScene 单镜头护栏：它只能带一张主参考图、只吃一条单镜头 prompt，并且只适配 single_subject_motion。",
            "source_provider": "comfyui_txt2img",
            "active_provider": "comfyui_txt2img",
            "created_at": utc_now(),
        }
    if args.dry_run:
        if missing_reference_blocks_by_image_id or preflight_blocks_by_image_id:
            update_manifest_state(data, manifest_path)
            write_json(manifest_path, data)
            print(f"COMFYUI TXT2IMG DRY RUN BLOCKED: {manifest_path}")
            return 1
        print(f"COMFYUI REQUEST MANIFEST UPDATED: {requests_path}")
        return 0
    if not runnable_jobs:
        update_manifest_state(data, manifest_path)
        write_json(manifest_path, data)
        print(f"COMFYUI TXT2IMG BLOCKED: {manifest_path}")
        return 1

    client = ComfyUIClient(
        base_url=settings["base_url"],
        timeout_seconds=settings["timeout_seconds"],
        retry_count=settings["retry_count"],
        output_dir=settings["output_dir"] or None,
    )
    failed = False
    for job in runnable_jobs:
        request_item = requests_by_id[job["image_id"]]
        request_item["requested_at"] = utc_now()
        try:
            workflow_name = resolve_workflow_mapping_key_for_job(job, str(args.workflow_name or ""))
            workflow_display_name = resolve_workflow_display_name_for_job(job, workflow_name)
            workflow_template, mapping_entry, _ = mapped_workflow_for_name(workflow_name)
            optimization = resolve_stage05_workflow_optimization(
                optimization_config,
                workflow_name,
                requested_profile=args.optimization_profile or job.get("comfyui_optimization_profile"),
            )
            width, height = optimized_dimensions_for_job(job, optimization)
            seed = stable_seed(job)
            auto_repair_plan = build_auto_repair_plan(job, job.get("quality_gate") if isinstance(job.get("quality_gate"), dict) else None)
            job["auto_repair_plan"] = auto_repair_plan
            request_item["auto_repair_plan"] = auto_repair_plan
            base_job = dict(job)
            reference_replacements, staged_reference_images = _reference_image_replacements_for_job(
                manifest_path,
                base_job,
                width=width,
                height=height,
                input_dir=settings["input_dir"],
                workflow_mapping_key=workflow_name,
                nodes=mapping_entry["nodes"],
            )
            replacements = {
                **workflow_replacements_for_job(
                    base_job,
                    mapping_entry["nodes"],
                    width=width,
                    height=height,
                    seed=seed,
                    optimization=optimization,
                ),
                **reference_replacements,
            }
            workflow_format = comfyui_ui_workflow.resolve_workflow_format(mapping_entry)
            if workflow_format == "ui_graph":
                patched_workflow = comfyui_ui_workflow.apply_ui_node_inputs(
                    workflow_template,
                    mapping_entry["nodes"],
                    replacements,
                )
                submission_payload = comfyui_ui_workflow.convert_ui_workflow_to_prompt(
                    patched_workflow,
                    base_url=settings["base_url"],
                    node_modules_dir=(Path.cwd() / ".tmp-playwright" / "node_modules"),
                )
                workflow = submission_payload["prompt"]
                extra_data = submission_payload.get("extra_data")
            else:
                workflow = apply_node_inputs(
                    workflow_template,
                    mapping_entry["nodes"],
                    replacements,
                )
                extra_data = None
            if staged_reference_images:
                request_item["staged_reference_images"] = staged_reference_images
            submitted = client.submit_prompt(workflow, extra_data=extra_data)
            request_item["prompt_id"] = submitted["prompt_id"]
            history_entry = client.wait_for_prompt(
                str(submitted["prompt_id"]),
                poll_interval=args.poll_interval,
                max_wait_seconds=args.max_wait_seconds,
            )
            outputs = client.collect_outputs(history_entry)
            selected_output = choose_output(outputs)
            pass_history = request_item.setdefault("pass_history", [])
            pass_history.append({
                "pass_name": "base_pass",
                "prompt_id": submitted["prompt_id"],
                "seed": seed,
                "status": "succeeded",
            })
            final_output = selected_output
            final_seed = seed
            repair_status = "not_needed"
            if auto_repair_plan.get("enabled"):
                preview_path = repair_preview_path_for_job(manifest_path, job)
                copy_selected_output(selected_output, preview_path)
                job["repair_preview_path"] = str(preview_path).replace("\\", "/")
                repair_job = dict(job)
                repair_job["repair_prompt_sections"] = auto_repair_plan.get("repair_prompt_sections") or []
                repair_job["repair_negative_prompt_additions"] = auto_repair_plan.get("repair_negative_hints") or []
                repair_seed = seed + 9973
                try:
                    repair_replacements = {
                        **workflow_replacements_for_job(
                            repair_job,
                            mapping_entry["nodes"],
                            width=width,
                            height=height,
                            seed=repair_seed,
                            optimization=optimization,
                        ),
                        **reference_replacements,
                    }
                    if workflow_format == "ui_graph":
                        patched_repair_workflow = comfyui_ui_workflow.apply_ui_node_inputs(
                            workflow_template,
                            mapping_entry["nodes"],
                            repair_replacements,
                        )
                        repair_submission_payload = comfyui_ui_workflow.convert_ui_workflow_to_prompt(
                            patched_repair_workflow,
                            base_url=settings["base_url"],
                            node_modules_dir=(Path.cwd() / ".tmp-playwright" / "node_modules"),
                        )
                        repair_workflow = repair_submission_payload["prompt"]
                        repair_extra_data = repair_submission_payload.get("extra_data")
                    else:
                        repair_workflow = apply_node_inputs(
                            workflow_template,
                            mapping_entry["nodes"],
                            repair_replacements,
                        )
                        repair_extra_data = None
                    repair_submitted = client.submit_prompt(repair_workflow, extra_data=repair_extra_data)
                    repair_history_entry = client.wait_for_prompt(
                        str(repair_submitted["prompt_id"]),
                        poll_interval=args.poll_interval,
                        max_wait_seconds=args.max_wait_seconds,
                    )
                    repair_outputs = client.collect_outputs(repair_history_entry)
                    repair_output = choose_output(repair_outputs)
                    final_output = repair_output
                    final_seed = repair_seed
                    repair_status = "auto_second_pass_succeeded"
                    pass_history.append({
                        "pass_name": "repair_pass",
                        "prompt_id": repair_submitted["prompt_id"],
                        "seed": repair_seed,
                        "status": "succeeded",
                    })
                except ComfyUIError as repair_exc:
                    repair_status = "repair_failed_fell_back_to_first_pass"
                    pass_history.append({
                        "pass_name": "repair_pass",
                        "prompt_id": None,
                        "seed": repair_seed,
                        "status": "failed",
                        "error_message": str(repair_exc),
                    })
            output_path = resolve_path(manifest_path, job.get("output_path") or job.get("evidence", {}).get("file_path"))
            copy_selected_output(final_output, output_path)
            output_dimensions = _validate_rendered_output_dimensions(
                output_path,
                requested_width=width,
                requested_height=height,
            )
            job["provider"] = "comfyui_txt2img"
            job["status"] = "succeeded"
            job["seed"] = final_seed
            job["errors"] = []
            job.setdefault("evidence", {})
            job["evidence"].update({
                "file_path": str(output_path).replace("\\", "/"),
                "file_exists": True,
                "file_size_bytes": output_path.stat().st_size,
                "image_width": output_dimensions["actual_width"],
                "image_height": output_dimensions["actual_height"],
                "created_at": utc_now(),
            })
            job["auto_repair_status"] = repair_status
            route_key = str(job.get("stage05_route_key") or "")
            route_prefix = f"route={route_key}; " if route_key else ""
            mapping_prefix = f"mapping={workflow_name}; " if workflow_name != workflow_display_name else ""
            migration_state = str(job.get("route_migration_state") or "").strip()
            migration_prefix = f"route_state={migration_state}; " if migration_state else ""
            preferred_workflow = str(job.get("preferred_comfyui_workflow_candidate") or "").strip()
            preferred_prefix = f"preferred_workflow={preferred_workflow}; " if preferred_workflow else ""
            optimization_prefix = f"profile={optimization['profile_key']}; size={width}x{height}; "
            repair_prefix = f"repair={repair_status}; " if repair_status != "not_needed" else ""
            job["notes"] = (
                f"{route_prefix}{migration_prefix}{preferred_prefix}"
                f"{optimization_prefix}{repair_prefix}{mapping_prefix}workflow={workflow_display_name}; prompt_id={submitted['prompt_id']}"
            )
            creator_review_card = build_creator_review_card(job, job.get("quality_gate"), auto_repair_status=repair_status)
            if creator_review_card:
                creator_review_card["repair_preview_path"] = job.get("repair_preview_path")
                job["creator_review_card"] = creator_review_card
            request_item.update({
                "status": "succeeded",
                "completed_at": utc_now(),
                "prompt_id": submitted["prompt_id"],
                "selected_output": final_output,
                "repair_status": repair_status,
                **output_dimensions,
            })
        except ComfyUIError as exc:
            failed = True
            append_error(job, "comfyui_txt2img", str(exc))
            request_item.update({
                "status": "failed",
                "completed_at": utc_now(),
                "error_message": str(exc),
            })
            if args.fail_fast:
                break

    update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    request_manifest["generated_at"] = utc_now()
    write_json(requests_path, request_manifest)

    if failed or missing_reference_blocks_by_image_id or preflight_blocks_by_image_id:
        print(f"COMFYUI TXT2IMG COMPLETED WITH FAILURES: {manifest_path}")
        return 1
    print(f"COMFYUI TXT2IMG COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
