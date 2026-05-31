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
from stage05_image_utils import (  # noqa: E402
    load_json,
    reference_bootstrap_candidates,
    resolve_path,
    write_json,
)

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

import new_keyframe_image_jobs  # noqa: E402
import run_comfyui_txt2img  # noqa: E402
import sync_keyframe_image_manifest  # noqa: E402


def _normalize_path_text(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/")


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


def _character_bible_path_for_manifest(manifest_path: Path) -> Path:
    return manifest_path.parents[1] / "03_characters" / "character_bible.json"


def _project_dir_for_manifest(manifest_path: Path) -> Path:
    return manifest_path.parents[1]


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


def _jobs_for_reference_shot_bundle(
    manifest: dict[str, Any],
    *,
    target_reference_path: str,
    source_candidate: dict[str, Any],
    rerun_all_reference_jobs: bool,
) -> list[str]:
    jobs = manifest.get("jobs") if isinstance(manifest.get("jobs"), list) else []
    normalized_target = _normalize_path_text(target_reference_path)
    source_shot_id = str(source_candidate.get("shot_id") or "").strip()
    selected: list[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        image_id = str(job.get("image_id") or "").strip()
        if not image_id:
            continue
        reference_images = {
            _normalize_path_text(item)
            for item in (job.get("reference_images") or [])
            if isinstance(item, str) and str(item).strip()
        }
        if normalized_target not in reference_images:
            continue
        if not rerun_all_reference_jobs and source_shot_id and str(job.get("shot_id") or "").strip() != source_shot_id:
            continue
        selected.append(image_id)
    return selected


def _rerun_reference_guided_jobs(
    manifest_path: Path,
    *,
    image_ids: list[str],
    allow_beyond_requested_scope: bool,
) -> tuple[list[str], list[str]]:
    succeeded: list[str] = []
    failed: list[str] = []
    seen: set[str] = set()
    for image_id in image_ids:
        normalized = str(image_id or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        argv = [str(manifest_path), "--image-id", normalized]
        if allow_beyond_requested_scope:
            argv.append("--allow-beyond-requested-scope")
        exit_code = run_comfyui_txt2img.main(argv)
        if exit_code == 0:
            succeeded.append(normalized)
        else:
            failed.append(normalized)
    return succeeded, failed


def _resolve_source_candidate(
    manifest_path: Path,
    *,
    target_reference_path: str,
    source_image_id: str | None,
) -> dict[str, Any]:
    candidates = reference_bootstrap_candidates(
        manifest_path,
        missing_reference_images=[target_reference_path],
    )
    if source_image_id:
        for item in candidates:
            if str(item.get("image_id") or "").strip() == source_image_id:
                return item
        raise SystemExit(f"ERROR: source_image_id not found among usable bootstrap candidates: {source_image_id}")
    if not candidates:
        raise SystemExit(
            "ERROR: no usable bootstrap candidate found. At least one existing Stage 05 keyframe that references this missing Stage 03 target is required."
        )
    return candidates[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--target-reference", required=True, help="Missing Stage 03 reference path, e.g. 03_characters/reference_images/CHAR_001_primary.png")
    parser.add_argument("--source-image-id", default=None, help="Optional Stage 05 image_id to use as the bootstrap source")
    parser.add_argument("--skip-refresh-stage05", action="store_true", help="Only copy the reference image and refresh Stage 03, without rebuilding Stage 05")
    parser.add_argument("--skip-rerun-shot-bundle", action="store_true", help="Do not automatically rerun the affected shot bundle after Stage 05 switches to reference-guided mode")
    parser.add_argument("--rerun-all-reference-jobs", action="store_true", help="After bootstrap, rerun every Stage 05 job that depends on this reference image instead of only the source shot bundle")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Pass through to Stage 05 regeneration when the requested output scope stops earlier")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json).resolve()
    manifest = load_json(manifest_path)
    target_reference = _normalize_path_text(args.target_reference)
    if not target_reference:
        print("ERROR: --target-reference must be non-empty", file=sys.stderr)
        return 1

    source_candidate = _resolve_source_candidate(
        manifest_path,
        target_reference_path=target_reference,
        source_image_id=str(args.source_image_id or "").strip() or None,
    )
    source_path = resolve_path(manifest_path, source_candidate["source_path"])
    target_path = (_project_dir_for_manifest(manifest_path) / target_reference).resolve()
    _copy_reference_image(source_path, target_path)

    character_bible_path = _character_bible_path_for_manifest(manifest_path)
    refreshed_character_bible = None
    if character_bible_path.exists():
        refreshed_character_bible = _refresh_character_bible(character_bible_path)
        prompts_path = Path(_normalize_path_text(manifest.get("source_keyframe_prompts"))).resolve()
        if prompts_path.exists():
            _refresh_keyframe_prompts(
                prompts_path,
                reference_status=refreshed_character_bible["reference_image_status"],
                stage05_execution_readiness=refreshed_character_bible["stage05_execution_readiness"],
            )

    refreshed_manifest = manifest
    if not args.skip_refresh_stage05:
        refreshed_manifest = _rebuild_stage05_manifest(
            manifest_path,
            optimization_profile=str(manifest.get("comfyui_optimization_profile") or "").strip() or None,
            allow_beyond_requested_scope=args.allow_beyond_requested_scope,
            provider_hint=_dominant_provider(manifest),
        )

    rerun_succeeded: list[str] = []
    rerun_failed: list[str] = []
    if not args.skip_rerun_shot_bundle and not args.skip_refresh_stage05:
        impacted_image_ids = _jobs_for_reference_shot_bundle(
            refreshed_manifest,
            target_reference_path=target_reference,
            source_candidate=source_candidate,
            rerun_all_reference_jobs=bool(args.rerun_all_reference_jobs),
        )
        rerun_succeeded, rerun_failed = _rerun_reference_guided_jobs(
            manifest_path,
            image_ids=impacted_image_ids,
            allow_beyond_requested_scope=args.allow_beyond_requested_scope,
        )
        refreshed_manifest = load_json(manifest_path)

    print(f"BOOTSTRAP_REFERENCE_IMAGE_COMPLETED: {target_path}")
    print(f"SOURCE_IMAGE_ID: {source_candidate['image_id']}")
    print(f"SOURCE_IMAGE_PATH: {source_path}")
    if refreshed_character_bible is not None:
        ready = bool((refreshed_character_bible.get("reference_image_status") or {}).get("all_present"))
        print(f"CHARACTER_REFERENCE_READY: {str(ready).lower()}")
    route_resolution = refreshed_manifest.get("route_resolution") if isinstance(refreshed_manifest.get("route_resolution"), dict) else {}
    print(f"STAGE05_WORKFLOW_MAPPING_KEY: {refreshed_manifest.get('comfyui_workflow_mapping_key')}")
    print(f"STAGE05_WORKFLOW_NAME: {refreshed_manifest.get('comfyui_workflow_name')}")
    print(f"REFERENCE_GUIDANCE_ACTIVE: {str(bool(refreshed_manifest.get('reference_guidance_active'))).lower()}")
    if rerun_succeeded:
        print(f"RERUN_SUCCEEDED_IMAGE_IDS: {','.join(rerun_succeeded)}")
    if rerun_failed:
        print(f"RERUN_FAILED_IMAGE_IDS: {','.join(rerun_failed)}")
    if route_resolution:
        print(f"ROUTE_RESOLUTION_MODE: {route_resolution.get('workflow_mapping_resolution')}")
    return 1 if rerun_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
