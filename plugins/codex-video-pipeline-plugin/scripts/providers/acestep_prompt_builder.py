#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from stage07_audio_utils import load_json, resolve_path


GENRE_HINTS = [
    ("古风", "chinese traditional", "cinematic folk"),
    ("武侠", "chinese traditional", "heroic ballad"),
    ("海边", "mandopop", "ambient pop"),
    ("海浪", "mandopop", "ambient pop"),
    ("钢琴", "piano ballad", "mandopop"),
    ("电子", "electronic pop", "synth pop"),
]

MOOD_HINTS = [
    ("悲", "melancholic", 78, "E minor"),
    ("伤感", "wistful", 80, "E minor"),
    ("安静", "calm", 76, "C major"),
    ("温暖", "warm", 92, "G major"),
    ("治愈", "healing", 90, "G major"),
    ("热血", "uplifting", 122, "D major"),
    ("大气", "epic", 108, "D minor"),
]

INSTRUMENT_HINTS = [
    ("钢琴", "piano"),
    ("海浪", "ocean ambience"),
    ("海边", "ocean ambience"),
    ("海滩", "ocean ambience"),
    ("古筝", "guzheng"),
    ("竹笛", "bamboo flute"),
    ("二胡", "erhu"),
    ("琵琶", "pipa"),
    ("弦乐", "strings"),
]

VOCAL_HINTS = [
    ("女声", "female vocal"),
    ("男声", "male vocal"),
    ("温柔", "soft vocal"),
    ("清澈", "clear vocal"),
    ("力量", "powerful vocal"),
]

PROFILE_ALIASES = {
    "song": "song",
    "vocal": "song",
    "lyrics": "song",
    "instrumental": "instrumental",
    "pure_music": "instrumental",
    "underscore": "underscore",
    "bgm": "underscore",
}

SONG_PROFILE_HINTS = ("歌词", "演唱", "人声", "主唱", "歌曲", "主题曲", "song", "vocal", "lyrics")
INSTRUMENTAL_PROFILE_HINTS = ("纯音乐", "纯器乐", "器乐", "instrumental", "pure music", "no vocal")
UNDERSCORE_PROFILE_HINTS = ("配乐", "铺底", "背景", "bgm", "underscore", "score")


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _normalize_profile(value: Any) -> str:
    raw = _safe_text(value).lower().replace("-", "_").replace(" ", "_")
    return PROFILE_ALIASES.get(raw, "")


def _infer_profile(*values: Any) -> str:
    joined = " ".join(_safe_text(value) for value in values).lower()
    if any(keyword in joined for keyword in SONG_PROFILE_HINTS):
        return "song"
    if any(keyword in joined for keyword in INSTRUMENTAL_PROFILE_HINTS):
        return "instrumental"
    if any(keyword in joined for keyword in UNDERSCORE_PROFILE_HINTS):
        return "underscore"
    return "underscore"


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


def _source_texts(context: dict[str, Any]) -> list[str]:
    script = context["script"]
    storyboard = context["storyboard"]
    job = context["job"]
    manifest = context["manifest"]
    requirements = manifest.get("requirements") if isinstance(manifest.get("requirements"), dict) else {}
    texts = [
        _safe_text(job.get("music_prompt")),
        _safe_text(job.get("emotion")),
        _safe_text(job.get("music_profile")),
        _safe_text(requirements.get("music_mode")),
        _safe_text(requirements.get("music_profile")),
        _safe_text(script.get("logline")),
        _safe_text(script.get("theme")),
    ]
    for section in (script.get("script") or {}).get("sections") or []:
        if not isinstance(section, dict):
            continue
        texts.extend([
            _safe_text(section.get("visual")),
            _safe_text(section.get("voiceover")),
        ])
    for shot in storyboard.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        texts.extend([
            _safe_text(shot.get("sound_music")),
            _safe_text(shot.get("emotion")),
            _safe_text(shot.get("scene")),
            _safe_text(shot.get("action")),
        ])
    return [text for text in texts if text]


def _derive_profile(context: dict[str, Any], explicit_profile: str | None = None) -> str:
    manifest = context["manifest"]
    requirements = manifest.get("requirements") if isinstance(manifest.get("requirements"), dict) else {}
    job = context["job"]
    candidates = [
        explicit_profile,
        job.get("music_profile"),
        requirements.get("music_profile"),
        (manifest.get("music_provider_strategy") or {}).get("default_profile") if isinstance(manifest.get("music_provider_strategy"), dict) else "",
    ]
    for candidate in candidates:
        normalized = _normalize_profile(candidate)
        if normalized:
            return normalized
    return _infer_profile(requirements.get("music_mode"), *_source_texts(context))


def _derive_language(context: dict[str, Any]) -> str:
    joined = "\n".join(_source_texts(context))
    return "zh" if _contains_cjk(joined) else "en"


def _derive_tags(context: dict[str, Any], profile: str) -> str:
    joined = " ".join(_source_texts(context))
    genres = ["mandopop"]
    moods = ["emotional"]
    instruments = ["polished arrangement"]
    if profile == "song":
        vocals = ["female vocal"]
    else:
        vocals = ["no vocals"]
    textures = ["studio quality", "coherent structure"]

    for keyword, primary, secondary in GENRE_HINTS:
        if keyword in joined:
            genres.extend([primary, secondary])
    for keyword, mood, _, _ in MOOD_HINTS:
        if keyword in joined:
            moods.append(mood)
    for keyword, instrument in INSTRUMENT_HINTS:
        if keyword in joined:
            instruments.append(instrument)
    if profile == "song":
        for keyword, vocal in VOCAL_HINTS:
            if keyword in joined:
                vocals.append(vocal)
    if "副歌" in joined or "回眸" in joined or "hook" in joined.lower():
        textures.append("strong chorus hook")
    if "电影" in joined or "大气" in joined:
        textures.append("cinematic build")

    if profile == "song":
        textures.extend(["lyrical topline", "vocal forward"])
    elif profile == "instrumental":
        textures.extend(["instrumental arrangement", "featured melody", "no vocals"])
    else:
        textures.extend(["background underscore", "supportive arrangement", "do not overpower narration"])

    genres = _dedupe(genres)
    moods = _dedupe(moods)
    instruments = _dedupe(instruments)
    vocals = _dedupe(vocals)
    textures = _dedupe(textures)

    metadata = " ".join([
        f"[genre: {', '.join(genres)}]",
        f"[mood: {', '.join(moods)}]",
        f"[instrument: {', '.join(instruments)}]",
        f"[vocal: {', '.join(vocals)}]",
    ])
    if profile == "song":
        caption = (
            f"{vocals[0]} {genres[0]} song, {moods[0]} but melodic, "
            f"featuring {', '.join(instruments[:3])}, {', '.join(textures[:3])}."
        )
    elif profile == "instrumental":
        caption = (
            f"{genres[0]} instrumental piece, {moods[0]} and expressive, "
            f"featuring {', '.join(instruments[:3])}, {', '.join(textures[:3])}."
        )
    else:
        caption = (
            f"{genres[0]} instrumental underscore, {moods[0]} and restrained, "
            f"featuring {', '.join(instruments[:3])}, {', '.join(textures[:3])}."
        )
    return metadata + "\n" + caption


def _story_lines(context: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    script = context["script"]
    storyboard = context["storyboard"]
    for section in (script.get("script") or {}).get("sections") or []:
        if not isinstance(section, dict):
            continue
        for candidate in (section.get("voiceover"), section.get("visual")):
            text = _safe_text(candidate)
            if text:
                lines.append(text.rstrip("。") + "。")
    if not lines:
        for shot in storyboard.get("shots") or []:
            if not isinstance(shot, dict):
                continue
            for candidate in (shot.get("voiceover"), shot.get("action"), shot.get("emotion")):
                text = _safe_text(candidate)
                if text:
                    lines.append(text.rstrip("。") + "。")
    return lines or ["海风把没说完的话，慢慢吹向远方。"]


def _pick_line(lines: list[str], index: int, fallback: str) -> str:
    if index < len(lines) and _safe_text(lines[index]):
        return lines[index]
    return fallback


def _format_section_lyrics(arranged: list[tuple[str, str, str]]) -> str:
    output: list[str] = []
    for section, style, text in arranged:
        output.append(f"[{section}, {style}]")
        output.append(text)
    return "\n".join(output)


def _derive_song_lyrics(context: dict[str, Any], language: str) -> str:
    lines = _story_lines(context)
    if language == "en":
        intro_line = "(instrumental intro)"
        fallbacks = [
            "The night wind brushes my shoulder, but the words still stay unsaid.",
            "The tide slips behind us, while memory lingers in the glow.",
            "I reach out, then hold back, afraid one word will break the calm.",
            "Turn goodbye into waves, turn longing into one last look.",
            "If tomorrow pulls you away, let this tenderness follow you home.",
            "When the evening settles down, I finally learn to let go slowly.",
            "The sea breeze will remember how we once kept walking side by side.",
        ]
    else:
        intro_line = "（器乐铺陈）"
        fallbacks = [
            "晚风经过肩头，心事还没说透。",
            "潮声退到身后，回忆轻轻停留。",
            "想靠近又停手，怕一开口就失守。",
            "把告别唱成海浪，把思念唱成回眸。",
            "若明天还要远走，愿温柔陪你到最后。",
            "当夜色落在肩头，我终于学会慢慢放手。",
            "海风会记得，我们曾并肩向前走。",
        ]
    arranged = [
        ("intro", "airy instrumental", intro_line),
        ("verse", "intimate lead vocal", _pick_line(lines, 0, fallbacks[0])),
        ("verse", "intimate lead vocal", _pick_line(lines, 1, fallbacks[1])),
        ("pre-chorus", "gentle lift", _pick_line(lines, 2, fallbacks[2])),
        ("chorus", "memorable hook", _pick_line(lines, 3, fallbacks[3])),
        ("chorus", "memorable hook", _pick_line(lines, 4, fallbacks[4])),
        ("bridge", "emotional release", _pick_line(lines, 5, fallbacks[5])),
        ("outro", "fade out", _pick_line(lines, 6, fallbacks[6])),
    ]
    return _format_section_lyrics(arranged)


def _derive_instrumental_lyrics(language: str) -> str:
    if language == "en":
        arranged = [
            ("intro", "airy instrumental", "(pure instrumental intro, piano and ambience enter slowly)"),
            ("verse", "featured melody", "(let the piano introduce a clear memorable lead melody)"),
            ("verse", "featured melody", "(expand the melody with strings and texture, keep it fully instrumental)"),
            ("chorus", "melodic lift", "(open the melody wider and lift the emotion without adding vocals)"),
            ("bridge", "dynamic release", "(briefly widen dynamics and space, highlight instrumental layers)"),
            ("outro", "fade out", "(gradually pull back and leave only a soft lingering tail)"),
        ]
    else:
        arranged = [
            ("intro", "airy instrumental", "（纯器乐引子，钢琴与环境声缓慢进入）"),
            ("verse", "featured melody", "（主旋律由钢琴提出，保持清晰而可记忆的器乐线条）"),
            ("verse", "featured melody", "（延展旋律，加入弦乐和氛围层次，不使用人声）"),
            ("chorus", "melodic lift", "（旋律抬升，情绪更开阔，但保持纯音乐表达）"),
            ("bridge", "dynamic release", "（短暂拉开动态与空间，突出器乐层次变化）"),
            ("outro", "fade out", "（逐步收束，只保留余韵与环境感淡出）"),
        ]
    return _format_section_lyrics(arranged)


def _derive_underscore_lyrics(language: str) -> str:
    if language == "en":
        arranged = [
            ("intro", "airy instrumental", "(pure instrumental bed, atmosphere first, do not compete with narration)"),
            ("verse", "supportive underscore", "(keep piano and ambience close and intimate, leave room for voiceover)"),
            ("verse", "supportive underscore", "(move the melody gently, keep rhythm restrained and picture-serving)"),
            ("pre-chorus", "gentle lift", "(lift emotion slightly while keeping background space and breath)"),
            ("chorus", "restrained swell", "(open the layers a little, but do not overpower dialogue or framing)"),
            ("bridge", "cinematic support", "(expand space and tension briefly, then pull back quickly)"),
            ("outro", "fade out", "(fade away quietly and leave a soft afterglow for the ending)"),
        ]
    else:
        arranged = [
            ("intro", "airy instrumental", "（纯器乐铺底，氛围先行，避免抢对白）"),
            ("verse", "supportive underscore", "（钢琴与环境声保持近景情绪，留出旁白空间）"),
            ("verse", "supportive underscore", "（旋律轻度推进，节奏克制，继续服务画面）"),
            ("pre-chorus", "gentle lift", "（情绪微微抬升，但保持背景感与呼吸感）"),
            ("chorus", "restrained swell", "（层次稍微打开，不抢镜头与台词重心）"),
            ("bridge", "cinematic support", "（短暂扩展空间与张力，然后迅速回收）"),
            ("outro", "fade out", "（安静淡出，为画面收尾保留余韵）"),
        ]
    return _format_section_lyrics(arranged)


def _derive_lyrics(context: dict[str, Any], profile: str, language: str) -> str:
    if profile == "song":
        return _derive_song_lyrics(context, language)
    if profile == "instrumental":
        return _derive_instrumental_lyrics(language)
    return _derive_underscore_lyrics(language)


def _derive_bpm_and_key(context: dict[str, Any], profile: str) -> tuple[int, str]:
    joined = " ".join(_source_texts(context))
    defaults = {
        "song": (96, "C major"),
        "instrumental": (92, "D minor"),
        "underscore": (84, "C major"),
    }
    bpm, keyscale = defaults[profile]
    for keyword, _, candidate_bpm, candidate_key in MOOD_HINTS:
        if keyword in joined:
            bpm = candidate_bpm
            keyscale = candidate_key
            break
    return bpm, keyscale


def _derive_time_signature(context: dict[str, Any]) -> str:
    joined = " ".join(_source_texts(context)).lower()
    if "华尔兹" in joined or "waltz" in joined:
        return "3"
    return "4"


def build_acestep_prompt(
    manifest_path: Path,
    job: dict[str, Any],
    *,
    profile: str | None = None,
) -> dict[str, Any]:
    context = _extract_context(manifest_path, job)
    final_profile = _derive_profile(context, explicit_profile=profile)
    language = _derive_language(context)
    bpm, keyscale = _derive_bpm_and_key(context, final_profile)
    return {
        "profile": final_profile,
        "tags": _derive_tags(context, final_profile),
        "lyrics": _derive_lyrics(context, final_profile, language),
        "language": language,
        "bpm": bpm,
        "keyscale": keyscale,
        "timesignature": _derive_time_signature(context),
    }
