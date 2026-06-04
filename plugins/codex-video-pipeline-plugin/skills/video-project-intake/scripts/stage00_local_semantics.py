#!/usr/bin/env python3
"""Deterministic Stage 00 local semantics.

Stage 00 is a tightly constrained intake wizard. To avoid recursive Codex CLI
deadlocks in desktop environments, we interpret Stage 00 locally while keeping
the same prompt-packet -> structured-output -> writer/validator artifact chain.
"""
from __future__ import annotations

import re
from typing import Any

from stage00_intake_common import QUESTION_KEYS, canonical_question_block, empty_brief_normalized

TARGET_DURATION_OPTIONS = {
    "A": ("15秒", 15),
    "B": ("30秒", 30),
    "C": ("60秒", 60),
    "D": ("90秒", 90),
    "E": ("120秒", 120),
    "F": ("180秒", 180),
    "G": ("300秒", 300),
}

GENRE_OPTIONS = {
    "A": "剧情短片",
    "B": "悬疑",
    "C": "恐怖惊悚",
    "D": "科幻",
    "E": "爱情",
    "F": "搞笑",
    "G": "治愈",
    "H": "励志",
    "I": "广告宣传",
    "J": "产品展示",
    "K": "纪录片",
    "L": "教育科普",
    "M": "国风/古风",
    "N": "奇幻",
    "O": "动漫短片",
    "P": "音乐MV",
}

STYLE_OPTIONS = {
    "A": "写实电影感",
    "B": "短剧爽感",
    "C": "日系动画风（日本动漫感）",
    "D": "国漫动画风（中国动画/新国风）",
    "E": "美式动画/卡通风（欧美动画感）",
    "F": "国风水墨/古风",
    "G": "赛博朋克",
    "H": "暗黑惊悚",
    "I": "温暖治愈",
    "J": "纪录片质感",
    "K": "广告高级感",
    "L": "游戏CG感",
    "M": "低饱和现实主义",
    "N": "高饱和潮流感",
}

ASPECT_RATIO_OPTIONS = {
    "A": ("9:16 竖屏", "9:16"),
    "B": ("16:9 横屏", "16:9"),
    "C": ("1:1 方屏", "1:1"),
    "D": ("4:5 竖图信息流", "4:5"),
    "E": ("21:9 宽银幕", "21:9"),
}

RESOLUTION_OPTIONS = {
    "1": "720P",
    "2": "1080P",
    "3": "2K",
    "4": "4K",
}

CHARACTER_OPTIONS = {
    "A": ("有固定主角/人物", True),
    "B": ("没有固定人物，以场景/物体/氛围为主", False),
    "C": ("由模型根据故事自动判断", "auto"),
    "D": ("不确定", "unknown"),
}

VOICE_OPTIONS = {
    "A": ("不需要配音", False),
    "B": ("只需要旁白", True),
    "C": ("只需要角色对白", True),
    "D": ("旁白 + 角色对白都需要", True),
    "E": ("不确定，先由模型建议", "recommend"),
}

MUSIC_OPTIONS = {
    "A": ("不需要", "", False),
    "B1": ("需要，歌曲（song）", "song", True),
    "B2": ("需要，纯音乐（instrumental）", "instrumental", True),
    "B3": ("需要，背景配乐（underscore）", "underscore", True),
    "C": ("由模型根据题材自动建议", "", "recommend"),
}

FINAL_OUTPUT_OPTIONS = {
    "A": "只要剧本",
    "B": "剧本 + 分镜脚本",
    "C": "剧本 + 分镜 + 关键帧提示词",
    "D": "生成关键帧图片素材包",
    "E": "生成视频片段素材包",
    "F": "合成粗剪成片",
    "G": "输出完整素材工程包，方便人工剪辑",
}


def _base_output(question_key: str, raw_input: str) -> dict[str, Any]:
    return {
        "answered_question_key": question_key,
        "user_answer_entry": {
            "raw_input": raw_input,
            "selected_option": "",
            "free_text_notes": "",
        },
        "user_answers_patch": {},
        "normalized_patch": {},
        "missing_required_fields": [],
        "required_fields_complete": False,
        "status": "collecting",
        "next_question_key": question_key,
        "next_prompt_text": canonical_question_block(question_key),
        "needs_followup": False,
        "followup_reason": "",
        "completion_summary": "",
    }


def _normalized_reply(raw: str) -> str:
    return str(raw or "").strip()


def _compact_reply(raw: str) -> str:
    return re.sub(r"\s+", "", _normalized_reply(raw)).upper()


def _selected_option(raw: str, allowed: set[str]) -> str:
    compact = _compact_reply(raw)
    return compact if compact in allowed else ""


def _next_question_key(current_question_key: str) -> str:
    index = QUESTION_KEYS.index(current_question_key)
    return QUESTION_KEYS[index + 1] if index + 1 < len(QUESTION_KEYS) else ""


def _missing_after(state: dict[str, Any], question_key: str, accepted: bool) -> list[str]:
    if not accepted:
        return list(state.get("missing_required_fields") or QUESTION_KEYS)
    user_answers = dict(state.get("user_answers") or {})
    user_answers[question_key] = "__answered__"
    return [key for key in QUESTION_KEYS if key not in user_answers]


def _finish(state: dict[str, Any], output: dict[str, Any], *, question_key: str, accepted: bool) -> dict[str, Any]:
    missing = _missing_after(state, question_key, accepted)
    output["missing_required_fields"] = missing
    if not accepted:
        output["required_fields_complete"] = False
        output["status"] = "collecting"
        output["next_question_key"] = question_key
        output["next_prompt_text"] = canonical_question_block(question_key)
        return output

    if not missing and question_key == "final_output":
        output["required_fields_complete"] = True
        output["status"] = "draft_ready"
        output["next_question_key"] = ""
        output["next_prompt_text"] = canonical_question_block("final_confirmation")
        return output

    next_key = _next_question_key(question_key)
    output["required_fields_complete"] = False
    output["status"] = "collecting"
    output["next_question_key"] = next_key
    output["next_prompt_text"] = canonical_question_block(next_key)
    return output


def _extract_duration(raw: str) -> tuple[str, int] | None:
    text = _normalized_reply(raw)
    compact = _compact_reply(raw)
    if compact in TARGET_DURATION_OPTIONS:
        return TARGET_DURATION_OPTIONS[compact]

    minute_second = re.search(r"(?P<minute>\d+)\s*(?:分钟|分)(?P<second>\d+)?\s*秒?", text)
    if minute_second:
        minute = int(minute_second.group("minute"))
        second = int(minute_second.group("second") or 0)
        total = minute * 60 + second
        label = f"{minute}分{second}秒" if second else f"{minute}分钟"
        return label, total

    clock = re.search(r"(?P<minute>\d+)\s*:\s*(?P<second>\d{1,2})", text)
    if clock:
        minute = int(clock.group("minute"))
        second = int(clock.group("second"))
        return f"{minute}分{second}秒", minute * 60 + second

    seconds = re.search(r"(?P<second>\d+)\s*秒", text)
    if seconds:
        total = int(seconds.group("second"))
        return f"{total}秒", total
    return None


def _parse_text_or_option(
    raw: str,
    *,
    options: dict[str, str],
    custom_option: str | None = None,
) -> tuple[str, str, str, bool]:
    text = _normalized_reply(raw)
    selected = _selected_option(raw, set(options) | ({custom_option} if custom_option else set()))
    if selected in options:
        return selected, options[selected], "", True
    if custom_option and selected == custom_option:
        return selected, "", "", False
    if text:
        return "", text, text, True
    return "", "", "", False


def _parse_visual_spec(raw: str) -> tuple[str, dict[str, str], str, str | None]:
    text = _normalized_reply(raw)
    compact = _compact_reply(raw)
    if "默认" in text or "推荐" in text:
        return "A2", {
            "aspect_ratio_label": "9:16 竖屏",
            "aspect_ratio": "9:16",
            "resolution_label": "1080P",
            "resolution": "1080P",
        }, "", None

    combined = re.fullmatch(r"([A-F])([1-5])", compact)
    if combined:
        letter = combined.group(1)
        digit = combined.group(2)
        ratio_label, ratio_value = ASPECT_RATIO_OPTIONS.get(letter, ("", ""))
        resolution_label = RESOLUTION_OPTIONS.get(digit, "")
        if letter == "F" and ":" not in text:
            return "F" + digit, {}, "", "请补充自定义画面比例，例如 2.39:1 + 1080P。"
        if digit == "5" and resolution_label == "":
            return letter + digit, {}, "", "请补充自定义输出画质。"
        if digit == "5":
            return letter + digit, {}, "", "请补充自定义输出画质。"
        if letter not in ASPECT_RATIO_OPTIONS or digit not in RESOLUTION_OPTIONS:
            return letter + digit, {}, "", "请同时给出有效的画面比例和输出画质。"
        return letter + digit, {
            "aspect_ratio_label": ratio_label,
            "aspect_ratio": ratio_value,
            "resolution_label": resolution_label,
            "resolution": resolution_label,
        }, "", None

    ratio_match = re.search(r"(\d+\s*:\s*\d+)", text)
    resolution_match = re.search(r"(720P|1080P|2K|4K)", text, re.I)
    ratio_value = ratio_match.group(1).replace(" ", "") if ratio_match else ""
    resolution_value = resolution_match.group(1).upper() if resolution_match else ""
    if ratio_value and resolution_value:
        ratio_label = next((label for label, value in ASPECT_RATIO_OPTIONS.values() if value == ratio_value), ratio_value)
        resolution_label = resolution_value
        return "", {
            "aspect_ratio_label": ratio_label,
            "aspect_ratio": ratio_value,
            "resolution_label": resolution_label,
            "resolution": resolution_value,
        }, text, None
    if ratio_value and not resolution_value:
        return "", {}, text, "请补充输出画质，例如 720P、1080P、2K 或 4K。"
    if resolution_value and not ratio_value:
        return "", {}, text, "请补充画面比例，例如 9:16、16:9 或 1:1。"
    return "", {}, text, "请同时给出画面比例和输出画质，例如 A2 或 16:9 + 1080P。"


def _parse_characters(raw: str) -> tuple[str, dict[str, Any], dict[str, str], bool]:
    text = _normalized_reply(raw)
    match = re.match(r"^\s*([A-Da-d])(?:[\s,，。:：;；-]*)(.*)$", text)
    note = ""
    if match:
        selected = match.group(1).upper()
        note = match.group(2).strip()
    elif "没有固定人物" in text or "以场景" in text or "氛围为主" in text:
        selected = "B"
    elif "模型" in text and "判断" in text:
        selected = "C"
    elif "不确定" in text:
        selected = "D"
    elif text:
        selected = "A"
        note = text
    else:
        return "", {}, {}, False
    mode, required = CHARACTER_OPTIONS[selected]
    user_patch: dict[str, Any] = {"characters": selected}
    if note:
        user_patch["characters_note"] = note
    normalized = {
        "characters_mode": mode,
        "characters_required": required,
    }
    return selected, user_patch, normalized, True


def _parse_voice(raw: str) -> tuple[str, dict[str, Any], bool]:
    text = _normalized_reply(raw)
    selected = _selected_option(raw, set(VOICE_OPTIONS))
    if not selected:
        if "不需要配音" in text:
            selected = "A"
        elif "只需要旁白" in text:
            selected = "B"
        elif "只需要角色对白" in text:
            selected = "C"
        elif "旁白" in text and "对白" in text:
            selected = "D"
        elif "建议" in text or "不确定" in text:
            selected = "E"
    if not selected:
        return "", {}, False
    mode, required = VOICE_OPTIONS[selected]
    return selected, {
        "voice_mode": mode,
        "voice_required": required,
    }, True


def _parse_music(raw: str) -> tuple[str, dict[str, Any], bool]:
    text = _normalized_reply(raw)
    compact = _compact_reply(raw)
    selected = compact if compact in MUSIC_OPTIONS else ""
    if not selected:
        if "不需要" in text:
            selected = "A"
        elif "SONG" in compact or "歌曲" in text:
            selected = "B1"
        elif "INSTRUMENTAL" in compact or "纯音乐" in text:
            selected = "B2"
        elif "UNDERSCORE" in compact or "背景配乐" in text or "氛围音乐" in text:
            selected = "B3"
        elif "建议" in text or "模型" in text:
            selected = "C"
    if not selected:
        return "", {}, False
    mode, profile, required = MUSIC_OPTIONS[selected]
    return selected, {
        "music_mode": mode,
        "music_profile": profile,
        "music_required": required,
    }, True


def evaluate_intake_turn(state: dict[str, Any], user_reply: str) -> dict[str, Any]:
    question_key = str(state.get("current_question_key") or "idea")
    raw = _normalized_reply(user_reply)
    output = _base_output(question_key, raw)
    output["user_answer_entry"]["free_text_notes"] = raw

    if question_key == "idea":
        if not raw:
            output["needs_followup"] = True
            output["followup_reason"] = "idea_missing"
            output["completion_summary"] = "故事想法仍为空，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = {"idea": raw}
        output["normalized_patch"] = {"idea": raw}
        output["completion_summary"] = "故事想法已记录，继续询问目标时长。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "target_duration":
        parsed = _extract_duration(raw)
        selected = _selected_option(raw, set(TARGET_DURATION_OPTIONS) | {"H"})
        output["user_answer_entry"]["selected_option"] = selected
        if selected == "H" and parsed is None:
            output["needs_followup"] = True
            output["followup_reason"] = "custom_duration_missing_value"
            output["completion_summary"] = "已识别为自定义时长，但仍缺少具体时长。"
            return _finish(state, output, question_key=question_key, accepted=False)
        if parsed is None:
            output["needs_followup"] = True
            output["followup_reason"] = "duration_unrecognized"
            output["completion_summary"] = "目标时长仍无法识别，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        label, seconds = parsed
        output["user_answers_patch"] = {"target_duration": selected or raw}
        output["normalized_patch"] = {
            "target_duration_label": label,
            "target_duration_sec": seconds,
        }
        output["completion_summary"] = "目标时长已记录，继续询问视频题材。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "genre":
        selected, canonical, notes, accepted = _parse_text_or_option(raw, options=GENRE_OPTIONS, custom_option="Q")
        output["user_answer_entry"]["selected_option"] = selected
        output["user_answer_entry"]["free_text_notes"] = notes
        if not accepted:
            output["needs_followup"] = True
            output["followup_reason"] = "genre_missing"
            output["completion_summary"] = "视频题材仍不明确，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = {"genre": selected or raw}
        output["normalized_patch"] = {"genre": canonical}
        output["completion_summary"] = "视频题材已记录，继续询问视频风格。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "style":
        selected, canonical, notes, accepted = _parse_text_or_option(raw, options=STYLE_OPTIONS, custom_option="O")
        output["user_answer_entry"]["selected_option"] = selected
        output["user_answer_entry"]["free_text_notes"] = notes
        if not accepted:
            output["needs_followup"] = True
            output["followup_reason"] = "style_missing"
            output["completion_summary"] = "视频风格仍不明确，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = {"style": selected or raw}
        output["normalized_patch"] = {"style": canonical}
        output["completion_summary"] = "视频风格已记录，继续询问画面规格。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "visual_spec":
        selected, normalized, notes, followup_message = _parse_visual_spec(raw)
        output["user_answer_entry"]["selected_option"] = selected
        output["user_answer_entry"]["free_text_notes"] = notes
        if followup_message:
            output["needs_followup"] = True
            output["followup_reason"] = followup_message
            output["completion_summary"] = "画面规格信息仍不完整，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = {"visual_spec": selected or raw}
        output["normalized_patch"] = normalized
        output["completion_summary"] = "画面规格已记录，继续询问固定人物需求。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "characters":
        selected, user_patch, normalized, accepted = _parse_characters(raw)
        output["user_answer_entry"]["selected_option"] = selected
        output["user_answer_entry"]["free_text_notes"] = str(user_patch.get("characters_note") or "")
        if not accepted:
            output["needs_followup"] = True
            output["followup_reason"] = "characters_missing"
            output["completion_summary"] = "固定人物需求仍不明确，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = user_patch
        output["normalized_patch"] = normalized
        output["completion_summary"] = "固定人物需求已记录，继续询问配音需求。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "voice":
        selected, normalized, accepted = _parse_voice(raw)
        output["user_answer_entry"]["selected_option"] = selected
        if not accepted:
            output["needs_followup"] = True
            output["followup_reason"] = "voice_missing"
            output["completion_summary"] = "配音需求仍不明确，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = {"voice": selected or raw}
        output["normalized_patch"] = normalized
        output["completion_summary"] = "配音需求已记录，继续询问背景音乐需求。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "music":
        selected, normalized, accepted = _parse_music(raw)
        output["user_answer_entry"]["selected_option"] = selected
        if not accepted:
            output["needs_followup"] = True
            output["followup_reason"] = "music_missing"
            output["completion_summary"] = "背景音乐需求仍不明确，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = {"music": selected or raw}
        output["normalized_patch"] = normalized
        output["completion_summary"] = "背景音乐需求已记录，继续询问最终输出。"
        return _finish(state, output, question_key=question_key, accepted=True)

    if question_key == "final_output":
        selected = _selected_option(raw, set(FINAL_OUTPUT_OPTIONS))
        canonical = FINAL_OUTPUT_OPTIONS.get(selected or "", "")
        output["user_answer_entry"]["selected_option"] = selected
        if not canonical:
            output["needs_followup"] = True
            output["followup_reason"] = "final_output_missing"
            output["completion_summary"] = "最终输出仍不明确，需要继续收集。"
            return _finish(state, output, question_key=question_key, accepted=False)
        output["user_answers_patch"] = {"final_output": selected}
        output["normalized_patch"] = {"final_output": canonical}
        output["completion_summary"] = "9 项基础需求已齐备，可以进入 Brief 汇总确认。"
        return _finish(state, output, question_key=question_key, accepted=True)

    raise SystemExit(f"ERROR: unsupported Stage 00 question key: {question_key}")


def _summary_characters(state: dict[str, Any]) -> str:
    normalized = dict(state.get("normalized") or {})
    user_answers = dict(state.get("user_answers") or {})
    mode = str(normalized.get("characters_mode") or "")
    note = str(user_answers.get("characters_note") or "").strip()
    return f"{mode}（{note}）" if note else mode


def _summary_music(normalized: dict[str, Any]) -> str:
    mode = str(normalized.get("music_mode") or "")
    profile = str(normalized.get("music_profile") or "")
    if profile == "song":
        return "需要，歌曲（song）"
    if profile == "instrumental":
        return "需要，纯音乐（instrumental）"
    if profile == "underscore":
        return "需要，背景配乐（underscore）"
    return mode


def build_brief_llm_output(state: dict[str, Any]) -> dict[str, Any]:
    normalized = empty_brief_normalized()
    normalized.update(dict(state.get("normalized") or {}))
    user_answers = dict(state.get("user_answers") or {})
    visual_spec = " + ".join([
        str(normalized.get("aspect_ratio_label") or "").strip(),
        str(normalized.get("resolution_label") or "").strip(),
    ]).strip(" +")
    return {
        "source": "Created from user-supplied Stage 00 intake answers.",
        "user_answers": user_answers,
        "normalized": normalized,
        "required_fields_complete": True,
        "missing_required_fields": [],
        "brief_confirmation_summary": {
            "idea": str(normalized.get("idea") or ""),
            "target_duration": str(normalized.get("target_duration_label") or ""),
            "genre": str(normalized.get("genre") or ""),
            "style": str(normalized.get("style") or ""),
            "visual_spec": visual_spec,
            "characters": _summary_characters(state),
            "voice": str(normalized.get("voice_mode") or ""),
            "music": _summary_music(normalized),
            "final_output": str(normalized.get("final_output") or ""),
        },
    }
