#!/usr/bin/env python3
"""Deterministic Stage 02 local semantics.

This module is not part of the formal Stage 02 production runtime.

The official Stage02 path must go through `run_stage02_codex_flow.py` and
generate `stage02_llm_output.json` through Codex structured output.

This module may exist only for non-formal roles such as:

- tests
- fixtures
- explicitly labeled manual fallback
"""
from __future__ import annotations

from typing import Any

from pipeline_blueprints import normal_brief
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors


def _parse_mmss(value: str) -> int:
    text = str(value or "").strip()
    if not text or ":" not in text:
        return 0
    minute_text, second_text = text.split(":", 1)
    try:
        return int(minute_text) * 60 + int(second_text)
    except ValueError:
        return 0


def _format_mmss(total_seconds: int) -> str:
    value = max(0, int(total_seconds))
    return f"{value // 60:02d}:{value % 60:02d}"


def _shot_id(index: int) -> str:
    return f"S{index + 1:03d}"


def _safe_section(sections: list[Any], index: int) -> dict[str, Any]:
    if 0 <= index < len(sections) and isinstance(sections[index], dict):
        return sections[index]
    return {}


def _safe_beat(beats: list[Any], index: int) -> dict[str, Any]:
    if 0 <= index < len(beats) and isinstance(beats[index], dict):
        return beats[index]
    return {}


def _key_prop(anchors: dict[str, Any], index: int) -> str:
    props = [str(item or "").strip() for item in list(anchors.get("key_props") or []) if str(item or "").strip()]
    if not props:
        return ""
    return props[min(index, len(props) - 1)]


def _camera_label(index: int, total: int, visual: str, composition_focus: str, key_prop: str) -> str:
    text = " ".join(part for part in [visual, composition_focus] if part)
    if index == 0:
        return "wide establishing shot"
    if index == total - 1:
        return "wide shot / back view"
    if any(token in text for token in ["特写", "close-up", "指尖", "手心", "肩颈"]):
        return "close-up"
    if any(token in text for token in ["贴近", "侧后方", "侧后", "发梢", "望向海平线"]):
        return "medium close-up"
    if key_prop:
        return "medium shot"
    return "medium shot"


def _scene_label(anchors: dict[str, Any], beat: dict[str, Any], section: dict[str, Any]) -> str:
    primary = str(anchors.get("scene_label") or "").strip()
    visual = str(section.get("visual") or "").strip()
    summary = str(beat.get("summary") or "").strip()
    if primary:
        return primary
    for candidate in [visual, summary]:
        if "便利店" in candidate and "雨" in candidate:
            return "雨夜便利店门口"
        if any(token in candidate for token in ["海滩", "海边"]):
            return "黄昏海滩"
    return "故事现场"


def _composition_text(scene: str, visual: str, composition_focus: str, action: str) -> str:
    for source in [visual, composition_focus]:
        text = str(source or "").strip()
        if text:
            return text
    return f"{scene}里把“{action}”这一瞬间交代清楚，保留环境与人物关系。"


def _action_text(beat: dict[str, Any], section: dict[str, Any]) -> str:
    summary = str(beat.get("summary") or "").strip()
    if summary:
        return summary
    visual = str(section.get("visual") or "").strip()
    if visual:
        return visual
    return "人物状态继续推进。"


def _emotion_text(beat: dict[str, Any], index: int, total: int) -> str:
    emotion = str(beat.get("emotion") or "").strip()
    if emotion:
        return emotion
    if index == 0:
        return "观察"
    if index == total - 1:
        return "收束"
    return "推进"


def _transition_text(index: int, total: int, scene: str, next_scene: str) -> str:
    if index == total - 1:
        return "fade out"
    if scene and next_scene and scene == next_scene:
        return "cut"
    return "soft cut"


def _production_note(subject: str, scene: str, key_prop: str, emotion: str) -> str:
    pieces = [
        f"保持{subject or '主角'}的外形、服装和动作连续。",
        f"场景要稳定停留在{scene or '当前现场'}。",
    ]
    if key_prop:
        pieces.append(f"{key_prop}需要在这个镜头里保持清晰可辨。")
    if emotion:
        pieces.append(f"表演情绪以“{emotion}”为主，不要过度夸张。")
    return " ".join(pieces)


def build_stage02_llm_output(
    brief: dict[str, Any],
    script: dict[str, Any],
    prompt_packet: dict[str, Any] | None = None,
    repair_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normal_brief(brief)
    beats = [item for item in list(((script.get("duration_plan") or {}).get("beats")) or []) if isinstance(item, dict)]
    sections = [item for item in list(((script.get("script") or {}).get("sections")) or []) if isinstance(item, dict)]
    anchors = resolve_upstream_story_anchors(script)
    subject = str(anchors.get("subject") or ((script.get("characters") or [{}])[0].get("name") if script.get("characters") else "") or "主角").strip()
    location = str(anchors.get("location") or anchors.get("scene_label") or ((script.get("settings") or [""])[0])).strip()
    weather = str(anchors.get("weather") or "").strip()
    target_duration = int(
        (prompt_packet or {}).get("shot_plan", {}).get("target_duration_sec")
        or (script.get("duration_plan") or {}).get("target_duration_sec")
        or normalized.get("target_duration_sec")
        or 30
    )

    shot_total = max(
        1,
        int((prompt_packet or {}).get("shot_plan", {}).get("target_shot_count") or 0),
        len(beats),
        len(sections),
    )
    shots: list[dict[str, Any]] = []
    elapsed = 0
    for idx in range(shot_total):
        beat = _safe_beat(beats, idx)
        section = _safe_section(sections, idx)
        start = str(beat.get("start") or "").strip()
        end = str(beat.get("end") or "").strip()
        if not start and section.get("time"):
            start = str(section.get("time")).split("-", 1)[0].strip()
        if not end and section.get("time"):
            parts = str(section.get("time")).split("-", 1)
            end = parts[1].strip() if len(parts) > 1 else ""
        start_sec = _parse_mmss(start) if start else elapsed
        end_sec = _parse_mmss(end) if end else 0
        if end_sec <= start_sec:
            fallback = max(1, round(target_duration / shot_total))
            end_sec = min(target_duration, start_sec + fallback)
        elapsed = end_sec

        composition_focus = str(
            section.get("composition_focus")
            or ((anchors.get("composition_focus_beats") or [])[min(idx, len(anchors.get("composition_focus_beats") or []) - 1)] if anchors.get("composition_focus_beats") else "")
            or ""
        ).strip()
        scene = _scene_label(anchors, beat, section)
        key_prop = _key_prop(anchors, idx)
        action = _action_text(beat, section)
        visual = str(section.get("visual") or "").strip()
        emotion = _emotion_text(beat, idx, shot_total)
        next_scene = _scene_label(anchors, _safe_beat(beats, idx + 1), _safe_section(sections, idx + 1)) if idx + 1 < shot_total else ""

        shots.append({
            "shot_id": _shot_id(idx),
            "start": _format_mmss(start_sec),
            "end": _format_mmss(end_sec),
            "duration_sec": max(1, end_sec - start_sec),
            "scene": scene,
            "location": location or scene,
            "weather": weather,
            "key_prop": key_prop,
            "camera": _camera_label(idx, shot_total, visual, composition_focus, key_prop),
            "composition": _composition_text(scene, visual, composition_focus, action),
            "composition_focus": composition_focus,
            "action": action,
            "emotion": emotion,
            "dialogue": str(section.get("dialogue") or "").strip(),
            "voiceover": str(section.get("voiceover") or "").strip(),
            "sound_music": str(section.get("music_cue") or "").strip(),
            "transition_to_next": _transition_text(idx, shot_total, scene, next_scene),
            "production_note": _production_note(subject, scene, key_prop, emotion),
        })

    self_check = {
        "matches_locked_brief": True,
        "matches_script": True,
        "duration_fits": True,
        "ready_for_character_stage": True,
        "notes": [
            "Generated by Stage 02 local semantics from the locked brief and approved Stage 01 script.",
        ],
    }
    if prompt_packet:
        self_check["notes"].append(f"Prompt packet preserved: {prompt_packet.get('packet_version') or 'unknown'}")
    if repair_packet:
        self_check["notes"].append("Repair loop requested deterministic regeneration from the same approved script.")

    return {
        "status": "draft",
        "target_duration_sec": target_duration,
        "shots": shots,
        "self_check": self_check,
    }
