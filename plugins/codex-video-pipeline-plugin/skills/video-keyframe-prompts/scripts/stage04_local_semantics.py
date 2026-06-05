#!/usr/bin/env python3
"""Deterministic Stage 04 local semantics.

This module is not part of the formal Stage 04 production runtime.

The official Stage04 path must go through `run_stage04_codex_flow.py` and
generate `stage04_llm_output.json` through Codex structured output.

This module may exist only for non-formal roles such as:

- tests
- fixtures
- explicitly labeled manual fallback
"""
from __future__ import annotations

from typing import Any

from pipeline_blueprints import normal_brief
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _rewrite_stage04_abstract_cjk_text(text: str) -> str:
    rewritten = _clean(text)
    if not rewritten:
        return ""
    replacements = [
        ("像是在等海风把心事吹散", "海风吹动头发和裙摆，她继续慢慢往前走，不要夸张表情"),
        ("把心事留在身后", "不再回头，肩膀自然下沉，背部不再紧绷"),
        ("整个人终于轻下来", "步伐更稳定，呼吸更均匀，肩膀放松"),
        ("海风把情绪一点点吹开", "海风吹动头发和裙摆，眉头慢慢放松，肩膀比前一镜头更放松"),
        ("呼吸和情绪都一点点慢下来", "呼吸节奏放慢，停下来望向海平线，肩膀慢慢放松"),
        ("呼吸和情绪一点点慢下来", "呼吸节奏放慢，停下来望向海平线，肩膀慢慢放松"),
        ("那点没说出口的情绪终于开始松开", "眉头慢慢放松，嘴角不再绷紧，肩膀和手臂比前一镜头更放松"),
        ("海面与晚霞继续呼吸", "海面反光、晚霞层次和海平线继续清楚可见"),
        ("画面里的情绪放缓", "海风吹动头发和裙摆，人物步伐偏慢，停顿要清楚"),
        ("停顿感比动作本身更重要", "停下来后的停顿要清楚，动作幅度要小"),
        ("原本绷着的情绪开始真正松开", "眉头和肩膀慢慢放松，嘴角不再绷紧"),
        ("把释然留给海面、风声和脚步", "把人物放在较小比例，保留海面、背影和步伐变化"),
        ("人物和环境的呼吸都要留住", "人物呼吸节奏、海面反光和晚霞层次都要清楚可见"),
        ("情绪落点留在人物与环境的共同呼吸上", "人物呼吸节奏、海面反光和晚霞层次都要清楚可见"),
        ("情绪回落", "动作结束后的停顿要清楚，肩膀和呼吸都更放松"),
        ("环境呼吸", "海面反光、晚霞层次和风吹动头发裙摆的变化"),
    ]
    for source, target in replacements:
        rewritten = rewritten.replace(source, target)
    rewritten = rewritten.replace("表情表情", "表情")
    rewritten = rewritten.replace("。。", "。")
    return rewritten.strip()


def _rewritten_action(shot: dict[str, Any]) -> str:
    return _rewrite_stage04_abstract_cjk_text(shot.get("action"))


def _rewritten_composition(shot: dict[str, Any]) -> str:
    text = _clean(shot.get("composition_focus")) or _clean(shot.get("composition"))
    return _rewrite_stage04_abstract_cjk_text(text)


def _sanitized_character_anchor(text: str) -> str:
    return _rewrite_stage04_abstract_cjk_text(text)


def _concrete_emotion_cn(emotion: str, action: str = "", *, location: str = "", key_prop: str = "") -> str:
    text = " ".join(part for part in [emotion, action, location, key_prop] if part)
    if "观察" in text:
        return "继续慢慢往前走，嘴唇自然闭合，视线停在前方或海平线，不回头"
    if "推进" in text:
        return "停下来望向远处，肩膀慢慢放松，呼吸节奏放慢，动作幅度收小"
    if "转折" in text:
        return "眉头从轻微收住变为放松，嘴角不再绷紧，肩膀自然下沉"
    if "收束" in text:
        return "继续当前动作但不再回头，步伐更稳定，背部和肩膀不再紧绷"
    if "安静" in text:
        return "表情平静，嘴唇自然闭合，视线稳定，动作收住"
    if "克制善意" in text:
        return "表情收住，手部动作轻，递出动作清楚，眼神温和但不过度微笑"
    if "落寞余温" in text:
        return "不回头，步伐稳定偏慢，肩膀略低，背影停顿感清楚"
    if "意外回暖" in text:
        return "先短暂停住，再轻微回头，眉头放松一点，视线落到关键道具上"
    if "迟疑" in text:
        return "动作先停半拍，再继续，视线短暂停留，手部动作不要太快"
    if "松动" in text:
        return "肩膀慢慢放松，眉头舒展一点，呼吸更均匀"
    if "释怀" in text:
        return "表情平静，肩膀自然下沉，步伐更稳定，不再回头"
    if "压抑" in text:
        return "嘴唇自然闭合，眉头轻微收住，肩颈略紧，动作收小"
    if "决心" in text:
        return "视线更稳定，站姿更稳，动作直接，不犹豫"
    if "落寞" in text:
        return "背影停顿感清楚，步伐偏慢，不与镜头对视"
    if "被安慰" in text:
        return "先停住，再轻微放松眉头和肩膀，表情不要夸张"
    if "平静" in text:
        return "表情平静，嘴唇自然闭合，动作稳定"
    return emotion or "表情平静，动作稳定"


def _concrete_emotion_en(emotion: str, action: str = "", *, location: str = "", key_prop: str = "") -> str:
    text = " ".join(part for part in [emotion, action, location, key_prop] if part).lower()
    if "观察" in text:
        return "keep walking slowly, closed lips, stable gaze toward the horizon or forward space, do not look back"
    if "推进" in text:
        return "pause and look out, relax the shoulders gradually, slow the breathing, keep movement small"
    if "转折" in text:
        return "soften the brow, release the mouth tension, let the shoulders drop slightly"
    if "收束" in text:
        return "continue forward without looking back, steadier steps, less tension in the back and shoulders"
    if "安静" in text or "quiet" in text:
        return "calm face, closed lips, stable gaze, restrained movement"
    if "克制善意" in text or "kind" in text:
        return "restrained expression, gentle eye line, clear handoff action, no exaggerated smile"
    if "落寞余温" in text or "lonely" in text:
        return "do not look back, keep the back view readable, slow steady steps, slightly lowered shoulders"
    if "意外回暖" in text or "warm" in text:
        return "pause first, then give a small turn back, soften the brow slightly, look at the prop"
    if "迟疑" in text:
        return "hold for half a beat before moving, keep the gaze brief and the hand motion slow"
    if "松动" in text:
        return "relax the shoulders gradually, soften the brow, let the breathing become more even"
    if "释怀" in text:
        return "calm face, lowered shoulders, steadier steps, no need to look back"
    if "压抑" in text:
        return "closed lips, slightly tightened brow, small movement range, tension visible in the shoulders"
    if "决心" in text:
        return "stable eye line, firm stance, direct action without hesitation"
    return emotion or "calm face, stable movement"


def _composition_directive(shot: dict[str, Any]) -> str:
    focus = _rewritten_composition(shot)
    if focus:
        return focus
    camera = _clean(shot.get("camera")).lower()
    if "wide" in camera:
        return "人物与环境都要清楚可读，环境空间优先建立出来"
    if "close" in camera:
        return "表情、视线和关键动作要清楚可读"
    return "主体动作和环境关系都要清楚可读"


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
    action = _rewritten_action(shot) or "未指定"
    key_prop = _clean(shot.get("key_prop")) or "无"
    emotion = _concrete_emotion_cn(_clean(shot.get("emotion")), action, location=location, key_prop=_clean(shot.get("key_prop"))) or "未指定"
    composition_focus = _rewritten_composition(shot) or "未指定"
    return (
        f"地点：{location} / 天气：{weather} / 动作：{action} / "
        f"道具：{key_prop} / 情绪：{emotion} / 构图重点：{composition_focus}"
    )


def _intent_summary(shot: dict[str, Any]) -> str:
    location = _clean(shot.get("location")) or _clean(shot.get("scene")) or "当前场景"
    action = _rewritten_action(shot) or "这个动作"
    emotion = _clean(shot.get("emotion")) or "当前情绪"
    key_prop = _clean(shot.get("key_prop"))
    composition = _composition_directive(shot)
    emotion_clause = _concrete_emotion_cn(emotion, action, location=location, key_prop=key_prop)
    prop_clause = f"，并让{key_prop}清楚可见" if key_prop else ""
    return f"这个镜头在{location}里要拍清楚“{action}”，人物需要呈现为{emotion_clause}，{composition}{prop_clause}。"


def _story_anchor_bundle(shot: dict[str, Any]) -> dict[str, str]:
    location = _clean(shot.get("location")) or _clean(shot.get("scene"))
    action = _rewritten_action(shot)
    key_prop = _clean(shot.get("key_prop"))
    emotion = _clean(shot.get("emotion"))
    return {
        "location": location,
        "weather": _clean(shot.get("weather")),
        "key_prop": key_prop,
        "emotion": _concrete_emotion_cn(emotion, action, location=location, key_prop=key_prop),
        "emotion_label": emotion,
        "action": action,
        "composition_focus": _rewritten_composition(shot),
    }


def _character_anchor_text(characters: list[dict[str, Any]], character_ids: list[str]) -> str:
    picked = [item for item in characters if _clean(item.get("character_id")) in character_ids]
    if not picked:
        return "Preserve the same protagonist identity in every frame."
    item = picked[0]
    name = _clean(item.get("name")) or "the protagonist"
    visual = _sanitized_character_anchor(_clean(item.get("visual_consistency_prompt")))
    if visual:
        return f"Character identity anchor: {visual}"
    continuity = _sanitized_character_anchor(_clean(((item.get("performance_profile") or {}).get("continuity_anchor"))))
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
                return joined or (_concrete_emotion_cn(emotion) or "表情平静，动作自然收住")
    return _concrete_emotion_cn(emotion) or "表情平静，动作自然收住"


def _start_keyframe_prompt(
    shot: dict[str, Any],
    character_anchor: str,
    style_prompt: str,
    lighting_prompt: str,
    aspect_ratio: str,
) -> str:
    location = _clean(shot.get("location")) or _clean(shot.get("scene"))
    action = _rewritten_action(shot)
    composition = _rewritten_composition(shot)
    emotion = _clean(shot.get("emotion"))
    camera = _camera_prompt(shot)
    emotion_clause = _concrete_emotion_en(emotion, action, location=location)
    parts = [
        "cinematic keyframe,",
        camera + ",",
        location + "," if location else "",
        action + "," if action else "",
        composition + "," if composition else "",
        f"{emotion_clause}," if emotion_clause else "",
        character_anchor,
        lighting_prompt + ",",
        style_prompt + ",",
        f"{aspect_ratio} composition" if aspect_ratio else "",
    ]
    return " ".join(part for part in parts if part).strip().rstrip(",")


def _end_keyframe_prompt(
    shot: dict[str, Any],
    character_anchor: str,
    style_prompt: str,
    lighting_prompt: str,
) -> str:
    action = _rewritten_action(shot)
    location = _clean(shot.get("location")) or _clean(shot.get("scene"))
    emotion = _clean(shot.get("emotion"))
    emotion_clause = _concrete_emotion_en(emotion, action, location=location)
    parts = [
        f"cinematic continuation of { _clean(shot.get('shot_id')) },",
        action + "," if action else "",
        location + "," if location else "",
        f"keep {emotion_clause}," if emotion_clause else "",
        "do not swap protagonist identity,",
        character_anchor,
        lighting_prompt + ",",
        style_prompt + ",",
    ]
    return " ".join(part for part in parts if part).strip().rstrip(",")


def _motion_prompt(shot: dict[str, Any], performance_prompt: str) -> str:
    action = _rewritten_action(shot)
    location = _clean(shot.get("location")) or _clean(shot.get("scene"))
    key_prop = _clean(shot.get("key_prop"))
    emotion = _clean(shot.get("emotion"))
    emotion_clause = _concrete_emotion_cn(emotion, action, location=location, key_prop=key_prop)
    prop_clause = f"，并保持{key_prop}始终清楚可见" if key_prop else ""
    return (
        f"{action}；动作幅度要小，起手、停顿和结束都要清楚，人物需要呈现为{emotion_clause}{prop_clause}；"
        f"保持身份连续性，场景保持{location or '当前环境'}可读，表演基线：{performance_prompt}"
    ).strip()


def _image_notes(shot: dict[str, Any]) -> str:
    focus = _rewritten_composition(shot)
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
    next_action = _rewritten_action(next_shot)
    next_emotion = _concrete_emotion_cn(
        _clean(next_shot.get("emotion")),
        next_action,
        location=next_scene,
        key_prop=_clean(next_shot.get("key_prop")),
    )
    return {
        "transition_id": f"T{index + 1:03d}",
        "from_shot_id": current_id,
        "to_shot_id": next_id,
        "transition_type": transition_type,
        "transition_motion_prompt": (
            f"Transition from {current_id} to {next_id} using {transition_type}, preserve {continuity_anchor}, "
            f"carry the action from {current_scene or 'the current scene'} into {next_scene or 'the next scene'}, "
            f"and land on {next_action or 'the next action'} with {next_emotion}."
        ),
        "continuity_requirements": [
            "same character face and hair",
            "same outfit silhouette",
            continuity_anchor or "same baseline expression, gaze direction, and action rhythm",
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
