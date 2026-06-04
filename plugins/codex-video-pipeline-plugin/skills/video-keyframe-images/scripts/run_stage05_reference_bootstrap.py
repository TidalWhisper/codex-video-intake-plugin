#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "providers"))

from pipeline_core.reference_image_readiness import (  # noqa: E402
    build_reference_image_status,
    build_stage05_execution_readiness,
)
from stage05_image_utils import load_json, write_json  # noqa: E402

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import new_keyframe_image_jobs  # noqa: E402
import run_comfyui_txt2img  # noqa: E402
import sync_keyframe_image_manifest  # noqa: E402


def _normalize_path_text(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/")


def _project_dir_for_manifest(manifest_path: Path) -> Path:
    return manifest_path.parents[1]


def _character_bible_path_for_manifest(manifest_path: Path) -> Path:
    return _project_dir_for_manifest(manifest_path) / "03_characters" / "character_bible.json"


def _keyframe_prompts_path_for_manifest(manifest: dict[str, Any], manifest_path: Path) -> Path:
    raw = _normalize_path_text(manifest.get("source_keyframe_prompts"))
    if raw:
        return Path(raw).resolve()
    return _project_dir_for_manifest(manifest_path) / "04_keyframes" / "keyframe_prompts.json"


def _dominant_provider(manifest: dict[str, Any]) -> str | None:
    counts: dict[str, int] = {}
    for job in manifest.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        if str(job.get("status") or "").strip() != "succeeded":
            continue
        provider = str(job.get("provider") or "").strip()
        if not provider:
            continue
        counts[provider] = counts.get(provider, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _resolve_reference_plan_item(character_bible: dict[str, Any], target_reference_path: str) -> dict[str, Any]:
    plan = character_bible.get("reference_image_plan") if isinstance(character_bible.get("reference_image_plan"), dict) else {}
    items = [item for item in (plan.get("reference_images") or []) if isinstance(item, dict)]
    normalized_target = _normalize_path_text(target_reference_path)
    for item in items:
        if _normalize_path_text(item.get("target_path")) == normalized_target:
            return item
    if items:
        return items[0]
    raise SystemExit("ERROR: character_bible.reference_image_plan.reference_images is empty; cannot bootstrap Stage05-A")


def _resolve_character_entry(character_bible: dict[str, Any], character_id: str | None) -> dict[str, Any]:
    characters = [item for item in (character_bible.get("characters") or []) if isinstance(item, dict)]
    normalized_character_id = _normalize_path_text(character_id)
    if normalized_character_id:
        for item in characters:
            if _normalize_path_text(item.get("character_id")) == normalized_character_id:
                return item
    if characters:
        return characters[0]
    raise SystemExit("ERROR: character_bible.characters is empty; cannot bootstrap Stage05-A")


def _bootstrap_prompt(
    reference_plan_item: dict[str, Any],
    character_entry: dict[str, Any],
    stage05_manifest: dict[str, Any],
) -> tuple[str, str, str, str]:
    story_anchors = character_entry.get("story_anchors") if isinstance(character_entry.get("story_anchors"), dict) else {}
    manifest_story_anchors = stage05_manifest.get("story_anchors") if isinstance(stage05_manifest.get("story_anchors"), dict) else {}
    character_name = str(reference_plan_item.get("name") or character_entry.get("name") or "主角").strip() or "主角"
    visual_consistency = str(
        reference_plan_item.get("visual_consistency_prompt")
        or character_entry.get("visual_consistency_prompt")
        or ""
    ).strip()
    negative_consistency = str(
        reference_plan_item.get("negative_consistency_prompt")
        or character_entry.get("negative_consistency_prompt")
        or ""
    ).strip()
    scene_label = str(
        story_anchors.get("scene_label")
        or manifest_story_anchors.get("scene_label")
        or manifest_story_anchors.get("location")
        or stage05_manifest.get("stage05_route_key")
        or ""
    ).strip()
    appearance = character_entry.get("appearance") if isinstance(character_entry.get("appearance"), dict) else {}
    hair = str(appearance.get("hair") or "").strip()
    clothing = str(appearance.get("clothing") or "").strip()
    face = str(appearance.get("face") or "").strip()

    prompt = (
        f"为后续跨场景分镜建立主角色参考图，{character_name} 单人入镜。"
        f"镜头采用正面偏左三分之四视角，膝上到全身之间的中景，人物占画面约六成，站姿自然稳定，不走动，不做夸张表情。"
        f"{face}。{hair}。{clothing}。"
        f"{visual_consistency}"
        "背景保持简洁、不抢戏、不要强叙事干扰，重点是把脸、发型、服装版型、领口、腰线和整体轮廓拍清楚，便于后续所有镜头保持同一人物。"
    )
    if scene_label:
        prompt += f"整体风格延续项目的{scene_label}气质，但这张图以角色识别清楚为第一优先。"

    lighting = "clean soft light, readable face, stable hair detail, clear dress silhouette"
    camera = "front left three-quarter medium full-body reference shot"
    style = "single-character reference image, stable identity anchor, clean readable design"
    return prompt, negative_consistency, lighting, f"{camera}; {style}"


def _reference_bootstrap_manifest_path(manifest_path: Path, target_reference_path: str) -> Path:
    stem = Path(target_reference_path).stem or "primary"
    return manifest_path.parents[1] / "03_characters" / "reference_images" / "_candidates" / f"{stem}_stage05a_manifest.json"


def _reference_bootstrap_output_path(manifest_path: Path, target_reference_path: str) -> Path:
    stem = Path(target_reference_path).stem or "primary"
    return manifest_path.parents[1] / "03_characters" / "reference_images" / "_candidates" / f"{stem}_stage05a.png"


def _build_reference_bootstrap_manifest(
    stage05_manifest: dict[str, Any],
    manifest_path: Path,
    *,
    target_reference_path: str,
    reference_bootstrap: dict[str, Any],
    prompt: str,
    negative_prompt: str,
    lighting_prompt: str,
    camera_and_style_prompt: str,
) -> tuple[dict[str, Any], Path]:
    output_path = _reference_bootstrap_output_path(manifest_path, target_reference_path)
    bootstrap_manifest_path = _reference_bootstrap_manifest_path(manifest_path, target_reference_path)
    workflow_mapping_key = str(reference_bootstrap.get("workflow_mapping_key") or "").strip()
    workflow_name = str(reference_bootstrap.get("workflow_name") or workflow_mapping_key).strip() or workflow_mapping_key
    job = {
        "image_id": "IMG_STAGE05A_PRIMARY_REFERENCE",
        "shot_id": "STAGE05A",
        "frame_role": "reference",
        "stage05_mode": "reference_bootstrap",
        "source_prompt_ref": f"{bootstrap_manifest_path.name}#IMG_STAGE05A_PRIMARY_REFERENCE",
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "consistency_prompt": prompt,
        "identity_anchor_prompt": prompt,
        "style_prompt": camera_and_style_prompt,
        "lighting_prompt": lighting_prompt,
        "camera_prompt": "front three-quarter reference shot",
        "reference_images": [],
        "secondary_reference_images": [],
        "reference_bundle_mode": "none",
        "primary_reference_image_path": target_reference_path,
        "missing_reference_images": [],
        "stage06_route_hint": "single_subject_motion",
        "stage06_requires_mid_guide": False,
        "stage05_route_key": str(stage05_manifest.get("stage05_route_key") or "").strip(),
        "style_family": str(stage05_manifest.get("style_family") or "").strip(),
        "comfyui_workflow_mapping_key": workflow_mapping_key,
        "comfyui_workflow_name": workflow_name,
        "comfyui_model_id": reference_bootstrap.get("comfyui_model_id"),
        "preferred_comfyui_workflow_candidate": reference_bootstrap.get("preferred_workflow_candidate") or workflow_name,
        "preferred_comfyui_model_candidate": reference_bootstrap.get("comfyui_model_id"),
        "route_migration_state": "stage05a_reference_bootstrap",
        "preferred_comfyui_workflow_source_ref": reference_bootstrap.get("preferred_workflow_source_ref"),
        "preferred_comfyui_workflow_format": reference_bootstrap.get("preferred_workflow_format") or "ui_graph",
        "preferred_comfyui_workflow_custom_node_dependencies": ["rgthree-comfy"],
        "preferred_comfyui_workflow_import_blockers": [],
        "comfyui_style_preset_key": reference_bootstrap.get("style_preset_key"),
        "comfyui_style_preset_label": reference_bootstrap.get("style_preset_label"),
        "comfyui_style_positive_anchor": reference_bootstrap.get("style_positive_anchor"),
        "comfyui_style_negative_anchor": reference_bootstrap.get("style_negative_anchor"),
        "comfyui_style_selector": reference_bootstrap.get("style_selector"),
        "comfyui_declared_control_mode": "prompt_only",
        "comfyui_control_mode": "prompt_only",
        "reference_guidance_requested": False,
        "reference_guidance_ready": False,
        "reference_guidance_active": False,
        "workflow_capability_gaps": [],
        "comfyui_optimization_profile": stage05_manifest.get("comfyui_optimization_profile") or "balanced",
        "comfyui_optimization_profile_label": stage05_manifest.get("comfyui_optimization_profile_label") or "Balanced",
        "aspect_ratio": str(stage05_manifest.get("jobs", [{}])[0].get("aspect_ratio") if stage05_manifest.get("jobs") else "16:9"),
        "resolution": str(stage05_manifest.get("jobs", [{}])[0].get("resolution") if stage05_manifest.get("jobs") else "1080P"),
        "provider_priority": ["comfyui_txt2img", "manual"],
        "provider": None,
        "status": "pending",
        "seed": 105003,
        "output_path": str(output_path).replace("\\", "/"),
        "prompt_composition_mode": "stage05a_reference_bootstrap",
        "quality_gate": {
            "risk_tags": [],
            "control_mode": "prompt_only",
            "requires_manual_review": False,
            "manual_review_status": "not_required",
            "reason": None,
        },
        "evidence": {
            "file_path": str(output_path).replace("\\", "/"),
            "file_exists": False,
            "file_size_bytes": 0,
            "created_at": None,
        },
        "errors": [],
        "notes": "Stage05-A primary reference bootstrap job",
    }
    bootstrap_manifest = {
        "schema_version": "0.6.0",
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "draft",
        "project_id": stage05_manifest.get("project_id"),
        "source_brief": stage05_manifest.get("source_brief"),
        "source_keyframe_prompts": stage05_manifest.get("source_keyframe_prompts"),
        "output_root": str(output_path.parent).replace("\\", "/"),
        "keyframes_dir": str(output_path.parent).replace("\\", "/"),
        "stage05_mode": "reference_bootstrap",
        "primary_reference_image_path": target_reference_path,
        "reference_bootstrap": reference_bootstrap,
        "stage05_route_key": job["stage05_route_key"],
        "style_family": job["style_family"],
        "comfyui_workflow_mapping_key": workflow_mapping_key,
        "comfyui_workflow_name": workflow_name,
        "comfyui_model_id": job["comfyui_model_id"],
        "preferred_comfyui_workflow_candidate": job["preferred_comfyui_workflow_candidate"],
        "preferred_comfyui_model_candidate": job["preferred_comfyui_model_candidate"],
        "route_migration_state": job["route_migration_state"],
        "preferred_comfyui_workflow_source_ref": job["preferred_comfyui_workflow_source_ref"],
        "preferred_comfyui_workflow_format": job["preferred_comfyui_workflow_format"],
        "preferred_comfyui_workflow_custom_node_dependencies": job["preferred_comfyui_workflow_custom_node_dependencies"],
        "preferred_comfyui_workflow_import_blockers": [],
        "comfyui_style_preset_key": job["comfyui_style_preset_key"],
        "comfyui_style_preset_label": job["comfyui_style_preset_label"],
        "comfyui_style_positive_anchor": job["comfyui_style_positive_anchor"],
        "comfyui_style_negative_anchor": job["comfyui_style_negative_anchor"],
        "comfyui_style_selector": job["comfyui_style_selector"],
        "comfyui_declared_control_mode": "prompt_only",
        "comfyui_control_mode": "prompt_only",
        "comfyui_optimization_profile": job["comfyui_optimization_profile"],
        "comfyui_optimization_profile_label": job["comfyui_optimization_profile_label"],
        "routing": stage05_manifest.get("routing") or {},
        "compiled_requirements": stage05_manifest.get("compiled_requirements") or {},
        "jobs": [job],
        "summary": {
            "shot_count": 1,
            "expected_image_count": 1,
            "generated_image_count": 0,
            "failed_image_count": 0,
        },
        "quality_review": {
            "risky_image_count": 0,
            "risky_image_ids": [],
            "required_count": 0,
            "approved_count": 0,
            "pending_count": 0,
            "waived_count": 0,
            "blocking_image_ids": [],
            "manual_review_cleared": True,
        },
        "self_check": {
            "covers_all_keyframe_prompts": True,
            "has_start_and_end_for_each_shot": True,
            "all_required_images_exist": False,
            "manual_review_cleared": True,
            "ready_for_video_clip_generation": False,
            "notes": ["Stage05-A bootstrap must finish before Stage05-B can consume the primary character reference image."],
        },
        "allowed_next_stage": None,
    }
    return bootstrap_manifest, bootstrap_manifest_path


def _copy_reference_image(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target_path)


def _refresh_character_bible(character_bible_path: Path) -> dict[str, Any]:
    data = load_json(character_bible_path)
    reference_plan = data.get("reference_image_plan") if isinstance(data.get("reference_image_plan"), dict) else {"required": True, "reference_images": []}
    reference_status = build_reference_image_status(character_bible_path.parent, reference_plan)
    stage05_execution_readiness = build_stage05_execution_readiness(
        continuity_mode=str((data.get("compiled_requirements") or {}).get("continuity_mode") or "character_locked"),
        reference_image_required=bool(data.get("reference_image_required")),
        reference_image_status=reference_status,
    )
    data["reference_image_status"] = reference_status
    data["stage05_execution_readiness"] = stage05_execution_readiness
    self_check = data.get("self_check") if isinstance(data.get("self_check"), dict) else {}
    self_check["reference_images_planned"] = bool((reference_plan.get("reference_images") or []))
    self_check["reference_images_ready"] = bool(reference_status.get("all_present"))
    self_check["safe_for_character_locked_image_generation"] = bool(stage05_execution_readiness.get("safe_to_auto_generate"))
    notes = [str(item) for item in (self_check.get("notes") or []) if isinstance(item, str)]
    notes = [item for item in notes if "Reference images still missing for character-locked continuity" not in item]
    if reference_status.get("missing_paths"):
        notes.append(
            "Reference images still missing for character-locked continuity: "
            + ", ".join(str(item) for item in reference_status["missing_paths"])
        )
    else:
        notes.append("Reference images are ready for character-locked continuity.")
    self_check["notes"] = notes
    data["self_check"] = self_check
    write_json(character_bible_path, data)
    return data


def _refresh_keyframe_prompts(
    prompts_path: Path,
    *,
    reference_status: dict[str, Any],
    stage05_execution_readiness: dict[str, Any],
) -> dict[str, Any]:
    data = load_json(prompts_path)
    data["reference_image_status"] = reference_status
    data["stage05_execution_readiness"] = stage05_execution_readiness
    self_check = data.get("self_check") if isinstance(data.get("self_check"), dict) else {}
    self_check["character_reference_images_ready"] = bool(reference_status.get("all_present"))
    self_check["safe_for_auto_image_generation"] = bool(stage05_execution_readiness.get("safe_to_auto_generate"))
    data["self_check"] = self_check
    write_json(prompts_path, data)
    return data


def _rebuild_stage05_manifest(
    manifest_path: Path,
    *,
    optimization_profile: str | None,
    allow_beyond_requested_scope: bool,
    provider_hint: str | None,
) -> dict[str, Any]:
    current = load_json(manifest_path)
    brief_path = _normalize_path_text(current.get("source_brief"))
    prompts_path = _normalize_path_text(current.get("source_keyframe_prompts"))
    if not brief_path or not prompts_path:
        raise SystemExit("ERROR: Stage 05 manifest is missing source_brief or source_keyframe_prompts")
    argv = [
        "new_keyframe_image_jobs.py",
        brief_path,
        prompts_path,
        str(manifest_path),
    ]
    if optimization_profile:
        argv.extend(["--optimization-profile", optimization_profile])
    if allow_beyond_requested_scope:
        argv.append("--allow-beyond-requested-scope")
    exit_code = new_keyframe_image_jobs.main(argv)
    if exit_code != 0:
        raise SystemExit(exit_code)
    sync_argv = [str(manifest_path)]
    if provider_hint:
        sync_argv.extend(["--provider", provider_hint])
    sync_exit = sync_keyframe_image_manifest.main(sync_argv)
    if sync_exit != 0:
        raise SystemExit(sync_exit)
    return load_json(manifest_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--target-reference", default=None, help="Optional Stage03 reference image target path override")
    parser.add_argument("--skip-refresh-stage05", action="store_true", help="Only backfill Stage03 and refresh Stage03/04, without rebuilding Stage05-B manifest")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Pass through when the project brief stops before Stage05")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json).resolve()
    stage05_manifest = load_json(manifest_path)
    reference_bootstrap = (
        stage05_manifest.get("reference_bootstrap")
        if isinstance(stage05_manifest.get("reference_bootstrap"), dict)
        else {}
    )
    target_reference_path = (
        _normalize_path_text(args.target_reference)
        or _normalize_path_text(reference_bootstrap.get("target_reference_image_path"))
        or _normalize_path_text(stage05_manifest.get("primary_reference_image_path"))
    )
    if not target_reference_path:
        raise SystemExit("ERROR: could not resolve Stage05-A target reference image path from manifest")
    workflow_mapping_key = str(reference_bootstrap.get("workflow_mapping_key") or "").strip()
    if not workflow_mapping_key:
        raise SystemExit("ERROR: Stage05 manifest is missing reference_bootstrap.workflow_mapping_key")

    character_bible_path = _character_bible_path_for_manifest(manifest_path)
    if not character_bible_path.exists():
        raise SystemExit(f"ERROR: Stage03 character_bible.json not found: {character_bible_path}")
    character_bible = load_json(character_bible_path)
    reference_plan_item = _resolve_reference_plan_item(character_bible, target_reference_path)
    character_entry = _resolve_character_entry(character_bible, reference_plan_item.get("character_id"))
    prompt, negative_prompt, lighting_prompt, camera_and_style_prompt = _bootstrap_prompt(
        reference_plan_item,
        character_entry,
        stage05_manifest,
    )
    bootstrap_manifest, bootstrap_manifest_path = _build_reference_bootstrap_manifest(
        stage05_manifest,
        manifest_path,
        target_reference_path=target_reference_path,
        reference_bootstrap=reference_bootstrap,
        prompt=prompt,
        negative_prompt=negative_prompt,
        lighting_prompt=lighting_prompt,
        camera_and_style_prompt=camera_and_style_prompt,
    )
    write_json(bootstrap_manifest_path, bootstrap_manifest)

    run_argv = [str(bootstrap_manifest_path), "--workflow-name", workflow_mapping_key]
    if args.allow_beyond_requested_scope:
        run_argv.append("--allow-beyond-requested-scope")
    exit_code = run_comfyui_txt2img.main(run_argv)
    if exit_code != 0:
        raise SystemExit(exit_code)

    refreshed_bootstrap_manifest = load_json(bootstrap_manifest_path)
    job = next(
        (item for item in (refreshed_bootstrap_manifest.get("jobs") or []) if isinstance(item, dict)),
        None,
    )
    if not isinstance(job, dict):
        raise SystemExit("ERROR: Stage05-A bootstrap manifest finished without a job record")
    output_path = Path(_normalize_path_text((job.get("evidence") or {}).get("file_path") or job.get("output_path"))).resolve()
    if not output_path.exists() or not output_path.is_file() or output_path.stat().st_size <= 0:
        raise SystemExit(f"ERROR: Stage05-A did not produce a usable reference image: {output_path}")

    target_path = (_project_dir_for_manifest(manifest_path) / target_reference_path).resolve()
    _copy_reference_image(output_path, target_path)

    refreshed_character_bible = _refresh_character_bible(character_bible_path)
    prompts_path = _keyframe_prompts_path_for_manifest(stage05_manifest, manifest_path)
    if prompts_path.exists():
        _refresh_keyframe_prompts(
            prompts_path,
            reference_status=refreshed_character_bible["reference_image_status"],
            stage05_execution_readiness=refreshed_character_bible["stage05_execution_readiness"],
        )

    refreshed_stage05_manifest = stage05_manifest
    if not args.skip_refresh_stage05:
        refreshed_stage05_manifest = _rebuild_stage05_manifest(
            manifest_path,
            optimization_profile=str(stage05_manifest.get("comfyui_optimization_profile") or "").strip() or None,
            allow_beyond_requested_scope=args.allow_beyond_requested_scope,
            provider_hint=_dominant_provider(stage05_manifest),
        )

    print(f"STAGE05A_REFERENCE_BOOTSTRAP_COMPLETED: {target_path}")
    print(f"BOOTSTRAP_WORKFLOW_MAPPING_KEY: {workflow_mapping_key}")
    print(f"BOOTSTRAP_CANDIDATE_IMAGE: {output_path}")
    print(f"PRIMARY_REFERENCE_READY: {str(bool((refreshed_character_bible.get('reference_image_status') or {}).get('all_present'))).lower()}")
    print(f"STAGE05B_WORKFLOW_MAPPING_KEY: {refreshed_stage05_manifest.get('comfyui_workflow_mapping_key')}")
    print(f"STAGE05B_MODE: {refreshed_stage05_manifest.get('stage05_mode')}")
    print(f"STAGE05B_REFERENCE_GUIDANCE_ACTIVE: {str(bool(refreshed_stage05_manifest.get('reference_guidance_active'))).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
