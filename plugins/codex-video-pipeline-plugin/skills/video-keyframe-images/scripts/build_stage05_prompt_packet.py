#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "video-keyframe-prompts" / "scripts"))

from pipeline_blueprints import normal_brief, routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from build_stage04_prompt_packet import ensure_locked_brief  # noqa: E402


STAGE05_BOOTSTRAP_ROUTE_OPTIONS = [
    {
        "style_family": "realistic",
        "workflow_mapping_key": "stage05_realistic_cinematic_amazing_z_photo_original",
        "workflow_name": "amazing_z_photo_safetensors",
        "comfyui_model_id": "Tongyi-MAI/Z-Image",
        "preferred_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json",
    },
    {
        "style_family": "anime",
        "workflow_mapping_key": "stage05_anime_jp",
        "workflow_name": "amazing_z_image_a_safetensors",
        "comfyui_model_id": "Tongyi-MAI/Z-Image",
        "preferred_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json",
    },
    {
        "style_family": "guofeng",
        "workflow_mapping_key": "stage05_anime_jp",
        "workflow_name": "amazing_z_image_a_safetensors",
        "comfyui_model_id": "Tongyi-MAI/Z-Image",
        "preferred_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json",
    },
    {
        "style_family": "stylized",
        "workflow_mapping_key": "stage05_western_cartoon",
        "workflow_name": "amazing_z_comics_safetensors",
        "comfyui_model_id": "Tongyi-MAI/Z-Image",
        "preferred_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-comics_SAFETENSORS.json",
    },
]

STAGE05_B_MAINLINE = {
    "stage05_mode": "reference_guided_storyboard",
    "comfyui_workflow_mapping_key": "stage05_realistic_cinematic_qwen_edit_nextscene_local",
    "comfyui_workflow_name": "qwen_edit_nextscene_local",
    "comfyui_model_id": "Qwen/Qwen-Edit-2511",
    "preferred_comfyui_workflow_candidate": "qwen_edit_nextscene_local",
    "preferred_comfyui_model_candidate": "Qwen/Qwen-Edit-2511",
    "preferred_comfyui_workflow_source_ref": "F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json",
    "preferred_comfyui_workflow_format": "ui_graph",
    "preferred_comfyui_workflow_custom_node_dependencies": ["rgthree-comfy"],
    "preferred_comfyui_workflow_import_blockers": [],
    "comfyui_control_mode": "reference_guided",
    "prompt_composition_mode": "codex_contract",
    "primary_reference_image_path": "03_characters/reference_images/CHAR_001_primary.png",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def _normalize_path_text(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/")


def _resolve_related_json(base_json: Path, raw: str | None) -> Path | None:
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
        resolved = anchor.resolve()
        key = str(resolved).lower()
        if key not in seen:
            anchors.append(resolved)
            seen.add(key)
    for anchor in anchors:
        resolved = (anchor / candidate).resolve()
        if resolved.exists():
            return resolved
    return (base_json.parent / candidate).resolve()


def ensure_stage04_keyframe_prompts(data: dict[str, Any]) -> None:
    if data.get("stage") != "STAGE_04_KEYFRAME_PROMPTS":
        raise SystemExit("ERROR: keyframe_prompts.stage must be STAGE_04_KEYFRAME_PROMPTS")
    if str(data.get("status") or "").strip().lower() not in {"draft", "confirmed"}:
        raise SystemExit("ERROR: keyframe_prompts.status must be draft or confirmed")


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _non_empty_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        cleaned = str(item or "").strip()
        if cleaned:
            items.append(cleaned)
    return items


def _shot_semantics(keyframe_prompts: dict[str, Any]) -> list[dict[str, Any]]:
    shots: list[dict[str, Any]] = []
    for shot in _list_of_dicts(keyframe_prompts.get("shot_prompts")):
        shot_id = str(shot.get("shot_id") or "").strip()
        if not shot_id:
            continue
        shots.append({
            "shot_id": shot_id,
            "scene_summary": str(shot.get("scene_summary") or "").strip(),
            "intent_summary": str(shot.get("intent_summary") or "").strip(),
            "story_anchor_bundle": dict(shot.get("story_anchor_bundle") or {}),
            "prompts": {
                "start_keyframe_prompt": str(shot.get("start_keyframe_prompt") or "").strip(),
                "end_keyframe_prompt": str(shot.get("end_keyframe_prompt") or "").strip(),
                "motion_prompt": str(shot.get("motion_prompt") or "").strip(),
                "camera_prompt": str(shot.get("camera_prompt") or "").strip(),
                "lighting_prompt": str(shot.get("lighting_prompt") or "").strip(),
                "style_prompt": str(shot.get("style_prompt") or "").strip(),
                "consistency_prompt": str(shot.get("consistency_prompt") or "").strip(),
                "identity_anchor_prompt": str(shot.get("identity_anchor_prompt") or "").strip(),
                "negative_prompt": str(shot.get("negative_prompt") or "").strip(),
            },
            "reference_images": _non_empty_strings(((shot.get("dependencies") or {}).get("reference_images"))),
            "image_generation_notes": str(shot.get("image_generation_notes") or "").strip(),
        })
    return shots


def _storyboard_beats(storyboard: dict[str, Any]) -> list[dict[str, Any]]:
    beats: list[dict[str, Any]] = []
    for shot in _list_of_dicts(storyboard.get("shots")):
        shot_id = str(shot.get("shot_id") or shot.get("id") or "").strip()
        if not shot_id:
            continue
        beats.append({
            "shot_id": shot_id,
            "summary": str(
                shot.get("summary")
                or shot.get("scene_summary")
                or shot.get("intent_summary")
                or ""
            ).strip(),
            "emotion": str(
                shot.get("emotion")
                or ((shot.get("story_anchor_bundle") or {}).get("emotion"))
                or ""
            ).strip(),
            "key_prop": str(
                shot.get("key_prop")
                or ((shot.get("story_anchor_bundle") or {}).get("key_prop"))
                or ""
            ).strip(),
            "camera_intent": str(
                shot.get("camera_intent")
                or shot.get("camera_prompt")
                or ""
            ).strip(),
        })
    return beats


def _reference_plan_summary(character_bible: dict[str, Any]) -> list[dict[str, Any]]:
    plan_items: list[dict[str, Any]] = []
    for item in _list_of_dicts(character_bible.get("reference_image_plan")):
        target_path = _normalize_path_text(
            item.get("target_path")
            or item.get("reference_image_path")
            or item.get("output_path")
        )
        if not target_path:
            continue
        plan_items.append({
            "character_id": str(item.get("character_id") or "").strip(),
            "target_path": target_path,
            "goal": str(
                item.get("goal")
                or item.get("purpose")
                or item.get("guidance")
                or ""
            ).strip(),
            "carry_over_props": _non_empty_strings(item.get("carry_over_props")),
            "must_not_include": _non_empty_strings(
                item.get("must_not_include")
                or item.get("negative_props")
            ),
        })
    return plan_items


def _character_anchor_summaries(character_bible: dict[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for character in _list_of_dicts(character_bible.get("characters")):
        character_id = str(
            character.get("character_id")
            or character.get("id")
            or ""
        ).strip()
        if not character_id:
            continue
        anchors.append({
            "character_id": character_id,
            "role": str(character.get("role") or "").strip(),
            "display_name": str(
                character.get("display_name")
                or character.get("name")
                or ""
            ).strip(),
            "visual_consistency_prompt": str(
                character.get("visual_consistency_prompt") or ""
            ).strip(),
            "negative_consistency_prompt": str(
                character.get("negative_consistency_prompt") or ""
            ).strip(),
            "performance_profile": dict(character.get("performance_profile") or {}),
        })
    return anchors


def build_packet(
    brief: dict[str, Any],
    keyframe_prompts: dict[str, Any],
    *,
    brief_path: Path,
    keyframe_path: Path,
) -> dict[str, Any]:
    normalized = normal_brief(brief)
    character_bible_path = _resolve_related_json(keyframe_path, _normalize_path_text(keyframe_prompts.get("source_character_bible")))
    storyboard_path = _resolve_related_json(keyframe_path, _normalize_path_text(keyframe_prompts.get("source_storyboard")))
    character_bible = load_json(character_bible_path) if character_bible_path and character_bible_path.exists() else {}
    storyboard = load_json(storyboard_path) if storyboard_path and storyboard_path.exists() else {}
    project_dir = Path(str(brief.get("project_dir") or "")).resolve() if brief.get("project_dir") else brief_path.parents[2]
    return {
        "packet_version": "0.1.0",
        "project_id": str(brief.get("project_id") or keyframe_prompts.get("project_id") or project_dir.name),
        "project_dir": str(project_dir).replace("\\", "/"),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_keyframe_prompts": str(keyframe_path.resolve()).replace("\\", "/"),
        "source_storyboard": str(storyboard_path.resolve()).replace("\\", "/") if storyboard_path else None,
        "source_character_bible": str(character_bible_path.resolve()).replace("\\", "/") if character_bible_path else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creative_goal": "Generate the official Stage 05 semantic contract so Python can execute the Stage05-A/Stage05-B mainline mechanically.",
        "hard_constraints": {
            "genre": str(normalized.get("genre") or ""),
            "style": str(normalized.get("style") or ""),
            "aspect_ratio": str(normalized.get("aspect_ratio") or ""),
            "resolution": str(normalized.get("resolution") or ""),
            "final_output": str(normalized.get("final_output") or ""),
        },
        "routing": routing_from_brief(brief),
        "official_mainline_constraints": {
            "stage05_a_bootstrap_route_options": [
                {
                    "style_family": item["style_family"],
                    "workflow_mapping_key": item["workflow_mapping_key"],
                    "workflow_name": item["workflow_name"],
                    "comfyui_model_id": item["comfyui_model_id"],
                }
                for item in STAGE05_BOOTSTRAP_ROUTE_OPTIONS
            ],
            "stage05_b_mainline": {
                "stage05_mode": STAGE05_B_MAINLINE["stage05_mode"],
                "comfyui_control_mode": STAGE05_B_MAINLINE["comfyui_control_mode"],
                "prompt_composition_mode": STAGE05_B_MAINLINE["prompt_composition_mode"],
                "default_workflow_mapping_key": STAGE05_B_MAINLINE["comfyui_workflow_mapping_key"],
                "default_workflow_name": STAGE05_B_MAINLINE["comfyui_workflow_name"],
                "default_model_id": STAGE05_B_MAINLINE["comfyui_model_id"],
            },
            "python_must_execute_mechanically_only": True,
            "python_must_not_decide_route_or_prompt_or_review": True,
            "codex_should_only_return_semantic_fields_python_cannot_infer": [
                "bootstrap prompt body",
                "per-job provider prompt body",
                "per-job negative prompt",
                "review decision",
                "repair direction",
                "optional per-job runtime overrides when a shot truly needs them",
            ],
        },
        "stage05_input_summary": {
            "prompt_language": keyframe_prompts.get("prompt_language"),
            "visual_strategy": keyframe_prompts.get("visual_strategy"),
            "story_anchors": keyframe_prompts.get("story_anchors"),
            "global_negative_prompt": keyframe_prompts.get("global_negative_prompt"),
            "stage05_handoff": keyframe_prompts.get("stage05_handoff"),
            "reference_image_status": keyframe_prompts.get("reference_image_status"),
            "stage05_execution_readiness": keyframe_prompts.get("stage05_execution_readiness"),
            "shot_semantics": _shot_semantics(keyframe_prompts),
        },
        "storyboard_context": {
            "target_duration_sec": storyboard.get("target_duration_sec"),
            "shot_count": storyboard.get("shot_count"),
            "shot_beats": _storyboard_beats(storyboard),
        },
        "reference_context": {
            "reference_image_required": bool(character_bible.get("reference_image_required")),
            "reference_image_status": character_bible.get("reference_image_status"),
            "stage05_execution_readiness": character_bible.get("stage05_execution_readiness"),
            "reference_image_handoff": character_bible.get("reference_image_handoff"),
            "reference_image_plan_items": _reference_plan_summary(character_bible),
            "character_anchor_summaries": _character_anchor_summaries(character_bible),
        },
        "schema_refs": {
            "llm_output_schema": "skills/video-keyframe-images/references/stage05_semantic_contract.schema.json",
            "generation_prompt": "skills/video-keyframe-images/references/stage05_codex_generation_prompt.md",
            "repair_prompt": "skills/video-keyframe-images/references/stage05_codex_repair_prompt.md",
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: python build_stage05_prompt_packet.py <locked_brief.json> <keyframe_prompts.json> <output.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1]).resolve()
    keyframe_path = Path(argv[2]).resolve()
    output_path = Path(argv[3]).resolve()
    brief = load_json(brief_path)
    keyframe_prompts = load_json(keyframe_path)
    ensure_locked_brief(brief)
    ensure_stage04_keyframe_prompts(keyframe_prompts)
    packet = build_packet(brief, keyframe_prompts, brief_path=brief_path, keyframe_path=keyframe_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"STAGE05_PROMPT_PACKET_CREATED: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
