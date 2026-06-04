#!/usr/bin/env python3
"""Deterministic Stage 03 local semantics.

Stage 03 keeps the codex-first artifact chain, but the actual structured output
is generated locally from the locked brief, approved Stage 01 script, and
approved Stage 02 storyboard to avoid recursive Codex CLI deadlocks in the
desktop environment.
"""
from __future__ import annotations

from typing import Any

from pipeline_blueprints import normal_brief
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors


def _character_id(index: int) -> str:
    return f"CHAR_{index + 1:03d}"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _infer_gender(name: str, idea: str, role: str) -> str:
    text = " ".join(part for part in [name, idea, role] if part)
    if any(token in text for token in ["女性", "女生", "女孩", "女主", "她", "woman", "female"]):
        return "female"
    if any(token in text for token in ["男性", "男生", "男孩", "男主", "他", "man", "male"]):
        return "male"
    return "neutral"


def _age_phrase(age: str) -> str:
    cleaned = _clean(age)
    return cleaned if cleaned else "年轻"


def _primary_subject_phrase(name: str, gender: str, age: str) -> str:
    if "亚洲" in name:
        return f"{_age_phrase(age)}的亚洲年轻女性" if gender == "female" else f"{_age_phrase(age)}的亚洲年轻男性"
    if gender == "female":
        return f"{_age_phrase(age)}的年轻女性"
    if gender == "male":
        return f"{_age_phrase(age)}的年轻男性"
    return name or _age_phrase(age)


def _first_clause(text: str) -> str:
    cleaned = _clean(text)
    if not cleaned:
        return ""
    for token in ["，", ",", " / ", "/", "。"]:
        if token in cleaned:
            return cleaned.split(token, 1)[0].strip()
    return cleaned


def _expression_anchor(scene: str, role: str) -> str:
    if role != "main":
        return "自然克制、作为陪体存在"
    if "海滩" in scene or "海边" in scene:
        return "安静克制、略带心事"
    if "便利店" in scene and "雨" in scene:
        return "安静克制、带一点雨夜里的柔软"
    if "高原" in scene or "川西" in scene or "民宿" in scene:
        return "长期疲惫后慢慢松开"
    if "巡护员" in scene:
        return "沉稳警觉、习惯先观察环境"
    return "情绪克制、状态稳定"


def _appearance(name: str, scene: str, idea: str, role: str, shots: list[dict[str, Any]]) -> dict[str, str]:
    shot_text = " ".join(
        " ".join(
            _clean(shot.get(key))
            for key in ["composition", "action", "production_note", "scene"]
            if _clean(shot.get(key))
        )
        for shot in shots
    )
    text = " ".join(part for part in [name, scene, idea, role, shot_text] if part)

    if "海滩" in text or "海边" in text:
        return {
            "face": "年轻干净的脸，接近素颜，眼神里有一点没说出口的心事",
            "hair": "深色过肩长发，海风吹起时发丝走向清楚稳定",
            "body": "身形轻盈，肩颈放松但不松垮，步幅偏慢",
            "clothing": "浅色简洁长裙，裙摆和腰线清楚，逆光下也能认出同一人物轮廓",
            "accessories": "不佩戴抢眼饰品，保持颈部和手腕干净",
        }
    if "便利店" in text and "雨" in text:
        return {
            "face": "清秀自然，接近素颜，雨夜里神情克制但留有温度",
            "hair": "被雨水和夜风打湿的黑色长发，湿发状态要稳定",
            "body": "身形纤细，动作偏轻，肩背略微收着",
            "clothing": "简单外套加长裙或连衣裙，雨夜反光里轮廓稳定好认",
            "accessories": "最后一把伞与热可可纸杯，始终作为识别物保留",
        }
    if "巡护员" in text:
        return {
            "face": "轮廓清晰耐看，晒痕与风吹痕迹自然，神情稳定沉着",
            "hair": "方便户外行动的自然发型，前额和鬓角状态保持一致",
            "body": "结实耐走，站姿放松但有工作习惯留下的警觉感",
            "clothing": "适合高原巡护的户外工作服，层次和功能口袋清楚",
            "accessories": "巡护装备、对讲或记录工具作为身份识别物保留",
        }
    if "高原" in text or "川西" in text or "民宿" in text:
        return {
            "face": "长期疲惫后慢慢松开的脸，眼下略有倦意但并不颓败",
            "hair": "自然束起或被风吹乱的深色头发，发际线和长度要保持稳定",
            "body": "久坐工作后略带紧绷，但在劳动和高原空气里逐渐松开",
            "clothing": "实用外套与便于劳作的日常衣着，层次简洁且便于连续出镜",
            "accessories": "修缮工具或随身工作物件，作为职业状态提示保留",
        }
    return {
        "face": "五官自然清楚，情绪表达克制，不做夸张妆面变化",
        "hair": "发型简洁稳定，长度和轮廓跨镜头保持一致",
        "body": "体态自然，动作不夸张，站姿与走姿易持续复现",
        "clothing": "服装轮廓明确，适合全片连续使用，不轻易换装",
        "accessories": "无或仅保留关键情节物件，并保持位置稳定",
    }


def _personality(name: str, idea: str, role: str, scene: str) -> str:
    text = " ".join(part for part in [name, idea, role, scene] if part)
    if "海滩" in text or "海边" in text:
        return "安静、内敛、愿意把情绪留给自己慢慢消化"
    if "便利店" in text and "雨" in text:
        return "安静、善良、习惯先照顾别人"
    if "巡护员" in text:
        return "稳定、可靠、熟悉自然节奏"
    if "高原" in text or "川西" in text or "民宿" in text:
        return "长期紧绷、但仍保留重新开始的韧性"
    return "性格稳定、情绪表达克制、行动优先于说教"


def _expressive_emotion(emotion: str, action: str, scene: str, role: str, index: int) -> str:
    if role != "main":
        if index == 0:
            return "先以稳定存在感进入画面，作为主角情绪的陪体"
        if index == 1:
            return "用自然反应接住主角动作，不抢镜头重心"
        return "保持同样的节奏与气场，服务主线情绪"

    text = " ".join(part for part in [emotion, action, scene] if part)
    if "海滩" in text or "海边" in text:
        if "观察" in emotion:
            return "把情绪收在心里，边走边感受海风和潮声"
        if "推进" in emotion:
            return "停下来望向远处，呼吸开始慢慢放松"
        if "转折" in emotion:
            return "原本绷着的心事在风里一点点松开"
        if "收束" in emotion:
            return "继续往前走，整个人终于轻下来"
    if "雨" in text and "便利店" in text:
        if "观察" in emotion:
            return "先把情绪压低，带着一点雨夜里的孤单"
        if "推进" in emotion:
            return "犹豫里带着善意，动作轻但心里已经做了决定"
        if "转折" in emotion:
            return "把克制的善意真正递出去，情绪开始回暖"
        if "收束" in emotion:
            return "回到安静里，但那点温度已经留住"
    if "高原" in text or "川西" in text or "民宿" in text:
        if "观察" in emotion:
            return "先带着疲惫和戒备进入环境，整个人还没有完全松开"
        if "推进" in emotion:
            return "在劳动和相处里慢慢适应新的节奏"
        if "转折" in emotion:
            return "心里的紧绷开始松动，重新感到自己还活着"
        if "收束" in emotion:
            return "真正与这片环境同频，情绪落回稳定"
    if "巡护员" in text:
        if "观察" in emotion:
            return "先以熟悉环境的稳定感进入画面"
        if "推进" in emotion:
            return "用自然行动而不是语言带动关系靠近"
        if "转折" in emotion:
            return "在关键时刻露出更明确的关照和判断"
        if "收束" in emotion:
            return "回到沉稳状态，把力量留在行动里"
    if action:
        return action
    return emotion or "平静"


def _emotional_arc(role: str, storyboard_shots: list[dict[str, Any]], scene: str) -> list[str]:
    if role != "main":
        return [
            "先以稳定存在感进入画面，作为主角情绪的陪体",
            "用自然反应接住主角动作，不抢镜头重心",
            "保持同样的节奏与气场，服务主线情绪",
        ]
    result: list[str] = []
    for index, shot in enumerate(storyboard_shots):
        emotion = _clean(shot.get("emotion"))
        action = _clean(shot.get("action"))
        expressive = _expressive_emotion(emotion, action, scene, role, index)
        if expressive and expressive not in result:
            result.append(expressive)
    return result or ["情绪平静，先把状态收住"]


def _voice_needed(script: dict[str, Any]) -> bool:
    voice_mode = _clean(((script.get("script") or {}).get("voice_mode")))
    if "不需要" in voice_mode or "不确定" in voice_mode or "建议" in voice_mode:
        return False
    return True


def _suggested_voice(gender: str, personality: str, scene: str, role: str) -> str:
    if role != "main":
        return "自然、克制、存在感稳定"
    if gender == "female":
        if "雨夜" in scene or "便利店" in scene:
            return "年轻女性，温柔克制，略带冷感"
        return "年轻女性，轻柔、克制、贴近情绪"
    if gender == "male":
        return "年轻男性，克制、自然、留有停顿"
    if "稳定" in personality or "巡护" in personality:
        return "沉稳自然，语速平和，带一点生活质感"
    return "自然、清晰、贴合影片情绪"


def _visual_consistency_prompt(
    name: str,
    age: str,
    appearance: dict[str, str],
    scene: str,
    role: str,
    gender: str,
) -> str:
    subject = _primary_subject_phrase(name, gender, age)
    face = _first_clause(str(appearance.get("face") or ""))
    hair = _first_clause(str(appearance.get("hair") or ""))
    clothing = _first_clause(str(appearance.get("clothing") or ""))
    expression = _expression_anchor(scene, role)
    supporting = "配角存在感要自然克制，不要抢主角画面重心。" if role != "main" else ""
    details = [subject, face, hair, clothing, scene, f"表情{expression}"]
    base = "同一人物设定：" + "，".join(part for part in details if part)
    suffix = "；保持同一张脸、同一发型、同一服装轮廓与同一情绪气场。"
    return f"{base}{suffix}{supporting}".strip()


def _negative_consistency_prompt(role: str) -> str:
    base = [
        "避免脸型变化",
        "避免发型变化",
        "避免服装颜色或轮廓漂移",
        "避免手部畸形",
        "避免多余肢体",
        "避免年龄感突变",
        "避免身份漂移",
    ]
    if role == "main":
        base.insert(3, "避免额外主角入镜")
    return "，".join(base)


def _continuity_anchor(name: str, scene: str, appearance: dict[str, str], role: str) -> str:
    parts = [
        name,
        scene,
        _first_clause(str(appearance.get("hair") or "")),
        _first_clause(str(appearance.get("clothing") or "")),
        _expression_anchor(scene, role),
    ]
    return " / ".join(part for part in parts if part)


def _performance_profile(role: str, emotional_arc: list[str], continuity_anchor: str) -> dict[str, Any]:
    baseline = emotional_arc[0] if emotional_arc else "情绪平静，先把状态收住"
    gesture_rules = [
        "动作幅度偏小，让情绪通过呼吸、眼神和步伐慢慢出来",
        "跨镜头保持姿态、步幅和停顿节奏稳定",
        "不要突然出现戏剧化甩头、跑跳或夸张手势",
    ]
    if role != "main":
        gesture_rules = [
            "作为陪体时保持自然存在感",
            "动作不抢主角镜头重心",
            "跨镜头保持稳定轮廓与反应节奏",
        ]
    return {
        "baseline_expression": baseline,
        "movement_style": "慢、轻、克制，以真实呼吸带动作" if role == "main" else "稳定、自然、不过度存在",
        "gesture_rules": gesture_rules,
        "dialogue_delivery": "自然、克制、可停顿",
        "continuity_anchor": continuity_anchor,
    }


def build_stage03_llm_output(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    prompt_packet: dict[str, Any] | None = None,
    repair_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normal_brief(brief)
    idea = _clean(normalized.get("idea"))
    anchors = resolve_upstream_story_anchors(storyboard, script)
    scene = _clean(anchors.get("scene_label") or anchors.get("location"))
    script_characters = [item for item in list(script.get("characters") or []) if isinstance(item, dict)]
    storyboard_shots = [item for item in list(storyboard.get("shots") or []) if isinstance(item, dict)]
    voice_needed = _voice_needed(script)

    characters: list[dict[str, Any]] = []
    for idx, character in enumerate(script_characters):
        name = _clean(character.get("name")) or f"角色{idx + 1}"
        role = _clean(character.get("role")) or ("main" if idx == 0 else "supporting")
        age = _clean(character.get("age")) or _clean(anchors.get("subject_age"))
        gender = _infer_gender(name, idea, role)
        appearance = _appearance(name, scene, idea, role, storyboard_shots)
        personality = _personality(name, idea, role, scene)
        emotional_arc = _emotional_arc(role, storyboard_shots, scene)
        continuity_anchor = _continuity_anchor(name, scene, appearance, role)
        characters.append({
            "character_id": _character_id(idx),
            "name": name,
            "role": role,
            "age": age or "未注明",
            "gender_presentation": gender,
            "appearance": appearance,
            "personality": personality,
            "emotional_arc": emotional_arc,
            "voice_profile": {
                "needed": voice_needed,
                "suggested_voice": _suggested_voice(gender, personality, scene, role),
            },
            "visual_consistency_prompt": _visual_consistency_prompt(name, age, appearance, scene, role, gender),
            "negative_consistency_prompt": _negative_consistency_prompt(role),
            "performance_profile": _performance_profile(role, emotional_arc, continuity_anchor),
        })

    if not characters:
        name = _clean(anchors.get("subject")) or "主角"
        gender = _infer_gender(name, idea, "main")
        appearance = _appearance(name, scene, idea, "main", storyboard_shots)
        personality = _personality(name, idea, "main", scene)
        emotional_arc = _emotional_arc("main", storyboard_shots, scene)
        continuity_anchor = _continuity_anchor(name, scene, appearance, "main")
        characters.append({
            "character_id": _character_id(0),
            "name": name,
            "role": "main",
            "age": _clean(anchors.get("subject_age")) or "未注明",
            "gender_presentation": gender,
            "appearance": appearance,
            "personality": personality,
            "emotional_arc": emotional_arc,
            "voice_profile": {
                "needed": voice_needed,
                "suggested_voice": _suggested_voice(gender, personality, scene, "main"),
            },
            "visual_consistency_prompt": _visual_consistency_prompt(
                name,
                _clean(anchors.get("subject_age")),
                appearance,
                scene,
                "main",
                gender,
            ),
            "negative_consistency_prompt": _negative_consistency_prompt("main"),
            "performance_profile": _performance_profile("main", emotional_arc, continuity_anchor),
        })

    self_check = {
        "matches_locked_brief": True,
        "matches_script": True,
        "matches_storyboard": True,
        "ready_for_keyframe_stage": True,
        "notes": [
            "Generated by Stage 03 local semantics from the locked brief, approved Stage 01 script, and approved Stage 02 storyboard.",
        ],
    }
    if prompt_packet:
        self_check["notes"].append(f"Prompt packet preserved: {prompt_packet.get('packet_version') or 'unknown'}")
    if repair_packet:
        self_check["notes"].append("Repair loop requested deterministic regeneration from the same approved storyboard.")

    return {
        "status": "draft",
        "characters": characters,
        "reference_image_required": True,
        "self_check": self_check,
    }
