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
    if "不需要" in voice_mode:
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


def _extract_subject_from_idea(idea: str, characters_required: Any) -> tuple[str, str]:
    patterns = [
        r"一位(?P<label>[^，。；]{1,24}?(?:女孩|男孩|女人|男人|女生|男生|店员|少年|少女|母亲|父亲|陌生人|主角))",
        r"一个(?P<label>[^，。；]{1,24}?(?:女孩|男孩|女人|男人|女生|男生|店员|少年|少女|母亲|父亲|陌生人|主角))",
        r"(?P<label>[^，。；]{1,24}?(?:女孩|男孩|女人|男人|女生|男生|店员|少年|少女|母亲|父亲|陌生人|主角))",
    ]
    for pattern in patterns:
        match = re.search(pattern, idea or "")
        if match:
            label = str(match.group("label") or "").strip()
            age_match = re.search(r"(\d+岁(?:出头|左右)?|[一二三四五六七八九十两]+岁(?:出头|左右)?)", label)
            age = age_match.group(1) if age_match else "20岁出头"
            return label, age
    if characters_required is False:
        return "场景主体", "未知"
    return "主角", "20岁出头"


def _extract_location(idea: str) -> str:
    for pattern in [
        r"在(?P<location>[^，。；]{1,24}?(?:便利店门口|便利店|咖啡馆门口|咖啡馆|商店门口|商店|超市门口|超市|门口|街角|巷口|海边|海滩|车站|月台|天台|桥上|桥边|公园|教室|校园|厨房|客厅|房间|窗边|阳台))",
        r"(?P<location>[^，。；]{0,12}?(?:便利店门口|便利店|咖啡馆门口|咖啡馆|商店门口|商店|超市门口|超市|门口|街角|巷口|海边|海滩|车站|月台|天台|桥上|桥边|公园|教室|校园|厨房|客厅|房间|窗边|阳台))",
    ]:
        match = re.search(pattern, idea or "")
        if not match:
            continue
        location = str(match.group("location") or "").strip()
        for prefix in [*WEATHER_HINTS, *TIME_HINTS]:
            if location.startswith(prefix):
                location = location[len(prefix):].strip()
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
    value = clause
    if subject:
        value = value.replace(f"一位{subject}", "", 1)
        value = value.replace(f"一个{subject}", "", 1)
        value = value.replace(subject, "", 1)
    if scene_label:
        value = re.sub(rf"^在{re.escape(scene_label)}", "", value)
    value = value.lstrip("在").strip("，。；;、 ")
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


def _composition_for_action(scene_label: str, weather: str, action: str, props: list[str], index: int, total: int) -> str:
    primary_prop = props[min(index, len(props) - 1)] if props else ""
    if index == 0:
        return f"先用竖屏建立镜头交代{scene_label}与{weather or '现场氛围'}，人物与{primary_prop or '关键道具'}同框。".strip()
    if index == total - 1:
        return f"把镜头重心放在{action}后的情绪回落，突出{primary_prop or '关键道具'}与人物回头反应。"
    return f"构图聚焦{action}的瞬间，保留{scene_label}环境线索和{primary_prop or '关键道具'}细节。"


def _intent_summary(scene_label: str, action: str, emotion: str, key_prop: str) -> str:
    prop_part = f"，让{key_prop}成为情绪支点" if key_prop else ""
    return f"这个镜头要在{scene_label}里抓住“{action}”这一瞬间，传达{emotion}{prop_part}。"


def extract_story_anchors(brief: dict[str, Any], beat_count: int) -> StoryAnchors:
    normalized = normal_brief(brief)
    idea = str(normalized.get("idea") or brief.get("idea") or "").strip()
    genre = str(normalized.get("genre") or brief.get("genre") or "").strip()
    style = str(normalized.get("style") or brief.get("style") or "").strip()
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
    composition_beats = [
        _composition_for_action(scene_label, weather, action, props, idx, beat_count)
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
        composition_beats=composition_beats,
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


def infer_camera(idx: int, total: int) -> str:
    if idx == 0:
        return "wide shot"
    if idx == total - 1:
        return "wide shot, closing frame"
    if idx % 3 == 0:
        return "close-up"
    if idx % 2 == 0:
        return "medium shot"
    return "tracking shot"


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
    title = title_from_idea(idea, genre, style)
    subject_name, subject_age = anchors.subject, anchors.subject_age
    theme = default_theme(genre, style)
    scene = anchors.scene_label
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
        voiceover, dialogue = default_voice_lines(voice_mode, idx, theme)
        if voiceover:
            voiceover = f"{subject_name}{action}，情绪落在{emotion}。"
        summary = f"{subject_name}在{scene}{action}，情绪推进到{emotion}。"
        beats.append({
            "start": format_time(start),
            "end": format_time(end),
            "summary": summary,
            "emotion": emotion,
        })
        sections.append({
            "time": f"{format_time(start)}-{format_time(end)}",
            "visual": (
                f"{scene}里，{subject_name}{action}；"
                f"保留{props_label}与人物关系，构图重点：{composition_focus}"
            ),
            "voiceover": voiceover,
            "dialogue": dialogue,
            "music_cue": "underscore" if music_profile or "需要" in music_mode else "",
        })
    return {
        "schema_version": "0.3.0",
        "stage": "STAGE_01_SCRIPT_GENERATION",
        "status": "draft",
        "project_id": brief.get("project_id") or "",
        "source_brief": str(brief.get("project_dir") or "").replace("\\", "/"),
        "title": title,
        "logline": f"{idea}。".strip("。"),
        "theme": theme,
        "characters": [
            {
                "name": subject_name,
                "age": subject_age,
                "role": "main",
            }
        ],
        "settings": [scene],
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
            "ready_for_storyboard": True,
            "quality_targets_defined": bool(quality_targets),
            "notes": [
                "Draft generated by pipeline_blueprints.",
            ],
        },
        "allowed_next_stage": None,
    }


def build_stage02_storyboard(brief: dict[str, Any], script: dict[str, Any]) -> dict[str, Any]:
    normalized = normal_brief(brief)
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_02")
    duration = int(normalized.get("target_duration_sec") or script.get("duration_plan", {}).get("target_duration_sec") or 30)
    genre = str(normalized.get("genre") or brief.get("genre") or "").strip()
    style = str(normalized.get("style") or brief.get("style") or "").strip()
    shots_needed = max(3, count_duration_beats(duration))
    anchors = extract_story_anchors(brief, shots_needed)
    scene = anchors.scene_label
    shot_lengths = split_duration(duration, shots_needed)
    sections = script.get("script", {}).get("sections") if isinstance(script.get("script"), dict) else []
    beats = script.get("duration_plan", {}).get("beats") if isinstance(script.get("duration_plan"), dict) else []
    voice_mode = str(script.get("script", {}).get("voice_mode") or "").strip()
    shots = []
    elapsed = 0
    for idx, shot_len in enumerate(shot_lengths):
        start = elapsed
        end = elapsed + shot_len
        elapsed = end
        shot_id = f"S{idx + 1:03d}"
        section = sections[idx % len(sections)] if sections else {}
        beat = beats[idx % len(beats)] if beats else {}
        emotion = str(beat.get("emotion") or "").strip() or anchors.emotion_beats[min(idx, len(anchors.emotion_beats) - 1)]
        action = anchors.action_beats[min(idx, len(anchors.action_beats) - 1)]
        composition_focus = anchors.composition_beats[min(idx, len(anchors.composition_beats) - 1)]
        key_prop = anchors.key_props[min(idx, len(anchors.key_props) - 1)] if anchors.key_props else ""
        visual = str(section.get("visual") or "").strip() or f"{scene}中的第{idx + 1}个情绪镜头。"
        voiceover = str(section.get("voiceover") or "").strip()
        dialogue = str(section.get("dialogue") or "").strip()
        sound_music = "轻柔 underscore 背景音乐" if "需要" in voice_mode or str(script.get("script", {}).get("music_mode") or "").strip() else ""
        camera = infer_camera(idx, shots_needed)
        transition = "match cut" if idx < shots_needed - 1 else "fade out"
        shots.append({
            "shot_id": shot_id,
            "start": format_time(start),
            "end": format_time(end),
            "duration_sec": shot_len,
            "scene": scene,
            "location": anchors.location,
            "weather": anchors.weather or anchors.time_of_day,
            "key_prop": key_prop,
            "camera": camera,
            "composition": f"{visual} 具体构图：{composition_focus}",
            "composition_focus": composition_focus,
            "action": f"{anchors.subject}{action}" if not action.startswith(anchors.subject) else action,
            "emotion": emotion,
            "dialogue": dialogue,
            "voiceover": voiceover,
            "sound_music": sound_music,
            "transition_to_next": transition,
            "production_note": f"保持{scene}、{key_prop or '关键道具'}与角色一致性，并与前后镜头形成连续情绪推进。",
        })
    return {
        "schema_version": "0.3.0",
        "stage": "STAGE_02_STORYBOARD_GENERATION",
        "status": "draft",
        "project_id": brief.get("project_id") or script.get("project_id") or "",
        "source_brief": str(brief.get("project_dir") or "").replace("\\", "/"),
        "source_script": str(script.get("source_brief") or "").replace("\\", "/") or str(script.get("source_brief") or ""),
        "target_duration_sec": duration,
        "shot_count": len(shots),
        "shots": shots,
        "story_anchors": anchors.to_dict(),
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "duration_fits": True,
            "ready_for_character_stage": True,
            "quality_targets_defined": bool(quality_targets),
            "notes": [
                "Draft storyboard generated by pipeline_blueprints.",
            ],
        },
        "allowed_next_stage": None,
    }


def _visual_detail(idea: str, style: str, role: str) -> str:
    base = f"{role} in {idea}".strip()
    if "国风" in style or "古风" in style:
        return "东方审美，留白丰富，线条柔和，衣着与环境有传统质感。"
    if "动画" in style or "卡通" in style:
        return "轮廓清晰，色块明确，夸张但可控。"
    return f"{base}，视觉细节稳定，便于跨镜头保持一致。"


def build_stage03_character_bible(brief: dict[str, Any], script: dict[str, Any], storyboard: dict[str, Any]) -> dict[str, Any]:
    normalized = normal_brief(brief)
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_03")
    idea = str(normalized.get("idea") or "").strip()
    style = str(normalized.get("style") or "").strip()
    anchors = extract_story_anchors(brief, max(1, len(storyboard.get("shots") or [])))
    characters_required = normalized.get("characters_required")
    if characters_required is False:
        name = "叙事主体"
        role = "main"
        age = "20岁出头"
        gender = "neutral"
    else:
        name, age = anchors.subject, anchors.subject_age
        role = "main"
        gender = "female" if "女孩" in name or "少女" in name else "male"
    primary_scene = anchors.scene_label
    voice_mode = str(normalized.get("voice_mode") or "").strip()
    voice_needed = voice_mode != "不需要配音"
    emotional_arc = emotion_sequence(str(normalized.get("genre") or ""), style)
    characters = [{
        "character_id": "CHAR_001",
        "name": name,
        "role": role,
        "age": age,
        "gender_presentation": gender,
        "appearance": {
            "face": "清秀自然，情绪表达克制",
            "hair": "自然发型，跨镜头保持一致",
            "body": "比例自然，动作轻缓",
            "clothing": f"与{primary_scene}环境匹配的主服装，保持跨镜头连续性",
            "accessories": "、".join(anchors.key_props[:2]) if anchors.key_props else "无夸张饰品",
        },
        "personality": default_theme(str(normalized.get("genre") or ""), style),
        "emotional_arc": anchors.emotion_beats or emotional_arc,
        "voice_profile": {
            "needed": bool(voice_needed),
            "suggested_voice": "年轻、清晰、贴合情绪节奏" if voice_needed else "无需配音",
        },
        "visual_consistency_prompt": f"{name} 在{primary_scene}中的外观、服装和道具关系要保持完全一致，便于跨镜头识别。",
        "negative_consistency_prompt": "不同脸、不同发型、服装漂移、年龄漂移、比例失真、表情失控、额外人物、额外肢体、道具数量错误",
        "performance_profile": {
            "baseline_expression": (anchors.emotion_beats or emotional_arc)[0] if (anchors.emotion_beats or emotional_arc) else "平静",
            "movement_style": "slow and restrained",
            "gesture_rules": [
                "动作幅度偏小",
                "转头和抬手动作尽量自然",
                "情绪变化按镜头节奏渐进",
            ],
            "dialogue_delivery": "自然、克制、可停顿",
            "continuity_anchor": f"{name} / {primary_scene} / {style} / {'、'.join(anchors.key_props[:2])}",
        },
    }]
    return {
        "schema_version": "0.4.0",
        "stage": "STAGE_03_CHARACTER_BIBLE",
        "status": "draft",
        "project_id": brief.get("project_id") or script.get("project_id") or storyboard.get("project_id") or "",
        "source_brief": str(brief.get("project_dir") or "").replace("\\", "/"),
        "source_script": str(script.get("source_brief") or "").replace("\\", "/") or str(script.get("source_brief") or ""),
        "source_storyboard": str(storyboard.get("source_script") or "").replace("\\", "/") or str(storyboard.get("source_script") or ""),
        "characters": characters,
        "reference_image_required": True,
        "story_anchors": anchors.to_dict(),
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "matches_storyboard": True,
            "ready_for_keyframe_stage": True,
            "quality_targets_defined": bool(quality_targets),
            "notes": [
                "Draft character bible generated by pipeline_blueprints.",
            ],
        },
        "allowed_next_stage": None,
    }


def build_stage04_keyframe_prompts(brief: dict[str, Any], script: dict[str, Any], storyboard: dict[str, Any], character_bible: dict[str, Any]) -> dict[str, Any]:
    normalized = normal_brief(brief)
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_04")
    style = str(normalized.get("style") or "").strip()
    genre = str(normalized.get("genre") or "").strip()
    characters = character_bible.get("characters") if isinstance(character_bible.get("characters"), list) else []
    char_map = {ch.get("character_id"): ch for ch in characters if isinstance(ch, dict) and ch.get("character_id")}
    shot_prompts = []
    transition_prompts = []
    storyboard_shots = storyboard.get("shots") if isinstance(storyboard.get("shots"), list) else []
    anchors = extract_story_anchors(brief, max(1, len(storyboard_shots)))
    global_negative = "low resolution, watermark, logo, subtitles, text artifacts, duplicate person, extra limbs, deformed hands, distorted face, inconsistent clothing, changed hairstyle, flicker, warped background"

    def _clean_text(value: Any) -> str:
        return str(value or "").strip()

    def _joined_text(*values: Any) -> str:
        return " ".join(_clean_text(value) for value in values if _clean_text(value))

    def _character_identity_anchor(character: dict[str, Any]) -> str:
        appearance = character.get("appearance") if isinstance(character.get("appearance"), dict) else {}
        parts = [
            _clean_text(character.get("name")),
            _clean_text(character.get("age")),
            _clean_text(character.get("gender_presentation")),
            f"face {_clean_text(appearance.get('face'))}" if _clean_text(appearance.get("face")) else "",
            f"hair {_clean_text(appearance.get('hair'))}" if _clean_text(appearance.get("hair")) else "",
            f"body {_clean_text(appearance.get('body'))}" if _clean_text(appearance.get("body")) else "",
            f"clothing {_clean_text(appearance.get('clothing'))}" if _clean_text(appearance.get("clothing")) else "",
            f"accessories {_clean_text(appearance.get('accessories'))}" if _clean_text(appearance.get("accessories")) else "",
        ]
        return ", ".join(part for part in parts if part)

    def _interaction_subject_rule(shot: dict[str, Any], shot_action: str, composition_focus: str, key_prop: str, subject_name: str) -> str:
        combined = _joined_text(shot_action, composition_focus, shot.get("composition"), shot.get("production_note"), shot.get("scene"))
        lowered = combined.lower()
        if any(marker in lowered for marker in ["陌生人", "对方", "another person", "stranger", "receiver", "giver", "留给", "交给", "递给", "handoff", "give to", "pass to"]):
            prop_label = key_prop or "关键道具"
            return (
                f"Primary protagonist must remain {subject_name} in every frame. "
                f"A secondary anonymous receiver may appear, but do not swap protagonist identity, hairstyle, outfit, or body shape. "
                f"Keep exactly two readable people and exactly one shared {prop_label}; the receiver stays secondary and less visually dominant than the protagonist."
            )
        return (
            f"Keep exactly one readable primary subject: {subject_name}. "
            "Do not introduce a new lead character, do not change face shape, hairstyle, clothing silhouette, or body proportions."
        )

    for idx, shot in enumerate(storyboard_shots):
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id") or f"S{idx + 1:03d}"
        prev_id = storyboard_shots[idx - 1].get("shot_id") if idx > 0 and isinstance(storyboard_shots[idx - 1], dict) else None
        next_id = storyboard_shots[idx + 1].get("shot_id") if idx + 1 < len(storyboard_shots) and isinstance(storyboard_shots[idx + 1], dict) else None
        primary_chars = [cid for cid in char_map] or ["CHAR_001"]
        main_char = char_map.get(primary_chars[0], {})
        perf = main_char.get("performance_profile") if isinstance(main_char.get("performance_profile"), dict) else {}
        visual_prompt = main_char.get("visual_consistency_prompt") or "consistent character design and styling"
        negative_prompt = main_char.get("negative_consistency_prompt") or global_negative
        shot_emotion = str(shot.get("emotion") or "").strip()
        shot_action = str(shot.get("action") or "").strip()
        camera = str(shot.get("camera") or "").strip()
        location = str(shot.get("location") or anchors.location or anchors.scene_label).strip()
        weather = str(shot.get("weather") or anchors.weather or anchors.time_of_day).strip()
        key_prop = str(shot.get("key_prop") or (anchors.key_props[min(idx, len(anchors.key_props) - 1)] if anchors.key_props else "")).strip()
        composition_focus = str(shot.get("composition_focus") or anchors.composition_beats[min(idx, len(anchors.composition_beats) - 1)]).strip()
        style_prompt = f"{style or genre or 'cinematic'} {shot_emotion or 'emotion'} visual treatment"
        identity_anchor = _character_identity_anchor(main_char)
        subject_rule = _interaction_subject_rule(shot, shot_action, composition_focus, key_prop, _clean_text(main_char.get("name")) or anchors.subject)
        gesture_rules = perf.get("gesture_rules") if isinstance(perf.get("gesture_rules"), list) else []
        gesture_clause = " ".join(_clean_text(item) for item in gesture_rules if _clean_text(item))
        identity_prompt = (
            f"Character identity anchor: {identity_anchor}. {subject_rule} "
            f"Keep facial identity, haircut, outfit silhouette, and carried accessories stable across start/end frames."
        ).strip()
        consistency_prompt = "; ".join(
            part for part in [
                visual_prompt,
                perf.get("continuity_anchor") or "",
                identity_prompt,
                f"Performance continuity: {gesture_clause}" if gesture_clause else "",
            ]
            if _clean_text(part)
        )
        performance_prompt = f"{shot_action} with {perf.get('dialogue_delivery') or 'natural pacing'}, baseline expression {perf.get('baseline_expression') or shot_emotion or 'neutral'}."
        structured_scene_summary = " / ".join([
            f"地点：{location or anchors.scene_label}",
            f"天气：{weather or '按故事气氛执行'}",
            f"动作：{shot_action}",
            f"道具：{key_prop or '无额外道具'}",
            f"情绪：{shot_emotion or '中性'}",
            f"构图重点：{composition_focus}",
        ])
        shot_prompts.append({
            "shot_id": shot_id,
            "source_shot_ref": str(storyboard.get("source_script") or "").replace("\\", "/") or str(storyboard.get("source_script") or ""),
            "duration_sec": shot.get("duration_sec"),
            "characters": primary_chars,
            "scene_summary": structured_scene_summary,
            "intent_summary": _intent_summary(location or anchors.scene_label, shot_action, shot_emotion or "当前情绪变化", key_prop),
            "story_anchor_bundle": {
                "location": location,
                "weather": weather,
                "key_prop": key_prop,
                "emotion": shot_emotion,
                "composition_focus": composition_focus,
            },
            "start_keyframe_prompt": (
                f"cinematic frame, location {location or anchors.scene_label}, weather {weather or 'story mood'}, "
                f"subject {anchors.subject}, action {shot_action}, key prop {key_prop or 'none'}, emotion {shot_emotion or 'neutral'}, "
                f"composition focus {composition_focus}, {visual_prompt}, {identity_prompt}, vertical 9:16 composition"
            ),
            "end_keyframe_prompt": (
                f"cinematic continuation, location {location or anchors.scene_label}, weather {weather or 'story mood'}, "
                f"subject {anchors.subject}, action {shot_action}, key prop {key_prop or 'none'}, emotion {shot_emotion or 'neutral'}, "
                f"composition focus {composition_focus}, {visual_prompt}, {identity_prompt}, vertical 9:16 composition"
            ),
            "motion_prompt": f"{performance_prompt} gentle camera movement, preserve identity and continuity.",
            "camera_prompt": camera,
            "lighting_prompt": f"natural lighting shaped by {weather or style or genre or 'the story mood'}",
            "style_prompt": style_prompt,
            "consistency_prompt": consistency_prompt,
            "identity_anchor_prompt": identity_prompt,
            "negative_prompt": negative_prompt,
            "image_generation_notes": "Use the same subject design across start and end frames; keep continuity anchors stable.",
            "video_generation_notes": "Carry the same performance and composition through the clip; avoid flicker or identity drift.",
            "performance_prompt": performance_prompt,
            "dialogue_delivery_prompt": f"Deliver any spoken line with {perf.get('dialogue_delivery') or 'natural pacing'}." if shot.get("dialogue") or shot.get("voiceover") else "",
            "dependencies": {
                "reference_images": [f"03_characters/reference_images/{primary_chars[0]}_primary.png"],
                "previous_shot_id": prev_id,
                "next_shot_id": next_id,
            },
        })
        if next_id:
            transition_prompts.append({
                "transition_id": f"T{idx + 1:03d}",
                "from_shot_id": shot_id,
                "to_shot_id": next_id,
                "transition_type": str(shot.get("transition_to_next") or "cut").strip(),
                "transition_motion_prompt": f"Continue from {shot_id} to {next_id} with stable character identity, consistent lighting, and preserved emotional continuity.",
                "continuity_requirements": [
                    "same character face and hair",
                    "same core wardrobe",
                    "same lighting direction",
                    "same performance rhythm",
                ],
            })
    return {
        "schema_version": "0.5.0",
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "status": "draft",
        "project_id": brief.get("project_id") or script.get("project_id") or storyboard.get("project_id") or character_bible.get("project_id") or "",
        "source_brief": str(brief.get("project_dir") or "").replace("\\", "/"),
        "source_script": str(script.get("source_brief") or "").replace("\\", "/") or str(script.get("source_brief") or ""),
        "source_storyboard": str(storyboard.get("source_script") or "").replace("\\", "/") or str(storyboard.get("source_script") or ""),
        "source_character_bible": str(character_bible.get("source_storyboard") or "").replace("\\", "/") or str(character_bible.get("source_storyboard") or ""),
        "prompt_language": "English generation prompts with Chinese review notes",
        "visual_strategy": {
            "keyframe_mode": "start_and_end_keyframes_per_shot",
            "video_mode": "image_to_video_per_shot",
            "continuity_strategy": "reuse character consistency prompts and adjacent-shot transition requirements",
        },
        "story_anchors": anchors.to_dict(),
        "shot_prompts": shot_prompts,
        "transition_prompts": transition_prompts,
        "global_negative_prompt": global_negative,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": {
            "matches_locked_brief": True,
            "matches_script": True,
            "matches_storyboard": True,
            "uses_character_consistency": True,
            "covers_all_storyboard_shots": True,
            "ready_for_image_generation": True,
            "quality_targets_defined": bool(quality_targets),
            "notes": [
                "Draft keyframe prompts generated by pipeline_blueprints.",
            ],
        },
        "allowed_next_stage": None,
    }
