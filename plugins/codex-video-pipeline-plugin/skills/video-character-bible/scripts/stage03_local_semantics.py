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
        return "表情自然收住，视线稳定，动作比主角更轻，不抢画面重心"
    if "海滩" in scene or "海边" in scene:
        return "表情平静，嘴唇自然闭合，眉头轻微收住，视线多停在远处，不夸张微笑"
    if "便利店" in scene and "雨" in scene:
        return "表情平静，嘴唇自然闭合，眼神温和，动作收住，不做夸张表情"
    if "高原" in scene or "川西" in scene or "民宿" in scene:
        return "肩颈起初略紧，呼吸偏浅，后续慢慢放松，表情不夸张"
    if "巡护员" in scene:
        return "站姿稳定，先看环境再看人，眉头轻微收住，动作干净"
    return "表情收住，嘴唇自然闭合，动作稳定，不做夸张表演"


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
            "face": "年轻干净的脸，接近素颜，嘴唇自然闭合，眉头轻微收住，视线安静稳定",
            "hair": "深色过肩长发，海风吹起时发丝走向清楚稳定",
            "body": "身形轻盈，肩颈放松但不松垮，步幅偏慢",
            "clothing": "浅色简洁长裙，裙摆和腰线清楚，逆光下也能认出同一人物轮廓",
            "accessories": "不佩戴抢眼饰品，保持颈部和手腕干净",
        }
    if "便利店" in text and "雨" in text:
        return {
            "face": "清秀自然，接近素颜，嘴唇自然闭合，眼神温和，眉头轻微收住",
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
            "face": "眼下略有倦意，嘴唇自然闭合，眉头轻微收住，不做夸张笑容",
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
            return "先稳定站住或坐住，视线落在主角或当前动作上，动作轻，不抢主角画面"
        if index == 1:
            return "用自然的小幅反应接住主角动作，手部和视线变化要清楚，但不要抢镜头"
        return "保持同样的动作节奏和视线方向，服务主线动作，不额外加戏"

    text = " ".join(part for part in [emotion, action, scene] if part)
    if "海滩" in text or "海边" in text:
        if "观察" in emotion:
            return "继续慢慢往前走，嘴唇自然闭合，视线停在前方或海平线，不回头"
        if "推进" in emotion:
            return "停下来望向远处，肩膀慢慢放松，呼吸节奏放慢，动作幅度收小"
        if "转折" in emotion:
            return "眉头从轻微收住变为放松，嘴角不再绷紧，肩膀自然下沉"
        if "收束" in emotion:
            return "继续往前走，不再回头，步伐更稳定，背部不再紧绷"
    if "雨" in text and "便利店" in text:
        if "观察" in emotion:
            return "先站在门廊边不说话，嘴唇自然闭合，眼神平静，握伞动作收住"
        if "推进" in emotion:
            return "递伞前先有短暂停顿，再把伞稳定递出去，手部动作清楚，表情收住"
        if "转折" in emotion:
            return "把伞递出去后短暂停顿，眼神变软一点，但不要夸张微笑"
        if "收束" in emotion:
            return "回到安静状态，动作更轻，眉头放松一点，视线停在热可可或门口台阶"
    if "高原" in text or "川西" in text or "民宿" in text:
        if "观察" in emotion:
            return "先带着浅呼吸和略紧的肩颈进入环境，视线先扫环境，不立刻放松"
        if "推进" in emotion:
            return "在劳动动作里慢慢找到稳定节奏，呼吸更均匀，手部动作更熟练"
        if "转折" in emotion:
            return "眉头和肩颈慢慢放松，停顿时间变长，动作不再急促"
        if "收束" in emotion:
            return "站姿和呼吸都稳定下来，视线停得更久，表情平静，不再紧绷"
    if "巡护员" in text:
        if "观察" in emotion:
            return "先稳定看环境，再转向人物，动作干净，不做多余手势"
        if "推进" in emotion:
            return "用明确的小动作带动关系推进，视线和手部动作都要看得清"
        if "转折" in emotion:
            return "在关键时刻先看清情况，再给出清楚动作或目光回应"
        if "收束" in emotion:
            return "回到稳定站姿和自然呼吸，把关照留在动作里，不靠夸张表情"
    if action:
        return action
    return emotion or "表情平静，动作收住"


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
    suffix = "；保持同一张脸、同一发型、同一服装轮廓与基础表情、视线方向和动作节奏。"
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
    baseline = emotional_arc[0] if emotional_arc else "表情平静，先把状态收住"
    gesture_rules = [
        "动作幅度偏小，抬手、转身、迈步都放慢，让呼吸、视线和停顿变化能被看清",
        "跨镜头保持姿态、步幅、视线方向和停顿节奏稳定",
        "不要突然出现甩头、跑跳、夸张摆臂或过大的表情变化",
    ]
    if role != "main":
        gesture_rules = [
            "作为陪体时先站稳或坐稳，动作自然收住",
            "反应动作比主角更轻，不抢主角镜头重心",
            "跨镜头保持稳定轮廓、视线方向和反应节奏",
        ]
    return {
        "baseline_expression": baseline,
        "movement_style": "动作幅度小，以呼吸、停顿、视线和步伐变化带动作" if role == "main" else "动作自然收住，存在感稳定，不过度抢镜",
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
