from __future__ import annotations

from pathlib import Path
from typing import Any


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def build_reference_image_plan(project_id: str, characters: list[dict[str, Any]]) -> dict[str, Any]:
    plan = {
        "project_id": project_id,
        "required": True,
        "reference_images": [],
    }
    for character in characters:
        if not isinstance(character, dict):
            continue
        character_id = _clean_text(character.get("character_id"))
        if not character_id:
            continue
        plan["reference_images"].append({
            "character_id": character_id,
            "name": _clean_text(character.get("name")),
            "target_path": f"03_characters/reference_images/{character_id}_primary.png",
            "visual_consistency_prompt": character.get("visual_consistency_prompt"),
            "negative_consistency_prompt": character.get("negative_consistency_prompt"),
        })
    return plan


def _resolve_target_path(stage03_dir: Path, target_path: str) -> Path:
    raw = Path(target_path)
    if raw.is_absolute():
        return raw
    project_dir = stage03_dir.parent
    return (project_dir / raw).resolve()


def build_reference_image_status(stage03_dir: Path, reference_plan: dict[str, Any]) -> dict[str, Any]:
    reference_images = reference_plan.get("reference_images") if isinstance(reference_plan.get("reference_images"), list) else []
    target_paths: list[str] = []
    existing_paths: list[str] = []
    missing_paths: list[str] = []
    detailed_items: list[dict[str, Any]] = []
    for item in reference_images:
        if not isinstance(item, dict):
            continue
        target_path = _clean_text(item.get("target_path"))
        if not target_path:
            continue
        resolved = _resolve_target_path(stage03_dir, target_path)
        normalized = target_path.replace("\\", "/")
        target_paths.append(normalized)
        exists = resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0
        if exists:
            existing_paths.append(normalized)
        else:
            missing_paths.append(normalized)
        detailed_items.append({
            "character_id": _clean_text(item.get("character_id")),
            "target_path": normalized,
            "file_exists": exists,
        })
    return {
        "required": bool(reference_plan.get("required", True)),
        "target_paths": target_paths,
        "existing_paths": existing_paths,
        "missing_paths": missing_paths,
        "all_present": bool(target_paths) and not missing_paths if target_paths else False,
        "item_count": len(target_paths),
        "missing_count": len(missing_paths),
        "items": detailed_items,
    }


def build_stage05_execution_readiness(
    *,
    continuity_mode: str,
    reference_image_required: bool,
    reference_image_status: dict[str, Any],
) -> dict[str, Any]:
    missing_paths = [
        _clean_text(item)
        for item in (reference_image_status.get("missing_paths") or [])
        if _clean_text(item)
    ]
    safe_to_auto_generate = True
    blocker_reasons: list[str] = []
    if continuity_mode == "character_locked" and reference_image_required and missing_paths:
        safe_to_auto_generate = False
        blocker_reasons.append("missing_character_reference_images")
    return {
        "continuity_mode": continuity_mode,
        "reference_image_required": bool(reference_image_required),
        "safe_to_auto_generate": safe_to_auto_generate,
        "blocker_reasons": blocker_reasons,
        "missing_reference_images": missing_paths,
    }
