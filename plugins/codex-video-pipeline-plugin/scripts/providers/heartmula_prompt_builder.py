#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from stage07_audio_utils import load_json, resolve_path


MANDATORY_STRUCTURES = [
    ("Intro", "Instrumental, atmospheric build"),
    ("Verse 1", "Calm vocal, narrative tone"),
    ("Pre-Chorus", "Increasing tension, emotional lift"),
    ("Chorus", "High energy, emotional peak"),
    ("Bridge", "Reflective vocal, dramatic tension"),
    ("Outro", "Fading out"),
]

STYLE_TAG_KEYWORDS = [
    ("钢琴", "Piano"),
    ("海浪", "Ocean Waves"),
    ("海边", "Seaside"),
    ("海滩", "Beach"),
    ("落日", "Sunset"),
    ("落霞", "Sunset Glow"),
    ("温暖", "Warm"),
    ("治愈", "Healing"),
    ("轻柔", "Soft"),
    ("悲伤", "Sad"),
    ("伤感", "Melancholic"),
    ("安静", "Calm"),
    ("低落", "Bittersweet"),
]


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _extract_context(manifest_path: Path, job: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    script_path = resolve_path(manifest_path, manifest.get("source_script"))
    storyboard_path = resolve_path(manifest_path, manifest.get("source_storyboard"))
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    return {
        "manifest": manifest,
        "script": script,
        "storyboard": storyboard,
        "job": job,
    }


def _derive_global_tags(context: dict[str, Any]) -> str:
    script = context["script"]
    storyboard = context["storyboard"]
    job = context["job"]
    source_texts = [
        _safe_text(job.get("music_prompt")),
        _safe_text(job.get("emotion")),
        _safe_text(script.get("logline")),
        _safe_text(script.get("theme")),
    ]
    for shot in storyboard.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        source_texts.extend([
            _safe_text(shot.get("sound_music")),
            _safe_text(shot.get("emotion")),
            _safe_text(shot.get("scene")),
        ])
    joined = " ".join(text for text in source_texts if text)

    tags = [
        "Mandopop",
        "Female",
        "Emotional",
    ]
    for keyword, tag in STYLE_TAG_KEYWORDS:
        if keyword in joined:
            tags.append(tag)
    if "悲" in joined or "告别" in joined or "低落" in joined:
        tags.append("Sad")
    if "温暖" in joined or "治愈" in joined or "重新出发" in joined:
        tags.append("Healing")
    if "钢琴" in joined:
        tags.append("Ballad")
    target_duration = ((context["manifest"].get("requirements") or {}).get("target_duration_sec")) or job.get("duration_sec")
    if target_duration:
        tags.append(f"{int(float(target_duration))}s")
    return "Global Tags: " + ", ".join(_dedupe(tags)) + "/"


def _derive_story_lines(context: dict[str, Any]) -> list[str]:
    script = context["script"]
    storyboard = context["storyboard"]
    lines: list[str] = []
    for section in (script.get("script") or {}).get("sections") or []:
        if not isinstance(section, dict):
            continue
        visual = _safe_text(section.get("visual"))
        voiceover = _safe_text(section.get("voiceover"))
        if visual:
            lines.append(visual.rstrip("。") + "。")
        if voiceover:
            lines.append(voiceover.rstrip("。") + "。")
    if not lines:
        for shot in storyboard.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            action = _safe_text(shot.get("action"))
            emotion = _safe_text(shot.get("emotion"))
            voiceover = _safe_text(shot.get("voiceover"))
            if action:
                lines.append(action.rstrip("。") + "。")
            if emotion:
                lines.append(f"心绪是{emotion}。")
            if voiceover:
                lines.append(voiceover.rstrip("。") + "。")
    return lines or ["把想说的话，轻轻放回海风里。"]


def _derive_lyrics(context: dict[str, Any]) -> str:
    story_lines = _derive_story_lines(context)
    intro_line = "（无歌词部分）"
    verse_lines = story_lines[:2] or ["海风轻轻吹过，晚霞慢慢沉落。"]
    prechorus_lines = story_lines[2:3] or ["有些话留在心里，也能慢慢被听懂。"]
    chorus_lines = story_lines[3:5] or ["我把告别交给海浪，把明天交给远方。"]
    bridge_lines = story_lines[5:6] or ["当回忆退潮以后，我终于学会不再回头。"]
    outro_lines = story_lines[6:7] or ["沿着暮色继续向前，风会带走没说完的话。"]

    sections = [
        ("Intro", "Instrumental, atmospheric build", [intro_line]),
        ("Verse 1", "Calm vocal, narrative tone", verse_lines),
        ("Pre-Chorus", "Increasing tension, emotional lift", prechorus_lines),
        ("Chorus", "High energy, emotional peak", chorus_lines),
        ("Bridge", "Reflective vocal, dramatic tension", bridge_lines),
        ("Outro", "Fading out", outro_lines),
    ]
    output: list[str] = ["Lyrics:"]
    for name, style, lines in sections:
        output.append(f"[{name}: {style}]")
        output.extend(line for line in lines if _safe_text(line))
    return "\n".join(output)


def build_heartmula_prompt(manifest_path: Path, job: dict[str, Any]) -> dict[str, str]:
    context = _extract_context(manifest_path, job)
    return {
        "global_tags": _derive_global_tags(context),
        "lyrics": _derive_lyrics(context),
    }
