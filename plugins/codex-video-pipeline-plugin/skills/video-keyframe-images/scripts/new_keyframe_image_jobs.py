#!/usr/bin/env python3
"""Create Stage 05 keyframe image generation jobs from Stage 04 prompts.

Usage:
  python new_keyframe_image_jobs.py <locked_brief.json> <keyframe_prompts.json> <keyframe_image_manifest.json>
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "providers"))
from pipeline_core.pipeline_blueprints import routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.quality_contracts import build_quality_contract, build_stage_quality_targets  # noqa: E402
from pipeline_core.stage05_optimization_profiles import (  # noqa: E402
    Stage05OptimizationError,
    load_stage05_optimization_profiles,
    resolve_stage05_workflow_optimization,
)
from pipeline_core.stage05_quality_gates import build_quality_gate, summarize_quality_review  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage, stage_meets_requested_output  # noqa: E402
from pipeline_core.stage05_route_registry import (  # noqa: E402
    RouteRegistryError,
    get_stage05_route_entry,
    get_stage05_route_for_style,
    load_stage05_route_registry,
    resolve_named_style_preset,
    resolve_route_style_preset,
    resolve_current_comfyui_target,
)
from pipeline_core.stage06_risk_profiles import classify_stage06_generation  # noqa: E402
from stage05_image_utils import write_stage05_manual_review_files, write_stage05_prompt_patch_files  # noqa: E402
from workflow_mapping import get_workflow_mapping, load_workflow_mapping, resolve_workflow_capabilities  # noqa: E402


STYLE_FAMILY_TO_WORKFLOW = {
    "realistic": "txt2img_keyframe_realistic",
    "anime": "txt2img_keyframe_anime",
    "guofeng": "txt2img_keyframe_guofeng",
    "stylized": "txt2img_keyframe_stylized",
}

ANIME_STYLE_HINTS = (
    "日系动画",
    "日本动漫",
    "国漫动画",
    "中国动画",
    "美式动画",
    "卡通",
    "动漫",
    "anime",
    "manga",
    "cel shading",
    "cel-shading",
    "key visual",
    "line art",
)
GUOFENG_STYLE_HINTS = (
    "国风水墨",
    "古风",
    "国风",
    "水墨",
    "guofeng",
    "ink wash",
    "brush texture",
    "poetic composition",
)
STYLIZED_STYLE_HINTS = (
    "赛博朋克",
    "暗黑惊悚",
    "高饱和潮流",
    "游戏cg",
    "游戏CG",
    "stylized",
    "concept art",
    "illustrative rendering",
    "bold shape design",
    "dramatic color",
)

GUOFENG_SCENIC_CAMERA_HINTS = (
    "medium scenic shot",
    "wide scenic shot",
    "scenic shot",
    "wide shot",
    "landscape shot",
)

GUOFENG_SCENIC_PROMPT_HINTS = (
    "umbrella",
    "oil-paper umbrella",
    "misty rain",
    "mist",
    "riverside",
    "riverbank",
    "pavilion",
)

INTERACTION_HANDOFF_ROUTE_HINT = "interaction_handoff"


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def parse_visual_spec(brief: dict) -> tuple[str, str]:
    # Prefer locked normalized values so downstream stages honor the confirmed Stage 00 spec.
    normalized = normalized_brief(brief)
    aspect = (
        normalized.get("aspect_ratio")
        or brief.get("aspect_ratio")
        or brief.get("visual_spec", {}).get("aspect_ratio")
        or "9:16"
    )
    resolution = (
        normalized.get("resolution")
        or brief.get("resolution")
        or brief.get("visual_spec", {}).get("resolution")
        or "1080P"
    )
    return str(aspect), str(resolution)


def normalized_brief(brief: dict) -> dict:
    normalized = brief.get("normalized")
    return normalized if isinstance(normalized, dict) else brief


def resolve_related_json(base_json: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = Path(str(raw))
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [Path.cwd(), base_json.parent, *base_json.parents]:
        key = str(anchor.resolve()).lower()
        if key not in seen:
            anchors.append(anchor)
            seen.add(key)
    for anchor in anchors:
        resolved = (anchor / candidate).resolve()
        if resolved.exists():
            return resolved
    for anchor in anchors:
        resolved = (anchor / candidate).resolve()
        if resolved.parent.exists():
            return resolved
    return (base_json.parent / candidate).resolve()


def resolve_related_asset(base_json: Path, raw: str | None) -> Path | None:
    return resolve_related_json(base_json, raw)


def storyboard_lookup_from_prompts(prompts: dict, prompts_path: Path) -> dict[str, dict]:
    raw_path = prompts.get("source_storyboard")
    storyboard_path = resolve_related_json(prompts_path, str(raw_path)) if raw_path else None
    if storyboard_path is None or not storyboard_path.exists():
        return {}
    storyboard = load_json(storyboard_path)
    return {
        str(shot.get("shot_id") or "").strip(): shot
        for shot in (storyboard.get("shots") or [])
        if isinstance(shot, dict) and str(shot.get("shot_id") or "").strip()
    }


def build_stage05_story_bundle(shot_prompt: dict, storyboard_shot: dict) -> dict[str, str]:
    bundle = shot_prompt.get("story_anchor_bundle")
    bundle_data = dict(bundle) if isinstance(bundle, dict) else {}
    return {
        "location": str(bundle_data.get("location") or storyboard_shot.get("location") or "").strip(),
        "weather": str(bundle_data.get("weather") or storyboard_shot.get("weather") or "").strip(),
        "key_prop": str(bundle_data.get("key_prop") or storyboard_shot.get("key_prop") or "").strip(),
        "emotion": str(bundle_data.get("emotion") or storyboard_shot.get("emotion") or "").strip(),
        "composition_focus": str(bundle_data.get("composition_focus") or storyboard_shot.get("composition_focus") or "").strip(),
        "action": str(
            bundle_data.get("action")
            or storyboard_shot.get("action")
            or shot_prompt.get("intent_summary")
            or shot_prompt.get("scene_summary")
            or ""
        ).strip(),
    }


def classify_stage05_frame_plan(shot_prompt: dict, storyboard_shot: dict) -> dict:
    bundle = build_stage05_story_bundle(shot_prompt, storyboard_shot)
    profile = classify_stage06_generation(shot_prompt, storyboard_shot or {}, bundle)
    required_roles = ["start", "end"]
    if str(profile.get("route_hint") or "").strip() == "interaction_handoff":
        required_roles = ["start", "mid", "end"]
    return {
        "bundle": bundle,
        "generation_profile": profile,
        "required_roles": required_roles,
        "requires_mid": "mid" in required_roles,
    }


def build_mid_keyframe_prompt(
    shot_prompt: dict,
    storyboard_shot: dict,
    bundle: dict[str, str],
    *,
    global_subject: str,
    aspect_ratio: str,
) -> str:
    existing = str(shot_prompt.get("mid_keyframe_prompt") or "").strip()
    if existing:
        return existing
    subject = str(global_subject or storyboard_shot.get("subject") or "主体").strip() or "主体"
    location = bundle.get("location") or "当前场景"
    weather = bundle.get("weather") or "当前氛围"
    action = bundle.get("action") or "推进到动作中段"
    key_prop = bundle.get("key_prop") or "关键道具"
    emotion = bundle.get("emotion") or "当前情绪"
    composition = bundle.get("composition_focus") or "交接动作与人物关系必须清晰可读"
    base_consistency = str(shot_prompt.get("consistency_prompt") or "").strip()
    continuity_clause = base_consistency or f"{subject} 在{weather}{location}中的外观、服装和道具关系要保持完全一致，便于跨镜头识别。"
    return (
        f"cinematic midpoint frame, location {location}, weather {weather}, subject {subject}, "
        f"action midpoint of {action}, key prop {key_prop}, emotion {emotion}, composition focus {composition}, "
        f"keep both giver and receiver readable in the same frame, exactly one shared {key_prop}, "
        f"readable handoff contact, stable frontal camera, no extra limbs, no duplicated prop, "
        f"{continuity_clause}, vertical {aspect_ratio} composition"
    )


def interaction_handoff_prompt_suffix(*, key_prop: str) -> str:
    readable_prop = key_prop or "shared prop"
    return (
        f"capture the real transfer moment of {readable_prop}, one person is releasing the handle while the other is receiving it, "
        "avoid symmetrical posing, keep both bodies slightly offset, preserve a believable grip transition, "
        "make the contact point readable, and keep the motion feeling alive rather than staged"
    )


def interaction_handoff_negative_suffix(*, key_prop: str) -> str:
    readable_prop = key_prop or "prop"
    return (
        f"frozen handoff pose, mirrored posture, both people separately owning {readable_prop}, "
        f"duplicated {readable_prop}, extra hands, broken grip, floating handle, ambiguous transfer timing"
    )


def project_relative_path(project_root: Path, target_path: Path) -> str:
    return str(target_path.resolve().relative_to(project_root.resolve())).replace("\\", "/")


def interaction_handoff_secondary_reference_images(
    *,
    project_root: Path,
    keyframes_dir: Path,
    shot_id: str,
    frame_role: str,
) -> list[str]:
    preferred_roles = {
        "start": ("mid", "end"),
        "mid": ("start", "end"),
        "end": ("mid", "start"),
    }.get(frame_role, ("start", "mid", "end"))
    references: list[str] = []
    for candidate_role in preferred_roles:
        candidate_path = keyframes_dir / f"{shot_id}_{candidate_role}.png"
        if not candidate_path.exists() or not candidate_path.is_file():
            continue
        if candidate_path.stat().st_size <= 0:
            continue
        references.append(project_relative_path(project_root, candidate_path))
        if len(references) >= 1:
            break
    return references


def build_identity_anchor_fallback(shot_prompt: dict, storyboard_shot: dict, *, global_subject: str) -> str:
    explicit = str(shot_prompt.get("identity_anchor_prompt") or "").strip()
    if explicit:
        return explicit
    subject = str(global_subject or storyboard_shot.get("subject") or "主体").strip() or "主体"
    shot_text = " ".join(
        str(item or "").strip()
        for item in [
            shot_prompt.get("intent_summary"),
            shot_prompt.get("scene_summary"),
            storyboard_shot.get("action"),
            storyboard_shot.get("composition"),
        ]
        if str(item or "").strip()
    ).lower()
    if any(marker in shot_text for marker in ["陌生人", "对方", "stranger", "another person", "receiver", "handoff", "留给", "交给", "递给"]):
        return (
            f"Character identity anchor: primary protagonist remains {subject} in every frame. "
            "A secondary receiver may appear, but do not swap protagonist identity, hairstyle, clothing silhouette, or body proportions."
        )
    return (
        f"Character identity anchor: keep the same protagonist {subject} in every frame, "
        "with stable face shape, hairstyle, outfit silhouette, body proportions, and carried accessories."
    )


def _contains_any_hint(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in hints)


REALISTIC_ESTABLISHING_CAMERA_HINTS = (
    "establishing shot",
    "wide shot",
    "wide coastal establishing shot",
    "wide environmental shot",
    "wide lifestyle establishing shot",
    "wide editorial establishing shot",
    "wide advertising establishing shot",
    "wide interior establishing shot",
)

REALISTIC_ESTABLISHING_PROMPT_HINTS = (
    "shoreline",
    "beach",
    "sea",
    "coast",
    "coastal",
    "harbor",
    "pier",
    "street",
    "skyline",
    "sunset",
    "dusk",
)


def _is_original_zimage_ui_workflow(source_ref: str | None) -> bool:
    return "/workflows/zimage/amazing-z-" in str(source_ref or "").replace("\\", "/").lower()


def sanitize_stage04_prompt_for_zimage(
    prompt_text: str,
    *,
    shot_prompt: dict[str, Any],
    aspect_ratio: str,
) -> str:
    cleaned = str(prompt_text or "").strip()
    shot_id = str(shot_prompt.get("shot_id") or "").strip()
    for prefix in [
        "cinematic keyframe,",
        f"cinematic continuation of {shot_id},",
    ]:
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
    removable_chunks = [
        str(shot_prompt.get("camera_prompt") or "").strip(),
        str(shot_prompt.get("lighting_prompt") or "").strip(),
        str(shot_prompt.get("style_prompt") or "").strip(),
        str(shot_prompt.get("consistency_prompt") or "").strip(),
        str(shot_prompt.get("identity_anchor_prompt") or "").strip(),
        "do not swap protagonist identity",
        f"emotion: {str(shot_prompt.get('story_anchor_bundle', {}).get('emotion') or shot_prompt.get('emotion') or '').strip()}".strip(),
        f"{aspect_ratio} composition".strip(),
    ]
    for chunk in removable_chunks:
        if chunk:
            cleaned = cleaned.replace(chunk, " ")
    parts = [
        part.strip()
        for part in cleaned.replace(";", ",").split(",")
        if part.strip()
    ]
    return ", ".join(parts)


def route_style_preset_override_key(
    *,
    route_key: str,
    shot_prompt: dict,
    storyboard_shot: dict,
) -> str | None:
    if route_key == "realistic_cinematic":
        camera_text = " ".join(
            str(item or "").strip()
            for item in [
                shot_prompt.get("camera_prompt"),
                storyboard_shot.get("camera"),
                storyboard_shot.get("composition"),
            ]
            if str(item or "").strip()
        ).lower()
        prompt_text = " ".join(
            str(item or "").strip()
            for item in [
                shot_prompt.get("scene_summary"),
                shot_prompt.get("start_keyframe_prompt"),
                shot_prompt.get("end_keyframe_prompt"),
                storyboard_shot.get("action"),
                storyboard_shot.get("location"),
            ]
            if str(item or "").strip()
        ).lower()
        if _contains_any_hint(camera_text, REALISTIC_ESTABLISHING_CAMERA_HINTS) and _contains_any_hint(prompt_text, REALISTIC_ESTABLISHING_PROMPT_HINTS):
            return "environmental_establishing_film"
        return None
    if route_key != "guofeng_ink":
        return None
    camera_text = " ".join(
        str(item or "").strip()
        for item in [
            shot_prompt.get("camera_prompt"),
            storyboard_shot.get("camera"),
            storyboard_shot.get("composition"),
        ]
        if str(item or "").strip()
    ).lower()
    prompt_text = " ".join(
        str(item or "").strip()
        for item in [
            shot_prompt.get("scene_summary"),
            shot_prompt.get("start_keyframe_prompt"),
            shot_prompt.get("end_keyframe_prompt"),
            shot_prompt.get("style_prompt"),
            storyboard_shot.get("action"),
            storyboard_shot.get("location"),
        ]
        if str(item or "").strip()
    ).lower()
    if _contains_any_hint(camera_text, GUOFENG_SCENIC_CAMERA_HINTS) and _contains_any_hint(prompt_text, GUOFENG_SCENIC_PROMPT_HINTS):
        return "scenic_single_subject_umbrella"
    return None


def infer_style_family(brief: dict, prompts: dict) -> str:
    normalized = normalized_brief(brief)
    style = str(normalized.get("style") or brief.get("style") or "").strip()
    genre = str(normalized.get("genre") or brief.get("genre") or "").strip()
    joined = " ".join(
        [
            style,
            genre,
            str(prompts.get("prompt_language") or ""),
            *[
                str(shot.get("style_prompt") or "")
                for shot in (prompts.get("shot_prompts") or [])
                if isinstance(shot, dict)
            ],
        ]
    ).lower()
    if any(keyword.lower() in joined for keyword in ANIME_STYLE_HINTS):
        return "anime"
    if any(keyword.lower() in joined for keyword in GUOFENG_STYLE_HINTS):
        return "guofeng"
    if any(keyword.lower() in joined for keyword in STYLIZED_STYLE_HINTS):
        return "stylized"
    return "realistic"


def resolve_stage05_route(brief: dict, prompts: dict) -> dict:
    normalized = normalized_brief(brief)
    style = str(normalized.get("style") or brief.get("style") or "").strip()
    fallback_style_family = infer_style_family(brief, prompts)
    fallback_workflow_name = STYLE_FAMILY_TO_WORKFLOW[fallback_style_family]
    reference_image_status = prompts.get("reference_image_status") if isinstance(prompts.get("reference_image_status"), dict) else {}
    stage05_execution_readiness = (
        prompts.get("stage05_execution_readiness") if isinstance(prompts.get("stage05_execution_readiness"), dict) else {}
    )
    reference_guided_requested = bool(stage05_execution_readiness.get("reference_image_required"))
    reference_guided_ready = bool(reference_guided_requested and reference_image_status.get("all_present"))
    resolved = {
        "route_key": fallback_style_family,
        "style_family": fallback_style_family,
        "comfyui_workflow_mapping_key": fallback_workflow_name,
        "comfyui_workflow_name": fallback_workflow_name,
        "comfyui_model_id": None,
        "comfyui_style_selector": None,
        "prompt_only_workflow_mapping_key": fallback_workflow_name,
        "prompt_only_workflow_name": fallback_workflow_name,
        "prompt_only_comfyui_model_id": None,
        "prompt_only_preferred_comfyui_workflow_candidate": None,
        "prompt_only_preferred_comfyui_workflow_source_ref": None,
        "preferred_comfyui_workflow_candidate": None,
        "preferred_comfyui_model_candidate": None,
        "route_migration_state": None,
        "preferred_comfyui_workflow_source_ref": None,
        "preferred_comfyui_workflow_format": None,
        "preferred_comfyui_workflow_custom_node_dependencies": None,
        "preferred_comfyui_workflow_import_blockers": None,
        "comfyui_style_preset_key": None,
        "comfyui_style_preset_label": None,
        "comfyui_style_positive_anchor": None,
        "comfyui_style_negative_anchor": None,
        "comfyui_control_mode": "prompt_only",
        "stage00_style": style,
        "registry_path": None,
        "used_registry": False,
        "resolution_mode": "legacy_style_family_fallback",
        "workflow_mapping_resolution": "legacy_style_family_fallback",
        "reference_guided_route_selected": False,
    }
    if not style:
        return resolved

    try:
        registry, registry_path = load_stage05_route_registry(root=ROOT)
        route_key, style_entry, route_entry = get_stage05_route_for_style(registry, style)
    except RouteRegistryError:
        return resolved

    comfyui_target = resolve_current_comfyui_target(route_key, route_entry)
    style_preset = resolve_route_style_preset(style_entry, route_entry)
    workflow_name = str(comfyui_target.get("workflow_name") or "").strip() or fallback_workflow_name
    workflow_mapping_key = str(comfyui_target.get("workflow_mapping_key") or "").strip() or workflow_name
    style_family = str(comfyui_target.get("style_family") or "").strip() or fallback_style_family
    control_mode = str(route_entry.get("control_mode") or "prompt_only").strip() or "prompt_only"
    style_selector = style_preset.get("style_selector")
    resolved.update(
        {
            "route_key": route_key,
            "style_family": style_family,
            "comfyui_workflow_mapping_key": workflow_mapping_key,
            "comfyui_workflow_name": workflow_name,
            "comfyui_model_id": comfyui_target.get("model_id"),
            "comfyui_style_selector": style_selector,
            "prompt_only_workflow_mapping_key": workflow_mapping_key,
            "prompt_only_workflow_name": workflow_name,
            "prompt_only_comfyui_model_id": comfyui_target.get("model_id"),
            "prompt_only_preferred_comfyui_workflow_candidate": comfyui_target.get("preferred_workflow_candidate"),
            "prompt_only_preferred_comfyui_workflow_source_ref": comfyui_target.get("preferred_workflow_source_ref"),
            "preferred_comfyui_workflow_candidate": comfyui_target.get("preferred_workflow_candidate"),
            "preferred_comfyui_model_candidate": comfyui_target.get("preferred_model_candidate"),
            "route_migration_state": comfyui_target.get("migration_state"),
            "preferred_comfyui_workflow_source_ref": comfyui_target.get("preferred_workflow_source_ref"),
            "preferred_comfyui_workflow_format": comfyui_target.get("preferred_workflow_format"),
            "preferred_comfyui_workflow_custom_node_dependencies": comfyui_target.get("preferred_workflow_custom_node_dependencies"),
            "preferred_comfyui_workflow_import_blockers": comfyui_target.get("preferred_workflow_import_blockers"),
            "comfyui_style_preset_key": style_preset.get("preset_key"),
            "comfyui_style_preset_label": style_preset.get("preset_label"),
            "comfyui_style_positive_anchor": style_preset.get("positive_anchor"),
            "comfyui_style_negative_anchor": style_preset.get("negative_anchor"),
            "comfyui_control_mode": control_mode,
            "registry_path": str(registry_path).replace("\\", "/"),
            "used_registry": True,
            "resolution_mode": "stage00_style_registry",
            "workflow_mapping_resolution": "route_registry_current_mapping",
            "reference_guided_route_selected": False,
        }
    )
    return resolved


def provider_strategy_from_brief(brief: dict) -> dict:
    compiled = compile_requirements(brief)
    configured_priority = list((compiled.get("provider_preferences") or {}).get("stage05_provider_priority") or [])
    image_generation = brief.get("image_generation") if isinstance(brief.get("image_generation"), dict) else {}
    primary = image_generation.get("primary") or (configured_priority[0] if configured_priority else "comfyui_txt2img")
    fallback = image_generation.get("fallback") or (configured_priority[1:] if len(configured_priority) > 1 else ["manual"])
    if isinstance(fallback, str):
        fallback = [fallback]
    return {
        "primary": primary,
        "fallback": fallback,
        "execution_mode": "provider_or_manual",
        "notes": "Use the local ComfyUI Zimage workflows for Stage 05; if generation cannot run, manually place generated images under 05_images/keyframes/."
    }


def resolve_stage05_optimization(workflow_mapping_key: str, requested_profile: str | None = None) -> dict:
    try:
        config, config_path = load_stage05_optimization_profiles(root=ROOT)
        resolved = resolve_stage05_workflow_optimization(
            config,
            workflow_mapping_key,
            requested_profile=requested_profile,
        )
    except Stage05OptimizationError as exc:
        raise SystemExit(f"ERROR: {exc}")
    resolved["config_path"] = str(config_path).replace("\\", "/")
    return resolved


def request_record(job: dict, provider: str) -> dict:
    return {
        "request_id": f"REQ_{provider.upper()}_{job['image_id']}",
        "image_id": job["image_id"],
        "shot_id": job["shot_id"],
        "frame_role": job["frame_role"],
        "provider": provider,
        "style_family": job.get("style_family"),
        "comfyui_workflow_mapping_key": job.get("comfyui_workflow_mapping_key"),
        "comfyui_workflow_name": job.get("comfyui_workflow_name"),
        "comfyui_model_id": job.get("comfyui_model_id"),
        "comfyui_style_selector": job.get("comfyui_style_selector"),
        "preferred_comfyui_workflow_candidate": job.get("preferred_comfyui_workflow_candidate"),
        "preferred_comfyui_model_candidate": job.get("preferred_comfyui_model_candidate"),
        "route_migration_state": job.get("route_migration_state"),
        "preferred_comfyui_workflow_source_ref": job.get("preferred_comfyui_workflow_source_ref"),
        "preferred_comfyui_workflow_format": job.get("preferred_comfyui_workflow_format"),
        "preferred_comfyui_workflow_custom_node_dependencies": job.get("preferred_comfyui_workflow_custom_node_dependencies"),
        "preferred_comfyui_workflow_import_blockers": job.get("preferred_comfyui_workflow_import_blockers"),
        "comfyui_style_preset_key": job.get("comfyui_style_preset_key"),
        "comfyui_style_preset_label": job.get("comfyui_style_preset_label"),
        "comfyui_declared_control_mode": job.get("comfyui_declared_control_mode"),
        "comfyui_control_mode": job.get("comfyui_control_mode"),
        "reference_guidance_requested": job.get("reference_guidance_requested"),
        "reference_guidance_ready": job.get("reference_guidance_ready"),
        "reference_guidance_active": job.get("reference_guidance_active"),
        "workflow_capability_gaps": job.get("workflow_capability_gaps"),
        "comfyui_optimization_profile": job.get("comfyui_optimization_profile"),
        "comfyui_optimization_profile_label": job.get("comfyui_optimization_profile_label"),
        "quality_gate": job.get("quality_gate"),
        "prompt": job["prompt"],
        "negative_prompt": job["negative_prompt"],
        "aspect_ratio": job["aspect_ratio"],
        "resolution": job["resolution"],
        "output_path": job["output_path"],
        "status": "planned"
    }


def main(argv: list[str]) -> int:
    requested_optimization_profile: str | None = None
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    filtered_argv = [argv[0]]
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg == "--allow-beyond-requested-scope":
            index += 1
            continue
        if arg == "--optimization-profile":
            if index + 1 >= len(argv):
                print("ERROR: --optimization-profile requires a value", file=sys.stderr)
                return 2
            requested_optimization_profile = str(argv[index + 1]).strip() or None
            index += 2
            continue
        if arg.startswith("--optimization-profile="):
            requested_optimization_profile = arg.split("=", 1)[1].strip() or None
            index += 1
            continue
        filtered_argv.append(arg)
        index += 1
    argv = filtered_argv
    if len(argv) != 4:
        print(
            "Usage: python new_keyframe_image_jobs.py <locked_brief.json> <keyframe_prompts.json> <keyframe_image_manifest.json> "
            "[--optimization-profile preview|balanced|quality]",
            file=sys.stderr,
        )
        return 2
    brief_path = Path(argv[1])
    prompts_path = Path(argv[2])
    out_path = Path(argv[3])
    brief = load_json(brief_path)
    prompts = load_json(prompts_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_05", compiled):
        print("ERROR: requested output scope does not allow Stage 05. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if prompts.get("stage") != "STAGE_04_KEYFRAME_PROMPTS":
        print("ERROR: keyframe_prompts.stage must be STAGE_04_KEYFRAME_PROMPTS", file=sys.stderr)
        return 1
    if prompts.get("status") not in {"draft", "confirmed"}:
        print("ERROR: keyframe_prompts.status must be draft or confirmed", file=sys.stderr)
        return 1

    project_id = brief.get("project_id") or prompts.get("project_id") or out_path.parents[1].name
    aspect, resolution = parse_visual_spec(brief)
    route_resolution = resolve_stage05_route(brief, prompts)
    stage05_route_key = str(route_resolution["route_key"])
    style_family = str(route_resolution["style_family"])
    comfyui_workflow_mapping_key = str(route_resolution["comfyui_workflow_mapping_key"])
    comfyui_workflow_name = str(route_resolution["comfyui_workflow_name"])
    comfyui_model_id = route_resolution.get("comfyui_model_id")
    preferred_comfyui_workflow_candidate = route_resolution.get("preferred_comfyui_workflow_candidate")
    preferred_comfyui_model_candidate = route_resolution.get("preferred_comfyui_model_candidate")
    route_migration_state = route_resolution.get("route_migration_state")
    preferred_comfyui_workflow_source_ref = route_resolution.get("preferred_comfyui_workflow_source_ref")
    preferred_comfyui_workflow_format = route_resolution.get("preferred_comfyui_workflow_format")
    preferred_comfyui_workflow_custom_node_dependencies = route_resolution.get("preferred_comfyui_workflow_custom_node_dependencies")
    preferred_comfyui_workflow_import_blockers = route_resolution.get("preferred_comfyui_workflow_import_blockers")
    comfyui_style_preset_key = route_resolution.get("comfyui_style_preset_key")
    comfyui_style_preset_label = route_resolution.get("comfyui_style_preset_label")
    comfyui_style_positive_anchor = route_resolution.get("comfyui_style_positive_anchor")
    comfyui_style_negative_anchor = route_resolution.get("comfyui_style_negative_anchor")
    comfyui_style_selector = route_resolution.get("comfyui_style_selector")
    declared_comfyui_control_mode = str(route_resolution.get("comfyui_control_mode") or "prompt_only")
    route_entry: dict | None = None
    if route_resolution.get("used_registry") is True:
        try:
            registry, _ = load_stage05_route_registry(root=ROOT)
            route_entry = get_stage05_route_entry(registry, stage05_route_key)
        except RouteRegistryError:
            route_entry = None
    comfyui_optimization = resolve_stage05_optimization(
        comfyui_workflow_mapping_key,
        requested_profile=requested_optimization_profile,
    )
    reference_image_status = prompts.get("reference_image_status") if isinstance(prompts.get("reference_image_status"), dict) else {}
    stage05_execution_readiness = prompts.get("stage05_execution_readiness") if isinstance(prompts.get("stage05_execution_readiness"), dict) else {}
    reference_guidance_requested = bool(
        stage05_execution_readiness.get("reference_image_required")
        or compiled.get("continuity_mode") == "character_locked"
    )
    reference_guidance_ready = bool(reference_guidance_requested and reference_image_status.get("all_present"))
    workflow_mapping_path: str | None = None
    workflow_mapping_capabilities = {
        "supports_reference_images": False,
        "supported_control_modes": ["prompt_only"],
    }
    try:
        mapping_data, mapping_path = load_workflow_mapping(root=ROOT)
        workflow_mapping_path = str(mapping_path).replace("\\", "/")
        workflow_mapping_capabilities = resolve_workflow_capabilities(
            get_workflow_mapping(mapping_data, comfyui_workflow_mapping_key)
        )
    except Exception:
        workflow_mapping_capabilities = {
            "supports_reference_images": False,
            "supported_control_modes": ["prompt_only"],
        }
    reference_guidance_active = bool(
        reference_guidance_ready
        and workflow_mapping_capabilities.get("supports_reference_images") is True
        and "reference_guided" in (workflow_mapping_capabilities.get("supported_control_modes") or [])
    )
    workflow_capability_gaps: list[str] = []
    if reference_guidance_requested and not reference_guidance_ready:
        workflow_capability_gaps.append("reference_images_missing")
    if reference_guidance_requested and workflow_mapping_capabilities.get("supports_reference_images") is not True:
        workflow_capability_gaps.append("selected_workflow_does_not_accept_reference_images")
    comfyui_control_mode = "reference_guided" if reference_guidance_active else declared_comfyui_control_mode
    quality_contract = build_quality_contract(brief, compiled)
    quality_targets = build_stage_quality_targets("STAGE_05", quality_contract)
    provider_priority = list((compiled.get("provider_preferences") or {}).get("stage05_provider_priority") or ["comfyui_txt2img", "manual"])
    keyframes_dir = out_path.parent / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    project_root = out_path.parent.parent
    prompts_ref = str(prompts_path).replace("\\", "/")
    routing = routing_from_brief(brief)
    storyboard_by_shot = storyboard_lookup_from_prompts(prompts, prompts_path)
    global_subject = str((prompts.get("story_anchors") or {}).get("subject") or "").strip()

    jobs = []
    shot_frame_requirements: dict[str, list[str]] = {}
    for idx, shot in enumerate(prompts.get("shot_prompts") or []):
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id") or f"S{idx+1:03d}"
        storyboard_shot = storyboard_by_shot.get(str(shot_id), {})
        frame_plan = classify_stage05_frame_plan(shot, storyboard_shot)
        shot_frame_requirements[str(shot_id)] = list(frame_plan["required_roles"])
        frame_specs: list[tuple[str, str | None]] = [("start", "start_keyframe_prompt")]
        if frame_plan["requires_mid"]:
            frame_specs.append(("mid", None))
        frame_specs.append(("end", "end_keyframe_prompt"))
        identity_anchor_prompt = build_identity_anchor_fallback(
            shot,
            storyboard_shot,
            global_subject=global_subject,
        )
        base_consistency_prompt = str(shot.get("consistency_prompt") or "").strip()
        if identity_anchor_prompt and identity_anchor_prompt not in base_consistency_prompt:
            effective_consistency_prompt = "; ".join(part for part in [base_consistency_prompt, identity_anchor_prompt] if part)
        else:
            effective_consistency_prompt = base_consistency_prompt
        for frame_role, prompt_key in frame_specs:
            image_id = f"IMG_{shot_id}_{frame_role.upper()}"
            output_path = keyframes_dir / f"{shot_id}_{frame_role}.png"
            dependencies = shot.get("dependencies") if isinstance(shot.get("dependencies"), dict) else {}
            reference_images = [
                str(item).replace("\\", "/")
                for item in (dependencies.get("reference_images") or [])
                if isinstance(item, str) and str(item).strip()
            ]
            route_hint = str(frame_plan["generation_profile"].get("route_hint") or "").strip()
            secondary_reference_images: list[str] = []
            if route_hint == INTERACTION_HANDOFF_ROUTE_HINT:
                secondary_reference_images = interaction_handoff_secondary_reference_images(
                    project_root=project_root,
                    keyframes_dir=keyframes_dir,
                    shot_id=str(shot_id),
                    frame_role=frame_role,
                )
            effective_reference_images = list(reference_images)
            for candidate in secondary_reference_images:
                if candidate not in effective_reference_images:
                    effective_reference_images.append(candidate)
            missing_reference_images = [
                str(item).replace("\\", "/")
                for item in effective_reference_images
                if not (resolve_related_asset(prompts_path, item) and resolve_related_asset(prompts_path, item).exists())
            ]
            prompt_text = (
                build_mid_keyframe_prompt(
                    shot,
                    storyboard_shot,
                    frame_plan["bundle"],
                    global_subject=global_subject,
                    aspect_ratio=aspect,
                )
                if frame_role == "mid"
                else (shot.get(prompt_key) or "")
            )
            prompt_text = str(prompt_text or "").strip()
            negative_prompt = str(shot.get("negative_prompt") or prompts.get("global_negative_prompt") or "").strip()
            selected_workflow_mapping_key = comfyui_workflow_mapping_key
            selected_workflow_name = comfyui_workflow_name
            selected_model_id = comfyui_model_id
            selected_preferred_workflow_candidate = preferred_comfyui_workflow_candidate
            selected_preferred_workflow_source_ref = preferred_comfyui_workflow_source_ref
            selected_control_mode = comfyui_control_mode
            selected_reference_guidance_active = reference_guidance_active
            selected_workflow_capability_gaps = list(workflow_capability_gaps)
            selected_style_preset_key = comfyui_style_preset_key
            selected_style_preset_label = comfyui_style_preset_label
            selected_style_positive_anchor = comfyui_style_positive_anchor
            selected_style_negative_anchor = comfyui_style_negative_anchor
            selected_style_selector = comfyui_style_selector
            style_preset_override_key = route_style_preset_override_key(
                route_key=stage05_route_key,
                shot_prompt=shot,
                storyboard_shot=storyboard_shot,
            )
            if route_entry and style_preset_override_key:
                override_preset = resolve_named_style_preset(route_entry, style_preset_override_key)
                if (
                    override_preset.get("positive_anchor")
                    or override_preset.get("negative_anchor")
                    or override_preset.get("style_selector")
                ):
                    selected_style_preset_key = override_preset.get("preset_key")
                    selected_style_preset_label = override_preset.get("preset_label")
                    selected_style_positive_anchor = override_preset.get("positive_anchor")
                    selected_style_negative_anchor = override_preset.get("negative_anchor")
                    selected_style_selector = override_preset.get("style_selector") or selected_style_selector
            prompt_composition_mode = "legacy_stage04_full_prompt"
            if _is_original_zimage_ui_workflow(selected_preferred_workflow_source_ref):
                prompt_text = sanitize_stage04_prompt_for_zimage(
                    prompt_text,
                    shot_prompt=shot,
                    aspect_ratio=aspect,
                )
                prompt_composition_mode = "zimage_skill_aligned"
            reference_bundle_mode = "primary_only"
            if route_hint == INTERACTION_HANDOFF_ROUTE_HINT:
                prompt_text = ", ".join(
                    part
                    for part in [
                        prompt_text,
                        interaction_handoff_prompt_suffix(key_prop=frame_plan["bundle"].get("key_prop") or ""),
                    ]
                    if str(part).strip()
                )
                negative_prompt = ", ".join(
                    part
                    for part in [
                        negative_prompt,
                        interaction_handoff_negative_suffix(key_prop=frame_plan["bundle"].get("key_prop") or ""),
                    ]
                    if str(part).strip()
                )
                if secondary_reference_images:
                    reference_bundle_mode = "primary_plus_context_frame"
            job = {
                "image_id": image_id,
                "shot_id": shot_id,
                "frame_role": frame_role,
                "source_prompt_ref": f"{prompts_ref}#{shot_id}.{frame_role}",
                "prompt": prompt_text,
                "negative_prompt": negative_prompt,
                "consistency_prompt": effective_consistency_prompt,
                "identity_anchor_prompt": identity_anchor_prompt,
                "style_prompt": shot.get("style_prompt") or "",
                "lighting_prompt": shot.get("lighting_prompt") or "",
                "camera_prompt": shot.get("camera_prompt") or "",
                "reference_images": effective_reference_images,
                "secondary_reference_images": secondary_reference_images,
                "reference_bundle_mode": reference_bundle_mode,
                "missing_reference_images": missing_reference_images,
                "stage06_route_hint": route_hint,
                "stage06_requires_mid_guide": frame_plan["requires_mid"],
                "stage05_route_key": stage05_route_key,
                "style_family": style_family,
                "comfyui_workflow_mapping_key": selected_workflow_mapping_key,
                "comfyui_workflow_name": selected_workflow_name,
                "comfyui_model_id": selected_model_id,
                "preferred_comfyui_workflow_candidate": selected_preferred_workflow_candidate,
                "preferred_comfyui_model_candidate": preferred_comfyui_model_candidate,
                "route_migration_state": route_migration_state,
                "preferred_comfyui_workflow_source_ref": selected_preferred_workflow_source_ref,
                "preferred_comfyui_workflow_format": preferred_comfyui_workflow_format,
                "preferred_comfyui_workflow_custom_node_dependencies": preferred_comfyui_workflow_custom_node_dependencies,
                "preferred_comfyui_workflow_import_blockers": preferred_comfyui_workflow_import_blockers,
                "comfyui_style_preset_key": selected_style_preset_key,
                "comfyui_style_preset_label": selected_style_preset_label,
                "comfyui_style_positive_anchor": selected_style_positive_anchor,
                "comfyui_style_negative_anchor": selected_style_negative_anchor,
                "comfyui_style_selector": selected_style_selector,
                "comfyui_declared_control_mode": declared_comfyui_control_mode,
                "comfyui_control_mode": selected_control_mode,
                "reference_guidance_requested": reference_guidance_requested,
                "reference_guidance_ready": reference_guidance_ready,
                "reference_guidance_active": selected_reference_guidance_active,
                "workflow_capability_gaps": selected_workflow_capability_gaps,
                "comfyui_optimization_profile": comfyui_optimization["profile_key"],
                "comfyui_optimization_profile_label": comfyui_optimization["profile_label"],
                "aspect_ratio": aspect,
                "resolution": resolution,
                "provider_priority": provider_priority,
                "provider": None,
                "status": "pending",
                "seed": None,
                "output_path": str(output_path).replace("\\", "/"),
                "prompt_composition_mode": prompt_composition_mode,
                "evidence": {
                    "file_path": str(output_path).replace("\\", "/"),
                    "file_exists": output_path.exists(),
                    "file_size_bytes": output_path.stat().st_size if output_path.exists() else 0,
                    "created_at": None
                },
                "errors": [],
                "notes": "",
            }
            job["quality_gate"] = build_quality_gate(job)
            if job["quality_gate"]["requires_manual_review"]:
                job["notes"] = (
                    "Manual review required before Stage 06: "
                    + str(job["quality_gate"].get("reason") or "high-risk composition")
                )
            elif frame_role == "mid":
                job["notes"] = "Auto-scaffolded mid keyframe for high-risk Stage 06 interaction coverage."
            jobs.append(job)

    quality_review = summarize_quality_review(jobs)
    top_level_style_preset_key = comfyui_style_preset_key
    top_level_style_preset_label = comfyui_style_preset_label
    top_level_style_positive_anchor = comfyui_style_positive_anchor
    top_level_style_negative_anchor = comfyui_style_negative_anchor
    top_level_style_selector = comfyui_style_selector
    if jobs:
        first_job = jobs[0]
        if all(job.get("comfyui_style_preset_key") == first_job.get("comfyui_style_preset_key") for job in jobs):
            top_level_style_preset_key = first_job.get("comfyui_style_preset_key")
            top_level_style_preset_label = first_job.get("comfyui_style_preset_label")
            top_level_style_positive_anchor = first_job.get("comfyui_style_positive_anchor")
            top_level_style_negative_anchor = first_job.get("comfyui_style_negative_anchor")
            top_level_style_selector = first_job.get("comfyui_style_selector")
        else:
            top_level_style_preset_key = None
            top_level_style_preset_label = None
            top_level_style_positive_anchor = None
            top_level_style_negative_anchor = None
            top_level_style_selector = None

    self_check_notes: list[str] = []
    if any("mid" in roles for roles in shot_frame_requirements.values()):
        self_check_notes.append("Mid keyframes were scaffolded for high-risk Stage 06 interaction shots.")
    if not quality_review["manual_review_cleared"]:
        self_check_notes.append("Manual review is required for risky prop-contact scenes before Stage 06.")
    if isinstance(stage05_execution_readiness.get("missing_reference_images"), list) and stage05_execution_readiness.get("missing_reference_images"):
        self_check_notes.append(
            "Stage 05 automatic generation is not safe yet because character reference images are still missing: "
            + ", ".join(str(path_text) for path_text in stage05_execution_readiness["missing_reference_images"])
        )
    if "selected_workflow_does_not_accept_reference_images" in workflow_capability_gaps:
        self_check_notes.append(
            "Current Stage 05 ComfyUI workflow is still prompt-only. Even after reference images are supplied, reference-guided continuity will stay inactive until a reference-capable workflow is mapped."
        )

    manifest = {
        "schema_version": "0.6.0",
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_keyframe_prompts": str(prompts_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "image_provider_strategy": provider_strategy_from_brief(brief),
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing,
        "output_root": str(out_path.parent).replace("\\", "/"),
        "keyframes_dir": str(keyframes_dir).replace("\\", "/"),
        "reference_image_status": reference_image_status,
        "stage05_execution_readiness": stage05_execution_readiness,
        "workflow_mapping_path": workflow_mapping_path,
        "comfyui_workflow_capabilities": workflow_mapping_capabilities,
        "reference_guidance_requested": reference_guidance_requested,
        "reference_guidance_ready": reference_guidance_ready,
        "reference_guidance_active": reference_guidance_active,
        "workflow_capability_gaps": workflow_capability_gaps,
        "stage05_route_key": stage05_route_key,
        "style_family": style_family,
        "comfyui_workflow_mapping_key": comfyui_workflow_mapping_key,
        "comfyui_workflow_router": STYLE_FAMILY_TO_WORKFLOW,
        "route_resolution": route_resolution,
        "shot_frame_requirements": shot_frame_requirements,
        "comfyui_workflow_name": comfyui_workflow_name,
        "comfyui_model_id": comfyui_model_id,
        "preferred_comfyui_workflow_candidate": preferred_comfyui_workflow_candidate,
        "preferred_comfyui_model_candidate": preferred_comfyui_model_candidate,
        "route_migration_state": route_migration_state,
        "preferred_comfyui_workflow_source_ref": preferred_comfyui_workflow_source_ref,
        "preferred_comfyui_workflow_format": preferred_comfyui_workflow_format,
        "preferred_comfyui_workflow_custom_node_dependencies": preferred_comfyui_workflow_custom_node_dependencies,
        "preferred_comfyui_workflow_import_blockers": preferred_comfyui_workflow_import_blockers,
        "comfyui_style_preset_key": top_level_style_preset_key,
        "comfyui_style_preset_label": top_level_style_preset_label,
        "comfyui_style_positive_anchor": top_level_style_positive_anchor,
        "comfyui_style_negative_anchor": top_level_style_negative_anchor,
        "comfyui_style_selector": top_level_style_selector,
        "comfyui_declared_control_mode": declared_comfyui_control_mode,
        "comfyui_control_mode": comfyui_control_mode,
        "comfyui_optimization_profile": comfyui_optimization["profile_key"],
        "comfyui_optimization_profile_label": comfyui_optimization["profile_label"],
        "comfyui_optimization": comfyui_optimization,
        "jobs": jobs,
        "summary": {
            "shot_count": len({j["shot_id"] for j in jobs}),
            "expected_image_count": len(jobs),
            "generated_image_count": sum(1 for j in jobs if j["evidence"]["file_exists"]),
            "failed_image_count": 0,
            "required_mid_image_count": sum(1 for roles in shot_frame_requirements.values() if "mid" in roles),
        },
        "quality_signals": {
            "intent_route_matches_strategy": routing.get("legacy_mode") or requested_output_allows_stage("STAGE_05", compiled),
            "style_route_matches_strategy": style_family == compiled.get("visual_family_hint"),
            "consistency_prompts_present": all(bool(j.get("consistency_prompt")) for j in jobs),
            "quality_targets_defined": bool(quality_targets),
        },
        "quality_review": quality_review,
        "self_check": {
            "covers_all_keyframe_prompts": len(jobs) == sum(len(roles) for roles in shot_frame_requirements.values()),
            "has_start_and_end_for_each_shot": True,
            "all_required_images_exist": False,
            "manual_review_cleared": quality_review["manual_review_cleared"],
            "ready_for_video_clip_generation": False,
            "notes": self_check_notes,
        },
        "allowed_next_stage": None
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "image_generation_jobs.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "comfyui_image_requests.json").write_text(json.dumps({"provider": "comfyui_txt2img", "requests": [request_record(j, "comfyui_txt2img") for j in jobs]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "image_generation_plan.md").write_text(
        "# Stage 05 Keyframe Image Generation Plan\n\n"
        f"Project: `{project_id}`\n\n"
        f"Stage 05 route key: `{stage05_route_key}`\n\n"
        f"Style family: `{style_family}`\n\n"
        f"ComfyUI workflow mapping key: `{comfyui_workflow_mapping_key}`\n\n"
        f"ComfyUI workflow route: `{comfyui_workflow_name}`\n\n"
        f"ComfyUI model candidate: `{comfyui_model_id or 'unassigned'}`\n\n"
        f"ComfyUI style selector: `{comfyui_style_selector or 'none'}`\n\n"
        f"ComfyUI declared control mode: `{declared_comfyui_control_mode}`\n\n"
        f"ComfyUI effective control mode: `{comfyui_control_mode}`\n\n"
        f"Workflow supports reference images: `{workflow_mapping_capabilities['supports_reference_images']}`\n\n"
        f"Reference guidance requested: `{reference_guidance_requested}`\n\n"
        f"Reference guidance ready: `{reference_guidance_ready}`\n\n"
        f"Reference guidance active: `{reference_guidance_active}`\n\n"
        f"ComfyUI optimization profile: `{comfyui_optimization['profile_key']}` ({comfyui_optimization['profile_label']})\n\n"
        f"Expected images: {len(jobs)}\n\n"
        "Provider order: OpenAI image → ComfyUI txt2img → manual placement.\n\n"
        "Do not mark Stage 05 complete until `keyframe_image_manifest.json` passes final validation.\n",
        encoding="utf-8"
    )
    write_stage05_manual_review_files(manifest, out_path)
    write_stage05_prompt_patch_files(manifest, out_path)
    print(f"KEYFRAME IMAGE JOBS CREATED: {out_path}")
    print(f"EXPECTED_IMAGES: {len(jobs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
