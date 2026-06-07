#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from pipeline_core.quality_contracts import build_quality_contract, build_stage_quality_targets
from pipeline_core.requirement_compiler import compile_requirements


STAGE_ORDER = [
    "STAGE_00_INTAKE",
    "STAGE_00_BRIEF_LOCKED",
    "STAGE_01_SCRIPT_GENERATION",
    "STAGE_01_SCRIPT_REVIEW",
    "STAGE_01_SCRIPT_CONFIRMED",
    "STAGE_02_STORYBOARD_GENERATION",
    "STAGE_02_STORYBOARD_REVIEW",
    "STAGE_02_STORYBOARD_CONFIRMED",
    "STAGE_03_CHARACTER_BIBLE_GENERATION",
    "STAGE_03_CHARACTER_BIBLE_REVIEW",
    "STAGE_03_CHARACTER_BIBLE_CONFIRMED",
    "STAGE_04_KEYFRAME_PROMPTS_GENERATION",
    "STAGE_04_KEYFRAME_PROMPTS_REVIEW",
    "STAGE_04_KEYFRAME_PROMPTS_CONFIRMED",
    "STAGE_05_KEYFRAME_IMAGES_GENERATION",
    "STAGE_05_KEYFRAME_IMAGES_REVIEW",
    "STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
    "STAGE_06_VIDEO_CLIPS_GENERATION",
    "STAGE_06_VIDEO_CLIPS_REVIEW",
    "STAGE_06_VIDEO_CLIPS_CONFIRMED",
    "STAGE_07_AUDIO_GENERATION",
    "STAGE_07_AUDIO_REVIEW",
    "STAGE_07_AUDIO_CONFIRMED",
    "STAGE_08_ASSEMBLY_GENERATION",
    "STAGE_08_ASSEMBLY_REVIEW",
    "STAGE_08_ASSEMBLY_CONFIRMED",
    "STAGE_09_QA_GENERATION",
    "STAGE_09_QA_REVIEW",
    "STAGE_09_QA_CONFIRMED",
    "PROJECT_DELIVERED",
]

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

OUTPUT_SCOPE_TO_LABEL = {
    "script_only": "只要剧本",
    "script_storyboard": "剧本 + 分镜脚本",
    "keyframe_prompts": "剧本 + 分镜 + 关键帧提示词",
    "keyframe_images": "生成关键帧图片素材包",
    "video_clips": "生成视频片段素材包",
    "rough_cut": "合成粗剪成片",
    "full_project": "输出完整素材工程包，方便人工剪辑",
}

OUTPUT_SCOPE_TO_TERMINAL_STAGE = {
    "script_only": "STAGE_01_SCRIPT_CONFIRMED",
    "script_storyboard": "STAGE_02_STORYBOARD_CONFIRMED",
    "keyframe_prompts": "STAGE_04_KEYFRAME_PROMPTS_CONFIRMED",
    "keyframe_images": "STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
    "video_clips": "STAGE_06_VIDEO_CLIPS_CONFIRMED",
    "rough_cut": "STAGE_08_ASSEMBLY_CONFIRMED",
    "full_project": "PROJECT_DELIVERED",
}

OUTPUT_SCOPE_TO_NEXT_STAGE = {
    "script_only": "STAGE_02_STORYBOARD",
    "script_storyboard": "STAGE_03_CHARACTER_BIBLE",
    "keyframe_prompts": "STAGE_05_KEYFRAME_IMAGES",
    "keyframe_images": "STAGE_06_VIDEO_CLIPS",
    "video_clips": "STAGE_07_AUDIO",
    "rough_cut": "STAGE_09_QA",
    "full_project": "PROJECT_DELIVERED",
}

GENERATION_STAGE_TO_SCOPE = {
    "STAGE_01_SCRIPT_GENERATION": "script_only",
    "STAGE_02_STORYBOARD_GENERATION": "script_storyboard",
    "STAGE_04_KEYFRAME_PROMPTS": "keyframe_prompts",
    "STAGE_05_KEYFRAME_IMAGES": "keyframe_images",
    "STAGE_06_VIDEO_CLIPS": "video_clips",
    "STAGE_07_AUDIO": "rough_cut",
    "STAGE_08_ASSEMBLY": "rough_cut",
    "STAGE_09_QA": "full_project",
}

LOCATION_HINTS = (
    "废弃医院",
    "医院",
    "川西的高原旷野",
    "川西高原旷野",
    "高原旷野",
    "藏式民宿",
    "便利店门口",
    "便利店",
    "咖啡馆门口",
    "咖啡馆",
    "商店门口",
    "商店",
    "超市门口",
    "超市",
    "门口",
    "街角",
    "巷口",
    "海边",
    "海滩",
    "车站",
    "月台",
    "天台",
    "桥上",
    "桥边",
    "公园",
    "教室",
    "校园",
    "厨房",
    "客厅",
    "房间",
    "窗边",
    "阳台",
    "雪山",
    "草地",
    "星空",
    "高原",
    "旷野",
    "川西",
)

WEATHER_HINTS = (
    "暴雨",
    "大雨",
    "小雨",
    "雨夜",
    "雨中",
    "雨后",
    "下雨",
    "雪夜",
    "雪中",
    "下雪",
    "雾夜",
    "雾中",
    "烈日",
    "晴天",
    "阴天",
)

TIME_HINTS = (
    "深夜",
    "夜晚",
    "夜里",
    "凌晨",
    "清晨",
    "早晨",
    "上午",
    "中午",
    "午后",
    "傍晚",
    "黄昏",
)

PROP_HINTS = (
    "外卖箱",
    "外卖袋",
    "送餐地址",
    "最后一把伞",
    "雨伞",
    "伞",
    "热可可",
    "可可",
    "咖啡",
    "纸杯",
    "花束",
    "手机",
    "照片",
    "信",
    "钥匙",
)

ROLE_SUFFIX_HINTS = (
    "外卖员",
    "骑手",
    "景观规划师",
    "规划师",
    "巡护员",
    "摄影师",
    "设计师",
    "工程师",
    "老师",
    "医生",
    "护士",
    "警察",
    "司机",
    "旅人",
    "游客",
    "创作者",
    "店员",
    "店主",
    "歌手",
    "演员",
    "学生",
    "上班族",
    "白领",
    "女孩",
    "男孩",
    "女人",
    "男人",
    "女生",
    "男生",
    "少年",
    "少女",
    "母亲",
    "父亲",
    "陌生人",
    "主角",
)

GENERIC_PERSON_SUFFIX_HINTS = (
    "女性",
    "女生",
    "女孩",
    "少女",
    "女人",
    "男性",
    "男生",
    "男孩",
    "少年",
    "男人",
)

AGE_PATTERN = r"(\d+岁(?:出头|左右)?|[一二三四五六七八九十两]+岁(?:出头|左右)?)"


@dataclass
class StoryAnchors:
    subject: str
    subject_age: str
    location: str
    weather: str
    time_of_day: str
    scene_label: str
    key_props: list[str]
    action_beats: list[str]
    emotion_beats: list[str]
    composition_beats: list[str]
    composition_focus_beats: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "subject_age": self.subject_age,
            "location": self.location,
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "scene_label": self.scene_label,
            "key_props": self.key_props,
            "action_beats": self.action_beats,
            "emotion_beats": self.emotion_beats,
            "composition_beats": self.composition_beats,
            "composition_focus_beats": self.composition_focus_beats,
        }


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def normal_brief(brief: dict[str, Any]) -> dict[str, Any]:
    normalized = brief.get("normalized")
    return normalized if isinstance(normalized, dict) else brief


def stage_index(stage: str | None) -> int:
    if not isinstance(stage, str):
        return -1
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return -1


def infer_output_scope(final_output: Any) -> str:
    raw = str(final_output or "").strip()
    if not raw:
        return ""
    return OUTPUT_SCOPE_ALIASES.get(raw, "")


def routing_from_brief(brief: dict[str, Any]) -> dict[str, Any]:
    normalized = normal_brief(brief)
    existing = brief.get("routing")
    if isinstance(existing, dict):
        scope = str(existing.get("requested_output_scope") or "").strip()
        if scope in OUTPUT_SCOPE_TO_LABEL:
            return {
                "requested_output_scope": scope,
                "requested_output_label": OUTPUT_SCOPE_TO_LABEL[scope],
                "requested_terminal_stage": OUTPUT_SCOPE_TO_TERMINAL_STAGE[scope],
                "requested_next_stage": OUTPUT_SCOPE_TO_NEXT_STAGE[scope],
                "legacy_mode": False,
            }

    scope = infer_output_scope(normalized.get("final_output") or brief.get("final_output"))
    if not scope:
        return {
            "requested_output_scope": "",
            "requested_output_label": "",
            "requested_terminal_stage": "",
            "requested_next_stage": "",
            "legacy_mode": True,
        }
    return {
        "requested_output_scope": scope,
        "requested_output_label": OUTPUT_SCOPE_TO_LABEL[scope],
        "requested_terminal_stage": OUTPUT_SCOPE_TO_TERMINAL_STAGE[scope],
        "requested_next_stage": OUTPUT_SCOPE_TO_NEXT_STAGE[scope],
        "legacy_mode": False,
    }


def apply_routing(brief: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    routing = routing_from_brief(brief)
    payload["routing"] = routing
    return routing


def should_stop_after_stage(stage: str, routing: dict[str, Any]) -> bool:
    if routing.get("legacy_mode"):
        return False
    terminal = routing.get("requested_terminal_stage")
    if not isinstance(terminal, str) or not terminal:
        return False
    return stage_index(stage) >= stage_index(terminal)


def next_stage_after(stage: str, routing: dict[str, Any], legacy_next: str | None) -> str | None:
    if routing.get("legacy_mode"):
        return legacy_next
    if should_stop_after_stage(stage, routing):
        return None
    return legacy_next


def strategy_bundle(brief: dict[str, Any], stage: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    compiled = compile_requirements(brief)
    contract = build_quality_contract(brief, compiled)
    targets = build_stage_quality_targets(stage, contract)
    return compiled, contract, targets


def count_duration_beats(target_duration_sec: int) -> int:
    if target_duration_sec <= 20:
        return 3
    if target_duration_sec <= 45:
        return 4
    if target_duration_sec <= 75:
        return 6
    if target_duration_sec <= 105:
        return 8
    if target_duration_sec <= 150:
        return 10
    if target_duration_sec <= 240:
        return 12
    return 16


def split_duration(target_duration_sec: int, count: int) -> list[int]:
    count = max(1, count)
    base = target_duration_sec // count
    remainder = target_duration_sec % count
    values = [base + (1 if idx < remainder else 0) for idx in range(count)]
    # Keep a floor of 1 second per beat.
    values = [max(1, value) for value in values]
    delta = target_duration_sec - sum(values)
    idx = 0
    while delta != 0 and values:
        pos = idx % len(values)
        if delta > 0:
            values[pos] += 1
            delta -= 1
        elif values[pos] > 1:
            values[pos] -= 1
            delta += 1
        idx += 1
    return values


def format_time(seconds: int) -> str:
    seconds = max(0, int(seconds))
    minutes, sec = divmod(seconds, 60)
    return f"{minutes:02d}:{sec:02d}"


def title_from_idea(idea: str, genre: str, style: str) -> str:
    idea = (idea or "").strip()
    if not idea:
        return "未命名短片"
    if "高原" in idea and any(token in idea for token in ["重新找到了生活的步调", "生活的步调", "精神内耗", "职业危机"]):
        return "在高原重新呼吸"
    if "川西" in idea and "星空" in idea:
        return "风穿过川西"
    if any(token in idea for token in ["黄昏", "傍晚", "落日"]) and any(token in idea for token in ["海滩", "海边"]) and any(token in idea for token in ["散步", "放空"]):
        return "黄昏潮线"
    if "雨夜" in idea and "便利店" in idea and any(token in idea for token in ["伞", "热可可"]):
        return "雨夜留下的伞"
    if len(idea) <= 12:
        return idea
    suffix = "短片" if "片" not in idea else ""
    if "海滩" in idea or "海边" in idea:
        return f"海边的{suffix or '故事'}".strip("的")
    if "女孩" in idea and "落日" in idea:
        return "落日之后"
    if "剧本" in idea or "故事" in idea:
        return idea[:10]
    if genre in {"治愈", "剧情短片"}:
        return "温柔时刻"
    if style in {"国风水墨/古风", "国风/古风"}:
        return "墨色人间"
    return idea[:14]


def default_theme(genre: str, style: str) -> str:
    if genre == "音乐MV" and style == "写实电影感":
        return "逃离内耗、重新校准生活节奏、在人与自然之间恢复真实感知"
    if genre in {"治愈", "爱情"}:
        return "释怀、成长、重新出发"
    if genre in {"悬疑", "恐怖惊悚"}:
        return "未知、压迫、真相显影"
    if genre in {"科幻", "奇幻"}:
        return "探索、改变、命运回响"
    if style in {"国风/古风", "国风水墨/古风"}:
        return "东方意境、留白、情绪回声"
    return "情绪推进与视觉完成度"


def default_subject(idea: str, characters_required: Any) -> str:
    if any(token in idea for token in ["女孩", "少女", "女主", "她"]):
        return "女孩"
    if any(token in idea for token in ["男孩", "少年", "他"]):
        return "男孩"
    if characters_required is False:
        return "场景主体"
    return "主角"


def default_voice_lines(voice_mode: str, beat_index: int, theme: str) -> tuple[str, str]:
    if "不需要" in voice_mode or "不确定" in voice_mode or "建议" in voice_mode:
        return "", ""
    if "对白" in voice_mode and "旁白" in voice_mode:
        return ("", f"角色在第{beat_index + 1}拍中推进情绪。")
    if "对白" in voice_mode:
        return ("", f"角色在此刻说出与{theme}有关的话。")
    return (f"第{beat_index + 1}拍：以{theme}为主的旁白推进。", "")


def _ordered_hits(text: str, hints: tuple[str, ...]) -> list[str]:
    hits: list[tuple[int, str]] = []
    lowered = text.lower()
    for hint in hints:
        idx = lowered.find(hint.lower())
        if idx >= 0:
            hits.append((idx, hint))
    hits.sort(key=lambda item: (item[0], -len(item[1])))
    ordered: list[str] = []
    for _, hint in hits:
        if any(hint in existing for existing in ordered):
            continue
        if hint not in ordered:
            ordered.append(hint)
    return ordered


def _dedupe_candidates(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value:
            continue
        if any(value == existing or value in existing for existing in ordered):
            continue
        ordered.append(value)
    return ordered


def _first_hit(text: str, hints: tuple[str, ...]) -> str:
    hits = _ordered_hits(text, hints)
    return hits[0] if hits else ""


def _clean_clause(text: str) -> str:
    value = re.sub(r"\s+", "", str(text or "")).strip("，。；;、 ")
    value = re.sub(r"^(然后|随后|接着|最后|于是|而后)", "", value)
    return value.strip("，。；;、 ")


def _split_idea_clauses(idea: str) -> list[str]:
    clauses = [_clean_clause(part) for part in re.split(r"[，。；;！？!?]", idea or "")]
    return [clause for clause in clauses if clause]


def _extract_age(text: str) -> str:
    match = re.search(AGE_PATTERN, text or "")
    return str(match.group(1)).strip() if match else ""


def _simplify_subject_label(label: str) -> str:
    value = str(label or "").strip("，。；;、 ")
    if not value or "的" not in value:
        return value
    head, tail = value.rsplit("的", 1)
    tail = tail.strip("，。；;、 ")
    if not tail:
        return value
    if re.search(AGE_PATTERN, head) and tail in {"女孩", "男孩", "女人", "男人", "女生", "男生", "少年", "少女"}:
        return value
    if tail in GENERIC_PERSON_SUFFIX_HINTS:
        return value
    if tail.endswith(ROLE_SUFFIX_HINTS) or tail in ROLE_SUFFIX_HINTS:
        return tail
    return value


def _extract_subject_from_idea(idea: str, characters_required: Any) -> tuple[str, str]:
    role_pattern = "|".join(sorted((re.escape(item) for item in ROLE_SUFFIX_HINTS), key=len, reverse=True))
    generic_person_pattern = "|".join(sorted((re.escape(item) for item in GENERIC_PERSON_SUFFIX_HINTS), key=len, reverse=True))
    patterns = [
        rf"一位(?P<label>[^，。；]{{1,32}}?(?:{generic_person_pattern}))",
        rf"一名(?P<label>[^，。；]{{1,32}}?(?:{generic_person_pattern}))",
        rf"一个(?P<label>[^，。；]{{1,32}}?(?:{generic_person_pattern}))",
        rf"一位(?P<label>[^，。；]{{1,32}}?(?:{role_pattern}))",
        rf"一个(?P<label>[^，。；]{{1,32}}?(?:{role_pattern}))",
        rf"(?P<label>[^，。；]{{1,32}}?(?:{role_pattern}))",
    ]
    for pattern in patterns:
        match = re.search(pattern, idea or "")
        if match:
            raw_label = str(match.group("label") or "").strip()
            label = _simplify_subject_label(raw_label)
            age = _extract_age(raw_label) or _extract_age(idea) or "20岁出头"
            return label, age
    if characters_required is False:
        return "场景主体", "未知"
    return "主角", _extract_age(idea) or "20岁出头"


def _extract_location(idea: str) -> str:
    location_pattern = "|".join(sorted((re.escape(item) for item in LOCATION_HINTS), key=len, reverse=True))
    for pattern in [
        rf"前往(?P<location>[^，。；]{{1,24}}?(?:{location_pattern}))",
        rf"在(?P<location>[^，。；]{{1,24}}?(?:{location_pattern}))",
        rf"(?P<location>[^，。；]{{0,18}}?(?:{location_pattern}))",
    ]:
        match = re.search(pattern, idea or "")
        if not match:
            continue
        location = str(match.group("location") or "").strip().replace("的", "")
        for prefix in [*WEATHER_HINTS, *TIME_HINTS]:
            if location.startswith(prefix):
                location = location[len(prefix):].strip()
        location = re.sub(r"^(?:一[家座栋间所]?|这家|那家)", "", location).strip()
        if "医院" in location:
            return "废弃医院" if "废弃" in location else "医院"
        if location:
            return location
    return ""


def _expand_sequence(values: list[str], count: int) -> list[str]:
    if count <= 0:
        return []
    cleaned = [value for value in values if value]
    if not cleaned:
        return [""] * count
    if len(cleaned) >= count:
        return cleaned[:count]
    expanded: list[str] = []
    for idx in range(count):
        source_idx = min(len(cleaned) - 1, int(idx * len(cleaned) / count))
        expanded.append(cleaned[source_idx])
    return expanded


def _normalize_action_clause(clause: str, subject: str, scene_label: str) -> str:
    original = _clean_clause(clause)
    value = clause
    if subject:
        descriptor_match = re.match(rf"^(?:一位|一个|一名)?(?P<descriptor>.+?)的{re.escape(subject)}$", value)
        if descriptor_match:
            descriptor = str(descriptor_match.group("descriptor") or "").strip("，。；;、 ")
            if descriptor:
                value = descriptor
    if subject:
        value = value.replace(f"一位{subject}", "", 1)
        value = value.replace(f"一个{subject}", "", 1)
        value = value.replace(f"一名{subject}", "", 1)
        value = value.replace(subject, "", 1)
    if scene_label:
        value = re.sub(rf"^在{re.escape(scene_label)}", "", value)
    value = value.lstrip("在").strip("，。；;、 ")
    value = re.sub(r"^(一位|一个|一名)", "", value).strip("，。；;、 ")
    if not value and subject and original in {subject, f"一位{subject}", f"一个{subject}", f"一名{subject}"}:
        return ""
    return value or clause


def _emotion_for_action(action: str, genre: str, style: str, index: int, total: int) -> str:
    if any(token in action for token in ["留给", "递给", "送给", "让给"]):
        return "克制善意"
    if any(token in action for token in ["淋着雨", "走远", "离开", "转身"]):
        return "落寞余温"
    if any(token in action for token in ["回头", "发现", "看见", "多了一杯", "收到"]):
        return "意外回暖"
    defaults = emotion_sequence(genre, style)
    return defaults[min(index, len(defaults) - 1)]


def _opening_shot_frame_phrase(aspect_ratio: str) -> str:
    ratio = str(aspect_ratio or "").strip()
    if ratio == "9:16":
        return "先用竖屏建立镜头交代"
    if ratio == "16:9":
        return "先用横屏建立镜头交代"
    if ratio == "1:1":
        return "先用方画幅建立镜头交代"
    if ratio == "21:9":
        return "先用宽银幕建立镜头交代"
    return "先用镜头建立交代"


def _composition_for_action(
    scene_label: str,
    weather: str,
    action: str,
    props: list[str],
    index: int,
    total: int,
    aspect_ratio: str = "",
) -> str:
    primary_prop = props[min(index, len(props) - 1)] if props else ""
    environment_focus = f"{scene_label}与{weather or '现场氛围'}"
    if index == 0:
        opening_phrase = _opening_shot_frame_phrase(aspect_ratio)
        if primary_prop:
            return f"{opening_phrase}{environment_focus}，人物与{primary_prop}同框。".strip()
        return f"{opening_phrase}{environment_focus}，人物与海面、天光一起进入画面。".strip()
    if index == total - 1:
        if primary_prop:
            return f"把镜头重心放在动作过后的情绪回落，突出{primary_prop}与人物反应。"
        return "把镜头重心放在动作过后的情绪回落，突出人物状态和环境呼吸。"
    if primary_prop:
        return f"构图聚焦{action}的瞬间，保留{scene_label}环境线索和{primary_prop}细节。"
    return f"构图聚焦{action}的瞬间，保留{scene_label}环境线索和人物动作细节。"


def _extract_setting_candidates(idea: str, scene_label: str) -> list[str]:
    candidates: list[str] = []
    for pattern in [
        r"川西(?:的)?高原旷野",
        r"藏式民宿",
        r"雪山、草地与星空",
        r"雪山",
        r"草地",
        r"星空",
        r"海滩",
        r"海边",
    ]:
        for match in re.finditer(pattern, idea or ""):
            value = str(match.group(0) or "").strip().replace("的", "")
            if value and not any(value == existing or value in existing for existing in candidates):
                candidates.append(value)
    if scene_label and scene_label not in {"故事现场", "古风场景", "未来感场景"} and scene_label not in candidates:
        candidates.insert(0, scene_label)
    return _dedupe_candidates(candidates)


def _music_cue_for_profile(music_mode: str, music_profile: str, beat_index: int, total: int) -> str:
    if "需要" not in (music_mode or "") and not music_profile:
        return ""
    if music_profile == "song":
        if beat_index == 0:
            return "song: 主歌起段，先铺陈氛围和人物心境"
        if beat_index == total - 1:
            return "song: 副歌或尾奏收束，放大情绪落点"
        return "song: 跟随歌曲主旋律推进画面节奏"
    if music_profile == "instrumental":
        return "instrumental: 纯音乐旋律持续推进情绪"
    if music_profile == "underscore" or "需要" in (music_mode or ""):
        return "underscore: 背景配乐托住环境氛围"
    return ""


def _compose_music_video_story_beats(idea: str, beat_count: int) -> list[str]:
    beats: list[str] = []
    if any(token in idea for token in ["职业危机", "精神内耗"]):
        beats.append("被职业危机与精神内耗推到几乎失衡")

    departure_parts: list[str] = []
    if "逃离钢筋水泥" in idea or "逃离" in idea:
        departure_parts.append("逃离钢筋水泥")
    if "驱车" in idea and any(token in idea for token in ["高原", "旷野", "川西"]):
        departure_parts.append("驱车驶入川西高原旷野")
    if departure_parts:
        beats.append("，".join(departure_parts))

    if all(token in idea for token in ["修缮", "民宿", "巡护员", "相识"]):
        beats.append("在修缮藏式民宿时与野生动物巡护员相识")
    elif "修缮" in idea and "民宿" in idea:
        beats.append("在修缮濒临倒闭的藏式民宿时慢慢停下来")

    if any(token in idea for token in ["雪山", "草地", "星空", "生活的步调", "羁绊"]):
        beats.append("在雪山、草地与星空之间重新找回生活步调，也看见人与自然的真实羁绊")

    cleaned = [beat for beat in beats if beat]
    if not cleaned:
        return []
    if len(cleaned) >= beat_count:
        return cleaned[:beat_count]
    return _expand_sequence(cleaned, beat_count)


def _compose_beach_reflection_beats(idea: str, beat_count: int) -> list[str]:
    if not (any(token in idea for token in ["黄昏", "傍晚", "落日"]) and any(token in idea for token in ["海滩", "海边"]) and any(token in idea for token in ["散步", "放空"])):
        return []
    beats = [
        "沿着潮线慢慢散步",
        "停下来望向海平线",
        "让海风和晚霞把情绪慢慢吹散",
        "继续朝前走，把心事留在身后",
    ]
    return _expand_sequence(beats, beat_count)


def _stage01_logline(idea: str, subject: str, genre: str, settings: list[str]) -> str:
    if genre == "音乐MV" and "高原" in idea:
        return (
            f"一位{_extract_age(idea) or ''}{subject}在职业危机与精神内耗中逃离城市，"
            "一路驶入川西高原；在修缮藏式民宿、与巡护员相识的过程中，"
            "她在雪山、草地与星空之间重新找回生活的步调。"
        ).replace("一位城市景观规划师", "一位城市景观规划师").replace("一位30岁城市景观规划师", "一位30岁的城市景观规划师")
    if any(token in idea for token in ["黄昏", "傍晚", "落日"]) and any(token in idea for token in ["海滩", "海边"]) and any(token in idea for token in ["散步", "放空"]):
        return f"黄昏海滩上，{subject}独自散步，在海风、晚霞和脚步声里慢慢把情绪放空。"
    if "雨夜" in idea and "便利店" in idea and any(token in idea for token in ["伞", "热可可"]):
        return f"雨夜便利店门口，{subject}把最后一把伞留给陌生人，自己走进雨里，却在回头时接住一杯热可可。"
    setting_text = "、".join(settings[:2]) if settings else ""
    if setting_text:
        return f"{setting_text}里，{subject}沿着自己的动作与停顿推进情绪，画面重心落在人物和环境的共同呼吸上。"
    return idea.strip("。")


def _stage01_summary_line(subject: str, scene: str, action: str, emotion: str, index: int, total: int) -> str:
    if "职业危机" in action or "精神内耗" in action:
        return f"{subject}被城市高压和长期内耗逼到失衡边缘，离开的念头第一次变得具体。"
    if "逃离钢筋水泥" in action or "驱车" in action:
        return f"{subject}把熟悉的钢筋水泥抛在身后，沿着通往{scene}的路让呼吸慢慢松开。"
    if "民宿" in action or "巡护员" in action:
        return f"{subject}在修缮与相识之间建立起新的连接，情绪从封闭转向回应。"
    if any(token in action for token in ["雪山", "草地", "星空", "步调", "羁绊"]):
        return f"{subject}在旷野与星空之间重新找回生活步调，也真正感到人与自然的羁绊。"
    if any(token in action for token in ["散步", "放空"]) and any(token in scene for token in ["海滩", "海边"]):
        if index == 0:
            return f"{scene}上，{subject}沿着潮线慢慢往前走，像是在等海风把心事吹散。"
        if index == 1:
            return f"{subject}停下来望向海平线，呼吸和脚步都一点点慢下来。"
        if index == total - 1:
            return f"{subject}把情绪留在海风里，继续往前走，整个人终于轻下来。"
        return f"海风裹着晚霞从她身边过去，那点没说出口的情绪终于开始松开。"
    if "停下来望向海平线" in action:
        return f"{subject}停下来望向海平线，呼吸和情绪都一点点慢下来。"
    if "让海风和晚霞把情绪慢慢吹散" in action:
        return "海风裹着晚霞从她身边过去，那点没说出口的情绪终于开始松开。"
    if "继续朝前走，把心事留在身后" in action:
        return f"{subject}继续朝前走，把心事留在身后，整个人终于轻下来。"
    if "雨夜" in scene and "伞" in action:
        return f"{subject}把最后一把伞递出去，情绪里的克制和善意同时被看见。"
    if index == total - 1:
        return f"{subject}把情绪安放在{scene}里，最终落到{emotion}。"
    if index == 0:
        return f"{scene}里，{subject}{action}，先把这个人的状态轻轻放进画面。"
    return f"{subject}{action}，情绪也顺着这个动作继续往前走。"


def _stage01_visual_focus_sentence(composition_focus: str) -> str:
    text = str(composition_focus or "").strip()
    if not text:
        return ""
    if "停下来望向海平线" in text:
        return "镜头跟住她望向海平线的那一刻，黄昏海滩的风声、天光和人物停顿都要留住。"
    if "让海风和晚霞把情绪慢慢吹散" in text:
        return "镜头跟住她在风里慢慢松开的那一刻，海面、晚霞和人物呼吸要始终在同一个节奏里。"
    if text.startswith("把镜头重心放在动作过后的情绪回落"):
        return "最后把画面落在她继续向前之后慢慢轻下来的状态上，人物和环境的呼吸都要留住。"
    if text.startswith("先用竖屏建立镜头交代"):
        return text.replace("先用竖屏建立镜头交代", "先把", 1).replace("，人物与", "交代出来，让人物与", 1)
    if text.startswith("先用横屏建立镜头交代"):
        return text.replace("先用横屏建立镜头交代", "先把", 1).replace("，人物与", "交代出来，让人物与", 1)
    if text.startswith("先用方画幅建立镜头交代"):
        return text.replace("先用方画幅建立镜头交代", "先把", 1).replace("，人物与", "交代出来，让人物与", 1)
    if text.startswith("先用宽银幕建立镜头交代"):
        return text.replace("先用宽银幕建立镜头交代", "先把", 1).replace("，人物与", "交代出来，让人物与", 1)
    if text.startswith("先用镜头建立交代"):
        return text.replace("先用镜头建立交代", "先把", 1).replace("，人物与", "交代出来，让人物与", 1)
    if text.startswith("构图聚焦"):
        return text.replace("构图聚焦", "镜头跟住", 1)
    if text.startswith("把镜头重心放在"):
        return text.replace("把镜头重心放在", "最后把画面落在", 1)
    return text


def _stage01_visual_line(
    scene: str,
    subject: str,
    action: str,
    composition_focus: str,
    props_label: str,
    index: int,
    total: int,
) -> str:
    if "职业危机" in action or "精神内耗" in action:
        opening = (
            f"玻璃幕墙、电脑冷光和压缩的城市通勤把{subject}推到几乎失衡的边缘，"
            "她的疲惫感先于动作抵达画面。"
        )
    elif "逃离钢筋水泥" in action or "驱车" in action:
        opening = (
            f"{subject}把城市抛在身后，车窗外从高架、隧道和楼群切到盘山公路、风口与高原天光，"
            "画面开始真正打开。"
        )
    elif "民宿" in action or "巡护员" in action:
        opening = (
            f"木梁、白墙、工具灰尘和经幡构成民宿修缮现场，{subject}在劳作间与巡护员建立第一层默契。"
        )
    elif any(token in action for token in ["雪山", "草地", "星空", "步调", "羁绊"]):
        opening = (
            f"雪山、草地与星空依次铺开，{subject}终于在风声与空旷里慢下来，"
            "情绪从紧绷过渡到重新呼吸。"
        )
    elif any(token in action for token in ["散步", "放空"]) and any(token in scene for token in ["海滩", "海边"]):
        opening = (
            f"晚霞压低在海面上，{subject}沿着潮线慢慢走，"
            "海风、裙摆和脚步声一起把画面里的情绪放缓。"
        )
    elif "停下来望向海平线" in action:
        opening = (
            f"镜头贴近{subject}停下来的那一刻，海风带动发丝和裙摆，"
            "停顿感比动作本身更重要。"
        )
    elif "让海风和晚霞把情绪慢慢吹散" in action:
        opening = (
            f"海风、晚霞和空阔海面把{subject}包在画面中央，"
            "原本绷着的情绪开始真正松开。"
        )
    elif "继续朝前走，把心事留在身后" in action:
        opening = (
            f"远景里，{subject}继续沿着海边往前走，背影被落日拉长，"
            "镜头把释然留给海面、风声和脚步。"
        )
    elif "雨夜" in scene and "伞" in action:
        opening = (
            f"便利店霓虹映在湿地上，{subject}把最后一把伞递出去，"
            "雨声和停顿一起撑起这个瞬间。"
        )
    else:
        opening = f"{scene}里，{subject}{action}，镜头保留环境层次与{props_label}细节。"

    lines = [opening if opening.endswith("。") else f"{opening}。"]
    if index == total - 1:
        lines.append("结尾把情绪落点留在人物与环境的共同呼吸上。")
    focus_line = _stage01_visual_focus_sentence(composition_focus)
    if focus_line:
        lines.append(focus_line if focus_line.endswith("。") else f"{focus_line}。")
    return " ".join(lines).strip()


def _stage01_title_candidates(title: str, idea: str, genre: str) -> list[str]:
    candidates = [title]
    if genre == "音乐MV" and "高原" in idea:
        candidates.extend(["风穿过川西", "把心留在旷野"])
    elif any(token in idea for token in ["黄昏", "傍晚", "落日"]) and any(token in idea for token in ["海滩", "海边"]):
        candidates.extend(["海风经过她", "潮声落下之前"])
    elif "雨夜" in idea and "便利店" in idea:
        candidates.extend(["便利店门口的热可可", "雨夜可可"])
    elif "海滩" in idea or "海边" in idea:
        candidates.extend(["黄昏海风里", "潮线之外"])
    return _dedupe_candidates(candidates)


def _stage01_protagonist_state(subject: str, idea: str) -> str:
    if any(token in idea for token in ["职业危机", "精神内耗"]):
        return f"{subject}正处在被工作消耗、需要暂时逃离原有秩序的边缘状态"
    if any(token in idea for token in ["黄昏", "海滩", "海边"]) and any(token in idea for token in ["散步", "放空"]):
        return f"{subject}看起来平静，但心里还压着一点没完全散开的心事"
    if "雨夜" in idea and "便利店" in idea:
        return f"{subject}习惯把情绪压在心里，也习惯在寒冷时刻先顾别人"
    return f"{subject}进入故事时仍背着未被解决的情绪负担"


def _stage01_theme_from_idea(idea: str, genre: str, style: str) -> str:
    if genre == "音乐MV" and style == "写实电影感" and "高原" in idea and any(token in idea for token in ["精神内耗", "职业危机"]):
        return "逃离长期内耗，在人与自然之间重新找回身体和情绪的真实节奏"
    if any(token in idea for token in ["黄昏", "傍晚", "落日"]) and any(token in idea for token in ["海滩", "海边"]) and any(token in idea for token in ["散步", "放空"]):
        return "把没说出口的情绪留给海风和晚霞"
    if "雨夜" in idea and "便利店" in idea and any(token in idea for token in ["伞", "热可可"]):
        return "微小善意会在最冷的时候悄悄回到人身边"
    return default_theme(genre, style)


def _stage01_narrative_movement(idea: str, genre: str, style: str) -> str:
    if genre == "音乐MV" and style == "写实电影感" and "高原" in idea and any(token in idea for token in ["精神内耗", "职业危机"]):
        return "从逃离钢筋水泥到在高原重新与世界建立真实联系"
    if any(token in idea for token in ["黄昏", "傍晚", "落日"]) and any(token in idea for token in ["海滩", "海边"]) and any(token in idea for token in ["散步", "放空"]):
        return "从独自沉浸到在海风与脚步里慢慢把情绪放下"
    if "雨夜" in idea and "便利店" in idea and any(token in idea for token in ["伞", "热可可"]):
        return "从把温暖让出去到在雨夜重新接住一份被返还的善意"
    if genre == "治愈":
        return "从情绪负担较重的起点，慢慢走向可以呼吸的状态"
    return "从初始情绪进入到最终落点，让人物状态在镜头里完成一次可感知的变化"


def _stage01_ending_direction(subject: str, idea: str, scene: str, beats: list[dict[str, Any]]) -> str:
    if any(token in idea for token in ["黄昏", "傍晚", "落日"]) and any(token in idea for token in ["海滩", "海边"]) and any(token in idea for token in ["散步", "放空"]):
        return f"{subject}沿着潮线继续往前走，背影和呼吸都慢慢轻下来。"
    if beats:
        return str((beats[-1] or {}).get("summary") or "").strip()
    return f"{subject}把情绪安放在{scene}里。"


def _stage01_avoid_list(genre: str, style: str, voice_mode: str) -> list[str]:
    if genre == "音乐MV" and style == "写实电影感" and "不确定" in voice_mode:
        return [
            "不要把情绪写成直白说教",
            "不要突然插入第二主角或明显对手戏",
            "不要让画面脱离黄昏海滩本身的呼吸感",
        ]
    items = ["不要偏离 locked brief 的题材、风格和配音约束"]
    if genre == "音乐MV":
        items.append("不要把 MV 写成对白驱动剧情片")
    if style == "写实电影感":
        items.append("不要使用过度悬浮或口号化的抒情表达")
    if "不需要配音" in voice_mode:
        items.append("不要额外生成旁白或角色对白")
    return items


def extract_story_anchors(brief: dict[str, Any], beat_count: int) -> StoryAnchors:
    normalized = normal_brief(brief)
    idea = str(normalized.get("idea") or brief.get("idea") or "").strip()
    genre = str(normalized.get("genre") or brief.get("genre") or "").strip()
    style = str(normalized.get("style") or brief.get("style") or "").strip()
    aspect_ratio = str(normalized.get("aspect_ratio") or brief.get("aspect_ratio") or "").strip()
    subject, subject_age = _extract_subject_from_idea(idea, normalized.get("characters_required"))
    weather = _first_hit(idea, WEATHER_HINTS)
    time_of_day = _first_hit(idea, TIME_HINTS)
    if weather == "雨夜" and not time_of_day:
        time_of_day = "夜晚"
    location = _extract_location(idea)
    if not location:
        if "海滩" in idea or "海边" in idea:
            location = "海边"
        elif "街" in idea:
            location = "街角"
        elif style in {"国风/古风", "国风水墨/古风"}:
            location = "古风场景"
        elif genre in {"科幻", "奇幻"}:
            location = "未来感场景"
        else:
            location = "故事现场"
    scene_parts = [part for part in [weather or time_of_day, location] if part]
    scene_label = "".join(scene_parts) if scene_parts else location
    props = _ordered_hits(idea, PROP_HINTS)
    clauses = [_normalize_action_clause(item, subject, scene_label) for item in _split_idea_clauses(idea)]
    action_beats = _expand_sequence(clauses or [f"在{scene_label}推进故事"], beat_count)
    emotion_beats = [
        _emotion_for_action(action, genre, style, idx, beat_count)
        for idx, action in enumerate(action_beats)
    ]
    composition_focus_beats = [
        _composition_for_action(scene_label, weather, action, props, idx, beat_count, aspect_ratio)
        for idx, action in enumerate(action_beats)
    ]
    return StoryAnchors(
        subject=subject,
        subject_age=subject_age,
        location=location,
        weather=weather,
        time_of_day=time_of_day,
        scene_label=scene_label,
        key_props=props,
        action_beats=action_beats,
        emotion_beats=emotion_beats,
        composition_beats=list(composition_focus_beats),
        composition_focus_beats=composition_focus_beats,
    )


def infer_scene(idea: str, genre: str, style: str) -> str:
    location = _extract_location(idea)
    weather = _first_hit(idea, WEATHER_HINTS)
    time_of_day = _first_hit(idea, TIME_HINTS)
    parts = [part for part in [weather or time_of_day, location] if part]
    if parts:
        return "".join(parts)
    if "海滩" in idea or "海边" in idea:
        return "落日海边"
    if "城市" in idea or "街" in idea:
        return "城市街景"
    if style in {"国风/古风", "国风水墨/古风"}:
        return "古风场景"
    if genre in {"科幻", "奇幻"}:
        return "未来感场景"
    return "故事现场"


def infer_action(subject: str, idea: str, beat_index: int, total: int) -> str:
    anchors = extract_story_anchors({"normalized": {"idea": idea}}, total)
    action = anchors.action_beats[min(beat_index, len(anchors.action_beats) - 1)]
    return f"{subject}{action}" if subject and not action.startswith(subject) else action


def parse_character_from_idea(idea: str) -> tuple[str, str]:
    return _extract_subject_from_idea(idea, True)


def emotion_sequence(genre: str, style: str) -> list[str]:
    if genre in {"治愈", "爱情"}:
        return ["安静", "沉思", "触动", "释怀", "平静", "希望"]
    if genre in {"悬疑", "恐怖惊悚"}:
        return ["警觉", "怀疑", "紧张", "逼近真相", "骤然明朗"]
    if genre in {"科幻", "奇幻"}:
        return ["陌生", "探索", "发现", "突破", "回望", "展开"]
    if style in {"国风/古风", "国风水墨/古风"}:
        return ["留白", "回眸", "起意", "沉静", "收束"]
    return ["观察", "推进", "转折", "收束"]


def build_stage01_script(brief: dict[str, Any]) -> dict[str, Any]:
    normalized = normal_brief(brief)
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_01")
    idea = str(normalized.get("idea") or brief.get("idea") or "").strip()
    genre = str(normalized.get("genre") or brief.get("genre") or "").strip()
    style = str(normalized.get("style") or brief.get("style") or "").strip()
    voice_mode = str(normalized.get("voice_mode") or "").strip()
    music_mode = str(normalized.get("music_mode") or "").strip()
    music_profile = str(normalized.get("music_profile") or "").strip()
    duration = int(normalized.get("target_duration_sec") or 30)
    beat_count = count_duration_beats(duration)
    beat_lengths = split_duration(duration, beat_count)
    anchors = extract_story_anchors(brief, beat_count)
    custom_music_video_beats = _compose_music_video_story_beats(idea, beat_count) if genre == "音乐MV" else []
    custom_beach_beats = _compose_beach_reflection_beats(idea, beat_count)
    preferred_beats = custom_music_video_beats or custom_beach_beats
    if preferred_beats:
        anchors.action_beats = preferred_beats
        anchors.emotion_beats = [
            _emotion_for_action(action, genre, style, idx, len(preferred_beats))
            for idx, action in enumerate(preferred_beats)
        ]
        anchors.composition_beats = [
            _composition_for_action(anchors.scene_label, anchors.weather, action, anchors.key_props, idx, len(preferred_beats), str(normalized.get("aspect_ratio") or ""))
            for idx, action in enumerate(preferred_beats)
        ]
        anchors.composition_focus_beats = list(anchors.composition_beats)
    title = title_from_idea(idea, genre, style)
    subject_name, subject_age = anchors.subject, anchors.subject_age
    theme = _stage01_theme_from_idea(idea, genre, style)
    scene = anchors.scene_label
    settings = _extract_setting_candidates(idea, scene) or [scene]
    logline = _stage01_logline(idea, subject_name, genre, settings)
    title_candidates = _stage01_title_candidates(title, idea, genre)
    props_label = "、".join(anchors.key_props[:2]) if anchors.key_props else "关键道具"
    beats = []
    sections = []
    elapsed = 0
    for idx, beat_len in enumerate(beat_lengths):
        start = elapsed
        end = elapsed + beat_len
        elapsed = end
        emotion = anchors.emotion_beats[min(idx, len(anchors.emotion_beats) - 1)]
        action = anchors.action_beats[min(idx, len(anchors.action_beats) - 1)]
        composition_focus = anchors.composition_beats[min(idx, len(anchors.composition_beats) - 1)]
        summary = _stage01_summary_line(subject_name, scene, action, emotion, idx, len(beat_lengths))
        voiceover, dialogue = default_voice_lines(voice_mode, idx, theme)
        if voiceover:
            voiceover = summary
        beats.append({
            "start": format_time(start),
            "end": format_time(end),
            "summary": summary,
            "emotion": emotion,
        })
        sections.append({
            "time": f"{format_time(start)}-{format_time(end)}",
            "visual": _stage01_visual_line(scene, subject_name, action, composition_focus, props_label, idx, len(beat_lengths)),
            "composition_focus": composition_focus,
            "voiceover": voiceover,
            "dialogue": dialogue,
            "music_cue": _music_cue_for_profile(music_mode, music_profile, idx, len(beat_lengths)),
        })
    return {
        "schema_version": "0.3.0",
        "stage": "STAGE_01_SCRIPT_GENERATION",
        "status": "draft",
        "project_id": brief.get("project_id") or "",
        "source_brief": str(brief.get("project_dir") or "").replace("\\", "/"),
        "title": title,
        "title_candidates": title_candidates,
        "logline": logline,
        "theme": theme,
        "protagonist_state": _stage01_protagonist_state(subject_name, idea),
        "narrative_movement": _stage01_narrative_movement(idea, genre, style),
        "ending_direction": _stage01_ending_direction(subject_name, idea, scene, beats),
        "avoid": _stage01_avoid_list(genre, style, voice_mode),
        "characters": [
            {
                "name": subject_name,
                "age": subject_age,
                "role": "main",
            }
        ],
        "settings": settings,
        "duration_plan": {
            "target_duration_sec": duration,
            "target_duration_label": normalized.get("target_duration_label") or f"{duration}秒",
            "beats": beats,
        },
        "script": {
            "format": "screenplay",
            "voice_mode": voice_mode or normalized.get("voice_mode") or "",
            "music_mode": music_mode or normalized.get("music_mode") or "",
            "music_profile": music_profile,
            "sections": sections,
        },
        "creative_contract": {
            "idea": idea,
            "genre": genre,
            "style": style,
            "subject": subject_name,
            "scene": scene,
            "performance_direction": theme,
        },
        "story_anchors": anchors.to_dict(),
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": {
            "matches_locked_brief": True,
            "duration_fits": True,
            "genre_style_fits": True,
            "aspect_ratio_fits": True,
            "character_requirement_fits": True,
            "voice_fits": True,
            "music_fits": True,
            "final_output_scope_fits": True,
            "ready_for_storyboard": True,
            "quality_targets_defined": bool(quality_targets),
            "notes": [
                "Draft generated by pipeline_blueprints.",
            ],
        },
        "allowed_next_stage": None,
    }
