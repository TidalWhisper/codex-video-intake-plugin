from __future__ import annotations

from typing import Any


SCALAR_KEYS = ("subject", "subject_age", "location", "weather", "time_of_day", "scene_label")
LIST_KEYS = ("key_props", "action_beats", "emotion_beats", "composition_beats")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for item in values:
        text = _clean_text(item)
        if text.lower() in {"none", "null"} or text in {"无", "未指定"}:
            continue
        if text and text not in result:
            result.append(text)
    return result


def _normalize_story_anchors(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {}
    return {
        **{key: _clean_text(candidate.get(key)) for key in SCALAR_KEYS},
        **{key: _clean_list(candidate.get(key)) for key in LIST_KEYS},
    }


def _derive_from_script(source: dict[str, Any]) -> dict[str, Any]:
    characters = source.get("characters") if isinstance(source.get("characters"), list) else []
    settings = source.get("settings") if isinstance(source.get("settings"), list) else []
    duration_plan = source.get("duration_plan") if isinstance(source.get("duration_plan"), dict) else {}
    beats = duration_plan.get("beats") if isinstance(duration_plan.get("beats"), list) else []
    primary_character = characters[0] if characters and isinstance(characters[0], dict) else {}
    primary_scene = _clean_text(settings[0]) if settings else _clean_text((source.get("creative_contract") or {}).get("scene"))
    return {
        "subject": _clean_text(primary_character.get("name")),
        "subject_age": _clean_text(primary_character.get("age")),
        "location": primary_scene,
        "weather": "",
        "time_of_day": "",
        "scene_label": primary_scene,
        "key_props": [],
        "action_beats": _clean_list([beat.get("summary") for beat in beats if isinstance(beat, dict)]),
        "emotion_beats": _clean_list([beat.get("emotion") for beat in beats if isinstance(beat, dict)]),
        "composition_beats": [],
    }


def _derive_from_storyboard_like(source: dict[str, Any]) -> dict[str, Any]:
    shots = source.get("shots") if isinstance(source.get("shots"), list) else []
    first_shot = next((shot for shot in shots if isinstance(shot, dict)), {})
    return {
        "subject": "",
        "subject_age": "",
        "location": _clean_text(first_shot.get("location")),
        "weather": _clean_text(first_shot.get("weather")),
        "time_of_day": "",
        "scene_label": _clean_text(first_shot.get("scene")),
        "key_props": _clean_list([shot.get("key_prop") for shot in shots if isinstance(shot, dict)]),
        "action_beats": _clean_list([shot.get("action") for shot in shots if isinstance(shot, dict)]),
        "emotion_beats": _clean_list([shot.get("emotion") for shot in shots if isinstance(shot, dict)]),
        "composition_beats": _clean_list([shot.get("composition") for shot in shots if isinstance(shot, dict)]),
    }


def _candidate_story_anchors(source: dict[str, Any]) -> dict[str, Any]:
    direct = _normalize_story_anchors(source.get("story_anchors"))
    if any(direct.get(key) for key in (*SCALAR_KEYS, *LIST_KEYS)):
        return direct
    if isinstance(source.get("shots"), list):
        return _derive_from_storyboard_like(source)
    if isinstance(source.get("duration_plan"), dict) or isinstance(source.get("script"), dict):
        return _derive_from_script(source)
    return {}


def resolve_upstream_story_anchors(*sources: dict[str, Any] | None) -> dict[str, Any]:
    resolved: dict[str, Any] = {key: "" for key in SCALAR_KEYS}
    for key in LIST_KEYS:
        resolved[key] = []

    for source in sources:
        if not isinstance(source, dict):
            continue
        candidate = _candidate_story_anchors(source)
        if not candidate:
            continue
        for key in SCALAR_KEYS:
            if not resolved[key] and candidate.get(key):
                resolved[key] = candidate[key]
        for key in LIST_KEYS:
            existing = resolved[key] if isinstance(resolved.get(key), list) else []
            for item in candidate.get(key) or []:
                if item and item not in existing:
                    existing.append(item)
            resolved[key] = existing
    return resolved
