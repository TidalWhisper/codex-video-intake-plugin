from __future__ import annotations

from typing import Any


OUTPUT_SCOPE_ALIASES = {
    "A": "script_only",
    "只要剧本": "script_only",
    "B": "script_storyboard",
    "剧本 + 分镜脚本": "script_storyboard",
    "C": "keyframe_prompts",
    "剧本 + 分镜 + 关键帧提示词": "keyframe_prompts",
    "D": "keyframe_images",
    "生成关键帧图片素材包": "keyframe_images",
    "E": "video_clips",
    "生成视频片段素材包": "video_clips",
    "F": "rough_cut",
    "合成粗剪成片": "rough_cut",
    "G": "full_project",
    "输出完整素材工程包，方便人工剪辑": "full_project",
}

OUTPUT_SCOPE_RANK = {
    "script_only": 1,
    "script_storyboard": 2,
    "keyframe_prompts": 3,
    "keyframe_images": 4,
    "video_clips": 5,
    "rough_cut": 6,
    "full_project": 7,
}

STAGE_TO_SCOPE = {
    "STAGE_01": "script_only",
    "STAGE_02": "script_storyboard",
    "STAGE_03": "keyframe_prompts",
    "STAGE_04": "keyframe_prompts",
    "STAGE_05": "keyframe_images",
    "STAGE_06": "video_clips",
    "STAGE_07": "rough_cut",
    "STAGE_08": "rough_cut",
    "STAGE_09": "full_project",
}


def normal_brief(brief: dict[str, Any]) -> dict[str, Any]:
    normalized = brief.get("normalized")
    return normalized if isinstance(normalized, dict) else brief


def infer_output_scope(final_output: Any) -> str:
    raw = str(final_output or "").strip()
    if not raw:
        return ""
    return OUTPUT_SCOPE_ALIASES.get(raw, "")


def compiled_requirements_from_context(data: dict[str, Any]) -> dict[str, Any]:
    compiled = data.get("compiled_requirements")
    if isinstance(compiled, dict):
        return compiled
    routing = data.get("routing")
    if isinstance(routing, dict):
        scope = str(routing.get("requested_output_scope") or "").strip()
        if scope:
            return {"requested_output_scope": scope}
    return {}


def stage_scope(stage_name: str) -> str:
    stage_key = stage_name if stage_name in STAGE_TO_SCOPE else "_".join(stage_name.split("_", 2)[:2])
    return STAGE_TO_SCOPE.get(stage_key, "")


def _visual_family_hint(style: str, genre: str) -> str:
    joined = f"{style} {genre}".lower()
    if any(token in joined for token in ["动画", "动漫", "anime", "卡通", "manga"]):
        return "anime"
    if any(token in joined for token in ["国风", "古风", "水墨", "guofeng", "ink wash"]):
        return "guofeng"
    if any(token in joined for token in ["赛博", "潮流", "stylized", "concept art", "cg", "暗黑"]):
        return "stylized"
    return "realistic"


def _project_shape(genre: str, style: str, voice_mode: str, music_profile: str, characters_required: Any) -> str:
    joined = f"{genre} {style}".lower()
    if "mv" in joined or "音乐" in genre.lower():
        return "music_video"
    if any(token in genre for token in ["广告宣传", "产品展示"]):
        return "brand_promo"
    if any(token in genre for token in ["纪录片", "教育科普"]):
        return "factual_explainer"
    if characters_required is False:
        return "scene_led_visual"
    if music_profile == "song" and "对白" not in voice_mode:
        return "music_led_visual"
    return "narrative_short"


def _creative_focus(shape: str) -> str:
    return {
        "music_video": "rhythm_and_visual_mood",
        "brand_promo": "message_clarity_and_product_focus",
        "factual_explainer": "fact_clarity_and_explanation_flow",
        "scene_led_visual": "atmosphere_and_composition",
        "music_led_visual": "mood_and_music_sync",
        "narrative_short": "story_and_emotional_arc",
    }.get(shape, "story_and_emotional_arc")


def _continuity_mode(shape: str, characters_required: Any) -> str:
    if characters_required is False:
        return "scene_locked"
    if shape in {"brand_promo", "narrative_short", "music_video"}:
        return "character_locked"
    return "hybrid"


def _stage05_provider_priority(shape: str, visual_hint: str) -> list[str]:
    if visual_hint in {"anime", "guofeng", "stylized"}:
        return ["comfyui_txt2img", "openai_gpt_image2", "manual"]
    if shape in {"brand_promo", "factual_explainer"}:
        return ["openai_gpt_image2", "comfyui_txt2img", "manual"]
    return ["openai_gpt_image2", "comfyui_txt2img", "manual"]


def _stage07_music_priority(shape: str, music_required: Any) -> list[str]:
    if music_required is not True:
        return []
    if shape in {"music_video", "music_led_visual"}:
        return ["comfyui_music", "manual"]
    return ["comfyui_music", "local_music_library", "manual"]


def compile_requirements(brief: dict[str, Any]) -> dict[str, Any]:
    normalized = normal_brief(brief)
    genre = str(normalized.get("genre") or "")
    style = str(normalized.get("style") or "")
    voice_mode = str(normalized.get("voice_mode") or "")
    music_profile = str(normalized.get("music_profile") or "")
    music_required = normalized.get("music_required")
    characters_required = normalized.get("characters_required")
    output_scope = infer_output_scope(normalized.get("final_output") or brief.get("final_output"))
    visual_hint = _visual_family_hint(style, genre)
    shape = _project_shape(genre, style, voice_mode, music_profile, characters_required)
    creative_focus = _creative_focus(shape)
    continuity_mode = _continuity_mode(shape, characters_required)
    human_review_flags: list[str] = []
    if shape == "brand_promo":
        human_review_flags.append("brand_message_accuracy")
    if shape == "factual_explainer":
        human_review_flags.append("fact_claim_accuracy")

    return {
        "schema_version": "0.1.0",
        "project_shape": shape,
        "requested_output_scope": output_scope,
        "creative_focus": creative_focus,
        "continuity_mode": continuity_mode,
        "visual_family_hint": visual_hint,
        "audio_mode": {
            "voice_mode": voice_mode,
            "music_profile": music_profile,
            "music_required": music_required,
        },
        "stage_directives": {
            "stage01": {
                "script_mode": "message_first" if shape in {"brand_promo", "factual_explainer"} else "dramatic_arc",
                "pace_bias": "compact" if output_scope in {"script_only", "script_storyboard"} else "balanced",
            },
            "stage02": {
                "storyboard_mode": "benefit_demo" if shape == "brand_promo" else "narrative_coverage",
                "continuity_mode": continuity_mode,
            },
            "stage03": {
                "reference_priority": "product_or_subject_consistency" if characters_required is False else "character_consistency",
            },
            "stage04": {
                "prompt_mode": "performance_driven" if shape in {"narrative_short", "music_video"} else "clarity_driven",
            },
        },
        "provider_preferences": {
            "stage05_provider_priority": _stage05_provider_priority(shape, visual_hint),
            "stage06_provider_priority": ["comfyui_ltx_i2v", "manual"],
            "stage07_voice_provider_priority": ["indextts2", "manual"],
            "stage07_music_provider_priority": _stage07_music_priority(shape, music_required),
        },
        "qa_profile": {
            "axes": [
                "intent_alignment",
                "visual_continuity",
                "performance_direction",
                "audio_direction",
                "delivery_readiness",
            ],
            "human_review_flags": human_review_flags,
        },
    }


def stage_meets_requested_output(stage_name: str, compiled: dict[str, Any]) -> bool:
    requested = str(compiled.get("requested_output_scope") or "")
    if not requested or requested not in OUTPUT_SCOPE_RANK:
        return False
    required_scope = stage_scope(stage_name)
    if required_scope not in OUTPUT_SCOPE_RANK:
        return False
    return OUTPUT_SCOPE_RANK[required_scope] >= OUTPUT_SCOPE_RANK[requested]


def requested_output_allows_stage(stage_name: str, compiled: dict[str, Any]) -> bool:
    requested = str(compiled.get("requested_output_scope") or "")
    if not requested or requested not in OUTPUT_SCOPE_RANK:
        return True
    required_scope = stage_scope(stage_name)
    if required_scope not in OUTPUT_SCOPE_RANK:
        return True
    return OUTPUT_SCOPE_RANK[requested] >= OUTPUT_SCOPE_RANK[required_scope]


def requested_scope_label(scope: str) -> str:
    return {
        "script_only": "只要剧本",
        "script_storyboard": "剧本 + 分镜脚本",
        "keyframe_prompts": "剧本 + 分镜 + 关键帧提示词",
        "keyframe_images": "生成关键帧图片素材包",
        "video_clips": "生成视频片段素材包",
        "rough_cut": "合成粗剪成片",
        "full_project": "输出完整素材工程包，方便人工剪辑",
    }.get(scope, scope)


def requested_output_scope_guard_message(stage_name: str, compiled: dict[str, Any]) -> str | None:
    if requested_output_allows_stage(stage_name, compiled):
        return None
    requested = str(compiled.get("requested_output_scope") or "").strip()
    required_scope = stage_scope(stage_name)
    return (
        f"requested output scope '{requested_scope_label(requested)}' does not allow {stage_name}; "
        f"this stage requires at least '{requested_scope_label(required_scope)}'. "
        "Re-run with --allow-beyond-requested-scope to override."
    )
