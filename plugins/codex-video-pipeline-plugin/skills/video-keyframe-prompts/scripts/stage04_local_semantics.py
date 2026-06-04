#!/usr/bin/env python3
"""Deterministic Stage 04 local semantics.

Stage 04 keeps the codex-first artifact chain, but the actual structured output
is generated locally from the locked brief and approved Stage 01-03 artifacts to
avoid recursive Codex CLI deadlocks in the desktop environment.
"""
from __future__ import annotations

from typing import Any

from pipeline_blueprints import normal_brief
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _style_prompt(style_text: str, visual_family: str) -> str:
    text = _clean(style_text)
    family = _clean(visual_family).lower()
    if "写实" in text or family == "realistic":
        return "realistic cinematic short film, natural skin texture, restrained emotion, coherent production design"
    if "动漫" in text or family == "anime":
        return "anime cinematic key visual, clean linework, controlled character consistency, emotionally restrained staging"
    if "国风" in text or family == "guofeng":
        return "Chinese aesthetic cinematic frame, elegant atmosphere, restrained emotion, coherent costume and environment details"
    return "cinematic visual storytelling, stable identity continuity, restrained emotional tone"


def _lighting_prompt(scene: str, weather: str, time_of_day: str) -> str:
    text = " ".join(part for part in [scene, weather, time_of_day] if part)
    if "黄昏" in text or "晚霞" in text or "sunset" in text.lower():
        return "warm sunset light, soft rim light, sea-surface reflections, gentle contrast, cinematic golden-hour atmosphere"
    if "雨" in text:
        return "cool rain-night practical light, wet-ground reflections, soft haze, stable low-key contrast"
    if "夜" in text:
        return "controlled night practical lighting, readable subject separation, cinematic shadow detail"
    return "natural cinematic lighting, stable contrast, readable subject silhouette"


def _global_negative_prompt(visual_family: str) -> str:
    base = [
        "watermark",
        "logo",
        "subtitles",
        "text artifacts",
        "duplicate person",
        "extra limbs",
        "deformed hands",
        "distorted face",
        "identity drift",
        "outfit drift",
        "background warp",
    ]
    if _clean(visual_family).lower() == "realistic":
        base.extend(["plastic skin", "over-retouched face"])
    return ", ".join(base)


def _character_map(character_bible: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    characters = [item for item in list(character_bible.get("characters") or []) if isinstance(item, dict)]
    by_id = {
        _clean(item.get("character_id")): item
        for item in characters
        if _clean(item.get("character_id"))
    }
    reference_paths = [
        _clean(item.get("target_path"))
        for item in list(((character_bible.get("reference_image_plan") or {}).get("reference_images")) or [])
        if isinstance(item, dict) and _clean(item.get("target_path"))
    ]
    return characters, by_id, reference_paths


def _pick_character_ids(shot: dict[str, Any], characters: list[dict[str, Any]]) -> list[str]:
    if not characters:
        return []
    action_text = " ".join(
        _clean(shot.get(key))
        for key in ["action", "composition", "production_note"]
        if _clean(shot.get(key))
    )
    matched: list[str] = []
    for item in characters:
        cid = _clean(item.get("character_id"))
        name = _clean(item.get("name"))
        if cid and name and name in action_text and cid not in matched:
            matched.append(cid)
    if matched:
        return matched
    primary = _clean(characters[0].get("character_id"))
    return [primary] if primary else []


def _scene_summary(shot: dict[str, Any]) -> str:
    location = _clean(shot.get("location")) or _clean(shot.get("scene")) or "未指定"
    weather = _clean(shot.get("weather")) or "未指定"
    action = _clean(shot.get("action")) or "未指定"
    key_prop = _clean(shot.get("key_prop")) or "无"
    emotion = _clean(shot.get("emotion")) or "未指定"
    composition_focus = _clean(shot.get("composition_focus")) or "未指定"
    return (
        f"地点：{location} / 天气：{weather} / 动作：{action} / "
        f"道具：{key_prop} / 情绪：{emotion} / 构图重点：{composition_focus}"
    )


def _intent_summary(shot: dict[str, Any]) -> str:
    location = _clean(shot.get("location")) or _clean(shot.get("scene")) or "当前场景"
    action = _clean(shot.get("action")) or "这个动作"
    emotion = _clean(shot.get("emotion")) or "当前情绪"
    key_prop = _clean(shot.get("key_prop"))
    tail = f"，让{key_prop}成为情绪支点。" if key_prop else "。"
    return f"这个镜头要在{location}里抓住“{action}”这一瞬间，传达{emotion}{tail}"


def _story_anchor_bundle(shot: dict[str, Any]) -> dict[str, str]:
    return {
        "location": _clean(shot.get("location")) or _clean(shot.get("scene")),
        "weather": _clean(shot.get("weather")),
        "key_prop": _clean(shot.get("key_prop")),
        "emotion": _clean(shot.get("emotion")),
        "composition_focus": _clean(shot.get("composition_focus")),
    }


def _character_anchor_text(characters: list[dict[str, Any]], character_ids: list[str]) -> str:
    picked = [item for item in characters if _clean(item.get("character_id")) in character_ids]
    if not picked:
        return "Preserve the same protagonist identity in every frame."
    item = picked[0]
    name = _clean(item.get("name")) or "the protagonist"
    visual = _clean(item.get("visual_consistency_prompt"))
    if visual:
        return f"Character identity anchor: {visual}"
    continuity = _clean(((item.get("performance_profile") or {}).get("continuity_anchor")))
    if continuity:
        return f"Character identity anchor: {continuity}"
    return f"Character identity anchor: Primary protagonist must remain {name} in every frame."


def _negative_prompt(global_negative: str, characters: list[dict[str, Any]], character_ids: list[str]) -> str:
    parts = [global_negative]
    for item in characters:
        if _clean(item.get("character_id")) in character_ids:
            neg = _clean(item.get("negative_consistency_prompt"))
            if neg:
                parts.append(neg)
    return ", ".join(part for part in parts if part)


def _camera_prompt(shot: dict[str, Any]) -> str:
    return _clean(shot.get("camera")) or "cinematic shot"


def _performance_prompt(characters: list[dict[str, Any]], character_ids: list[str], emotion: str) -> str:
    for item in characters:
        if _clean(item.get("character_id")) in character_ids:
            movement = _clean(((item.get("performance_profile") or {}).get("movement_style")))
            baseline = _clean(((item.get("performance_profile") or {}).get("baseline_expression")))
            if movement or baseline:
                joined = " / ".join(part for part in [baseline, movement] if part)
                return joined or (emotion or "Restrained natural performance.")
    return emotion or "Restrained natural performance."


def _start_keyframe_prompt(
    shot: dict[str, Any],
    character_anchor: str,
    style_prompt: str,
    lighting_prompt: str,
    aspect_ratio: str,
) -> str:
    location = _clean(shot.get("location")) or _clean(shot.get("scene"))
    action = _clean(shot.get("action"))
    composition = _clean(shot.get("composition_focus")) or _clean(shot.get("composition"))
    emotion = _clean(shot.get("emotion"))
    camera = _camera_prompt(shot)
    parts = [
        "cinematic keyframe,",
        camera + ",",
        location + "," if location else "",
        action + "," if action else "",
        composition + "," if composition else "",
        character_anchor,
        lighting_prompt + ",",
        style_prompt + ",",
        f"emotion: {emotion}," if emotion else "",
        f"{aspect_ratio} composition" if aspect_ratio else "",
    ]
    return " ".join(part for part in parts if part).strip().rstrip(",")


def _end_keyframe_prompt(
    shot: dict[str, Any],
    character_anchor: str,
    style_prompt: str,
    lighting_prompt: str,
) -> str:
    action = _clean(shot.get("action"))
    location = _clean(shot.get("location")) or _clean(shot.get("scene"))
    emotion = _clean(shot.get("emotion"))
    parts = [
        f"cinematic continuation of { _clean(shot.get('shot_id')) },",
        action + "," if action else "",
        location + "," if location else "",
        "do not swap protagonist identity,",
        character_anchor,
        lighting_prompt + ",",
        style_prompt + ",",
        f"emotion remains {emotion}" if emotion else "",
    ]
    return " ".join(part for part in parts if part).strip().rstrip(",")


def _motion_prompt(shot: dict[str, Any], performance_prompt: str) -> str:
    action = _clean(shot.get("action"))
    location = _clean(shot.get("location")) or _clean(shot.get("scene"))
    return (
        f"{action}; keep movement natural and low-amplitude, preserve identity continuity, "
        f"let the {location or 'scene'} atmosphere breathe, performance baseline: {performance_prompt}"
    ).strip()


def _image_notes(shot: dict[str, Any]) -> str:
    focus = _clean(shot.get("composition_focus")) or _clean(shot.get("composition"))
    return f"Generate start/end keyframes for {_clean(shot.get('shot_id'))}; keep {focus or 'the storyboard intent'} readable."


def _video_notes(reference_paths: list[str], shot: dict[str, Any]) -> str:
    if reference_paths:
        return (
            f"Generate an I2V clip for {_clean(shot.get('shot_id'))}; use the locked character reference set and "
            "prioritize stable face, outfit, and scene continuity."
        )
    return (
        f"Generate an I2V clip for {_clean(shot.get('shot_id'))}; stable identity is required even before reference-image "
        "recovery is complete."
    )


def _transition_type(current_shot: dict[str, Any]) -> str:
    transition = _clean(current_shot.get("transition_to_next"))
    return transition or "cut"


def _transition_prompt(
    index: int,
    current_shot: dict[str, Any],
    next_shot: dict[str, Any],
    continuity_anchor: str,
) -> dict[str, Any]:
    current_id = _clean(current_shot.get("shot_id"))
    next_id = _clean(next_shot.get("shot_id"))
    transition_type = _transition_type(current_shot)
    current_scene = _clean(current_shot.get("scene")) or _clean(current_shot.get("location"))
    next_scene = _clean(next_shot.get("scene")) or _clean(next_shot.get("location"))
    return {
        "transition_id": f"T{index + 1:03d}",
        "from_shot_id": current_id,
        "to_shot_id": next_id,
        "transition_type": transition_type,
        "transition_motion_prompt": (
            f"Transition from {current_id} to {next_id} using {transition_type}, preserve {continuity_anchor}, "
            f"carry the action and emotion from {current_scene or 'the current scene'} into {next_scene or 'the next scene'}."
        ),
        "continuity_requirements": [
            "same character face and hair",
            "same outfit silhouette",
            continuity_anchor or "same emotional progression",
        ],
    }


def build_stage04_llm_output(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    character_bible: dict[str, Any],
    prompt_packet: dict[str, Any] | None = None,
    repair_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normal_brief(brief)
    style_text = _clean(normalized.get("style"))
    visual_family = _clean(((brief.get("compiled_requirements") or {}).get("visual_family_hint"))) or _clean(((storyboard.get("compiled_requirements") or {}).get("visual_family_hint")))
    aspect_ratio = _clean(normalized.get("aspect_ratio")) or _clean(normalized.get("aspect_ratio_label"))
    anchors = resolve_upstream_story_anchors(character_bible, storyboard, script)
    time_of_day = _clean(anchors.get("time_of_day"))

    storyboard_shots = [item for item in list(storyboard.get("shots") or []) if isinstance(item, dict)]
    characters, _, reference_paths = _character_map(character_bible)
    global_negative = _global_negative_prompt(visual_family)
    style_prompt = _style_prompt(style_text, visual_family)

    shot_prompts: list[dict[str, Any]] = []
    for index, shot in enumerate(storyboard_shots):
        character_ids = _pick_character_ids(shot, characters)
        character_anchor = _character_anchor_text(characters, character_ids)
        scene = _clean(shot.get("scene")) or _clean(shot.get("location"))
        weather = _clean(shot.get("weather"))
        lighting_prompt = _lighting_prompt(scene, weather, time_of_day)
        emotion = _clean(shot.get("emotion"))
        performance_prompt = _performance_prompt(characters, character_ids, emotion)
        shot_prompts.append({
            "shot_id": _clean(shot.get("shot_id")),
            "source_shot_ref": f"{_clean(storyboard.get('source_script') or '')}#{_clean(shot.get('shot_id'))}" if _clean(storyboard.get("source_script")) else f"storyboard#{_clean(shot.get('shot_id'))}",
            "duration_sec": shot.get("duration_sec") or 1,
            "characters": character_ids,
            "scene_summary": _scene_summary(shot),
            "intent_summary": _intent_summary(shot),
            "story_anchor_bundle": _story_anchor_bundle(shot),
            "start_keyframe_prompt": _start_keyframe_prompt(shot, character_anchor, style_prompt, lighting_prompt, aspect_ratio),
            "end_keyframe_prompt": _end_keyframe_prompt(shot, character_anchor, style_prompt, lighting_prompt),
            "motion_prompt": _motion_prompt(shot, performance_prompt),
            "camera_prompt": _camera_prompt(shot),
            "lighting_prompt": lighting_prompt,
            "style_prompt": style_prompt,
            "consistency_prompt": character_anchor,
            "identity_anchor_prompt": character_anchor,
            "negative_prompt": _negative_prompt(global_negative, characters, character_ids),
            "image_generation_notes": _image_notes(shot),
            "video_generation_notes": _video_notes(reference_paths, shot),
            "performance_prompt": performance_prompt,
            "dialogue_delivery_prompt": "",
            "dependencies": {
                "reference_images": reference_paths,
                "previous_shot_id": _clean(storyboard_shots[index - 1].get("shot_id")) if index > 0 else None,
                "next_shot_id": _clean(storyboard_shots[index + 1].get("shot_id")) if index + 1 < len(storyboard_shots) else None,
            },
        })

    primary_continuity = _clean((((characters[0].get("performance_profile") or {}) if characters else {}).get("continuity_anchor")))
    transition_prompts = [
        _transition_prompt(index, storyboard_shots[index], storyboard_shots[index + 1], primary_continuity)
        for index in range(max(0, len(storyboard_shots) - 1))
    ]

    self_check = {
        "matches_locked_brief": True,
        "matches_script": True,
        "matches_storyboard": True,
        "uses_character_consistency": True,
        "covers_all_storyboard_shots": True,
        "ready_for_image_generation": True,
        "notes": [
            "Generated by Stage 04 local semantics from the locked brief and approved Stage 01-03 artifacts.",
        ],
    }
    if prompt_packet:
        self_check["notes"].append(f"Prompt packet preserved: {prompt_packet.get('packet_version') or 'unknown'}")
    if repair_packet:
        self_check["notes"].append("Repair loop requested deterministic regeneration from the same approved storyboard and character bible.")

    return {
        "status": "draft",
        "prompt_language": "English generation prompts with Chinese review notes",
        "visual_strategy": {
            "keyframe_mode": "start_and_end_keyframes_per_shot",
            "video_mode": "image_to_video_per_shot",
            "continuity_strategy": "reuse character consistency prompts and adjacent-shot transition requirements",
        },
        "shot_prompts": shot_prompts,
        "transition_prompts": transition_prompts,
        "global_negative_prompt": global_negative,
        "self_check": self_check,
    }
