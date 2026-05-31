from __future__ import annotations

from typing import Any

from pipeline_blueprints import extract_story_anchors


GENERIC_TEMPLATE_PHRASES = (
    "海边女孩",
    "核心场景",
    "进入故事空间",
    "当前情绪节点推进故事",
    "动作与情绪逐步变化",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_clean_text(item) for item in values if _clean_text(item)]


def has_template_leak(value: Any) -> bool:
    text = _clean_text(value)
    return bool(text) and any(term in text for term in GENERIC_TEMPLATE_PHRASES)


def _usable_text(value: Any) -> str:
    text = _clean_text(value)
    return "" if has_template_leak(text) else text


def _usable_list(values: Any) -> list[str]:
    return [item for item in _clean_list(values) if not has_template_leak(item)]


def style_label_from_sources(brief: dict[str, Any], *sources: dict[str, Any] | None) -> str:
    normalized = brief.get("normalized") if isinstance(brief.get("normalized"), dict) else {}
    candidates = [
        normalized.get("style"),
        brief.get("style"),
    ]
    for source in sources:
        if not isinstance(source, dict):
            continue
        candidates.extend([
            source.get("style"),
            source.get("visual_family_hint"),
            (source.get("compiled_requirements") or {}).get("visual_family_hint") if isinstance(source.get("compiled_requirements"), dict) else None,
        ])
    for candidate in candidates:
        text = _clean_text(candidate)
        if text:
            return text
    return "写实电影感"


def pick_story_anchors(brief: dict[str, Any], beat_count: int, *sources: dict[str, Any] | None) -> dict[str, Any]:
    fallback = extract_story_anchors(brief, max(1, beat_count)).to_dict()
    chosen = None
    for source in sources:
        if isinstance(source, dict) and isinstance(source.get("story_anchors"), dict):
            chosen = dict(source["story_anchors"])
            break
    raw = chosen or fallback
    return {
        "subject": _usable_text(raw.get("subject")) or _clean_text(fallback.get("subject")),
        "subject_age": _usable_text(raw.get("subject_age")) or _clean_text(fallback.get("subject_age")),
        "location": _usable_text(raw.get("location")) or _clean_text(fallback.get("location")),
        "weather": _usable_text(raw.get("weather")) or _clean_text(fallback.get("weather")),
        "time_of_day": _usable_text(raw.get("time_of_day")) or _clean_text(fallback.get("time_of_day")),
        "scene_label": _usable_text(raw.get("scene_label")) or _clean_text(fallback.get("scene_label")),
        "key_props": _usable_list(raw.get("key_props")) or _clean_list(fallback.get("key_props")),
        "action_beats": _usable_list(raw.get("action_beats")) or _clean_list(fallback.get("action_beats")),
        "emotion_beats": _usable_list(raw.get("emotion_beats")) or _clean_list(fallback.get("emotion_beats")),
        "composition_beats": _usable_list(raw.get("composition_beats")) or _clean_list(fallback.get("composition_beats")),
    }


def shot_anchor_bundle(
    anchors: dict[str, Any],
    index: int,
    *,
    shot: dict[str, Any] | None = None,
    shot_prompt: dict[str, Any] | None = None,
) -> dict[str, str]:
    shot = shot if isinstance(shot, dict) else {}
    shot_prompt = shot_prompt if isinstance(shot_prompt, dict) else {}
    prompt_bundle = shot_prompt.get("story_anchor_bundle") if isinstance(shot_prompt.get("story_anchor_bundle"), dict) else {}
    props = _clean_list(prompt_bundle.get("key_props")) or _clean_list(shot.get("key_props")) or _clean_list(anchors.get("key_props"))
    key_prop = _clean_text(prompt_bundle.get("key_prop") or shot.get("key_prop") or (props[0] if props else ""))
    emotions = _clean_list(anchors.get("emotion_beats"))
    compositions = _clean_list(anchors.get("composition_beats"))
    actions = _clean_list(anchors.get("action_beats"))
    return {
        "location": _clean_text(prompt_bundle.get("location") or shot.get("location") or anchors.get("location") or anchors.get("scene_label")),
        "weather": _clean_text(prompt_bundle.get("weather") or shot.get("weather") or anchors.get("weather")),
        "key_prop": key_prop or (props[0] if props else ""),
        "emotion": _clean_text(prompt_bundle.get("emotion") or shot.get("emotion") or (emotions[min(index, len(emotions) - 1)] if emotions else "")),
        "composition_focus": _clean_text(prompt_bundle.get("composition_focus") or shot.get("composition_focus") or (compositions[min(index, len(compositions) - 1)] if compositions else "")),
        "action": _clean_text(shot_prompt.get("action") or shot.get("action") or (actions[min(index, len(actions) - 1)] if actions else "")),
    }


def key_props_text(*values: Any) -> str:
    result: list[str] = []
    for value in values:
        if isinstance(value, list):
            items = value
        else:
            items = [value]
        for item in items:
            text = _clean_text(item)
            if text and text not in result:
                result.append(text)
    return "、".join(result)


def build_continuity_anchor_text(subject: str, scene_label: str, style_label: str, key_props: list[str]) -> str:
    prop_text = key_props_text(key_props)
    pieces = [subject, scene_label, style_label]
    if prop_text:
        pieces.append(prop_text)
    return " / ".join(_clean_text(piece) for piece in pieces if _clean_text(piece))
