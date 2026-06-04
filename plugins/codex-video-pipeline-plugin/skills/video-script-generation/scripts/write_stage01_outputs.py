#!/usr/bin/env python3
"""Write official Stage 01 outputs from Codex-first structured output."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import extract_story_anchors, routing_from_brief, strategy_bundle  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def ensure_shape(data: dict[str, Any]) -> None:
    required = [
        "title_candidates",
        "selected_title",
        "logline",
        "theme",
        "characters",
        "settings",
        "beats",
        "self_check",
    ]
    missing = [key for key in required if key not in data]
    if missing:
        raise SystemExit(f"ERROR: missing required keys in llm output: {', '.join(missing)}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def normalize_music_cue(cue: Any, music_profile: str) -> str:
    text = str(cue or "").strip()
    profile = str(music_profile or "").strip().lower()
    if not text or not profile:
        return text

    for known_profile in ("song", "instrumental", "underscore"):
        ascii_prefix = f"{known_profile}:"
        fullwidth_prefix = f"{known_profile}："
        lowered = text.lower()
        if lowered.startswith(ascii_prefix) or lowered.startswith(fullwidth_prefix):
            body = text[len(ascii_prefix):] if lowered.startswith(ascii_prefix) else text[len(fullwidth_prefix):]
            return f"{known_profile}: {body.strip()}".rstrip()

    return f"{profile}: {text}"


def build_story_anchors_from_output(brief: dict[str, Any], llm_output: dict[str, Any]) -> dict[str, Any]:
    beats = [beat for beat in list(llm_output.get("beats") or []) if isinstance(beat, dict)]
    base = extract_story_anchors(brief, max(1, len(beats))).to_dict()
    characters = [item for item in list(llm_output.get("characters") or []) if isinstance(item, dict)]
    settings = [str(item).strip() for item in list(llm_output.get("settings") or []) if str(item or "").strip()]
    if characters:
        base["subject"] = str(characters[0].get("name") or base.get("subject") or "").strip()
        base["subject_age"] = str(characters[0].get("age") or base.get("subject_age") or "").strip()
    if settings:
        base["scene_label"] = settings[0]
        if len(settings) > 1:
            base["location"] = settings[1]
        else:
            base["location"] = settings[0]
    if beats:
        base["action_beats"] = [str(beat.get("summary") or "").strip() for beat in beats]
        base["emotion_beats"] = [str(beat.get("emotion") or "").strip() for beat in beats]
        base["composition_beats"] = [str(beat.get("visual") or "").strip() for beat in beats]
        base["composition_focus_beats"] = [
            str(beat.get("composition_focus") or beat.get("visual") or "").strip()
            for beat in beats
        ]
    return base


def build_script_payload(brief: dict[str, Any], llm_output: dict[str, Any], source_brief_path: Path) -> dict[str, Any]:
    normalized = brief.get("normalized") if isinstance(brief.get("normalized"), dict) else brief
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_01")
    beats = list(llm_output.get("beats") or [])
    story_anchors = build_story_anchors_from_output(brief, llm_output)
    music_profile = str(normalized.get("music_profile") or "")
    script_sections = []
    duration_plan_beats = []
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        duration_plan_beats.append({
            "beat_id": beat.get("beat_id"),
            "start": beat.get("start"),
            "end": beat.get("end"),
            "summary": beat.get("summary"),
            "emotion": beat.get("emotion"),
        })
        script_sections.append({
            "time": f"{beat.get('start')}-{beat.get('end')}",
            "visual": beat.get("visual"),
            "composition_focus": beat.get("composition_focus"),
            "voiceover": beat.get("voiceover"),
            "dialogue": beat.get("dialogue"),
            "music_cue": normalize_music_cue(beat.get("music_cue"), music_profile),
        })
    payload = {
        "schema_version": "0.3.0",
        "stage": "STAGE_01_SCRIPT_GENERATION",
        "status": "draft",
        "project_id": str(brief.get("project_id") or ""),
        "source_brief": str(source_brief_path.resolve()).replace("\\", "/"),
        "title_candidates": list(llm_output.get("title_candidates") or []),
        "title": str(llm_output.get("selected_title") or ""),
        "logline": str(llm_output.get("logline") or ""),
        "theme": str(llm_output.get("theme") or ""),
        "protagonist_state": str(llm_output.get("protagonist_state") or ""),
        "narrative_movement": str(llm_output.get("narrative_movement") or ""),
        "ending_direction": str(llm_output.get("ending_direction") or ""),
        "avoid": list(llm_output.get("avoid") or []),
        "characters": list(llm_output.get("characters") or []),
        "settings": list(llm_output.get("settings") or []),
        "duration_plan": {
            "target_duration_sec": int(normalized.get("target_duration_sec") or 30),
            "target_duration_label": str(normalized.get("target_duration_label") or ""),
            "beats": duration_plan_beats,
        },
        "script": {
            "format": "screenplay",
            "voice_mode": str(normalized.get("voice_mode") or ""),
            "music_mode": str(normalized.get("music_mode") or ""),
            "music_profile": music_profile,
            "sections": script_sections,
        },
        "creative_contract": {
            "idea": str(normalized.get("idea") or ""),
            "genre": str(normalized.get("genre") or ""),
            "style": str(normalized.get("style") or ""),
            "subject": str((llm_output.get("characters") or [{}])[0].get("name") if llm_output.get("characters") else ""),
            "scene": str((llm_output.get("settings") or [""])[0]),
            "performance_direction": str(llm_output.get("theme") or ""),
        },
        "story_anchors": story_anchors,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": dict(llm_output.get("self_check") or {}),
        "generation_meta": {
            "mode": "codex_llm_output",
        },
        "allowed_next_stage": None,
    }
    return payload


def render_story_direction(script_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    beats = (script_payload.get("duration_plan") or {}).get("beats") or []
    story_direction_json = {
        "project_id": script_payload.get("project_id"),
        "title_candidates": list(script_payload.get("title_candidates") or [script_payload.get("title")]),
        "core_theme": script_payload.get("theme"),
        "protagonist_state": script_payload.get("protagonist_state"),
        "emotional_arc": [beat.get("emotion") for beat in beats if isinstance(beat, dict)],
        "narrative_conflict_or_movement": script_payload.get("narrative_movement") or script_payload.get("logline"),
        "ending_direction": script_payload.get("ending_direction"),
        "genre": (script_payload.get("creative_contract") or {}).get("genre") or "",
        "style": (script_payload.get("creative_contract") or {}).get("style") or "",
        "avoid": list(script_payload.get("avoid") or []),
    }
    story_direction_md = "\n".join([
        "# Stage 01 Story Direction",
        "",
        f"- 标题候选：{' / '.join(story_direction_json['title_candidates'])}",
        f"- 核心主题：{story_direction_json['core_theme']}",
        f"- 主角状态：{story_direction_json['protagonist_state']}",
        f"- 类型/风格：{story_direction_json['genre']} / {story_direction_json['style']}",
        f"- 叙事推进：{story_direction_json['narrative_conflict_or_movement']}",
        f"- 结尾方向：{story_direction_json['ending_direction']}",
        f"- 不应包含：{'；'.join(story_direction_json['avoid']) if story_direction_json['avoid'] else '无'}",
    ])
    return story_direction_json, story_direction_md


def render_plot_structure(script_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    beats = (script_payload.get("duration_plan") or {}).get("beats") or []
    plot_structure_json = {
        "project_id": script_payload.get("project_id"),
        "target_duration_sec": (script_payload.get("duration_plan") or {}).get("target_duration_sec"),
        "beats": beats,
    }
    lines = ["# Stage 01 Plot Structure", ""]
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        lines.append(f"- {beat.get('start')} - {beat.get('end')} | {beat.get('summary')} | 情绪：{beat.get('emotion')}")
    return plot_structure_json, "\n".join(lines)


def render_script_md(script_payload: dict[str, Any]) -> str:
    lines = ["# Stage 01 Script", "", f"## {script_payload.get('title')}", "", f"{script_payload.get('logline')}", ""]
    sections = (script_payload.get("script") or {}).get("sections") or []
    for section in sections:
        if not isinstance(section, dict):
            continue
        lines.extend([
            f"### {section.get('time')}",
            f"- 画面：{section.get('visual')}",
            f"- 旁白：{section.get('voiceover') or '无'}",
            f"- 对白：{section.get('dialogue') or '无'}",
            f"- 音乐：{section.get('music_cue') or '无'}",
            "",
        ])
    return "\n".join(lines)


def render_script_review(script_payload: dict[str, Any]) -> str:
    self_check = script_payload.get("self_check") if isinstance(script_payload.get("self_check"), dict) else {}
    return "\n".join([
        "# Stage 01 Script Review",
        "",
        f"1. 是否严格遵守 locked brief：{'是' if self_check.get('matches_locked_brief') else '否'}",
        f"2. 是否符合目标时长：{'是' if self_check.get('duration_fits') else '否'}",
        f"3. 是否符合题材：{'是' if self_check.get('genre_style_fits') else '否'}",
        f"4. 是否符合风格：{'是' if self_check.get('genre_style_fits') else '否'}",
        f"5. 是否符合画面规格：{'是' if self_check.get('aspect_ratio_fits') else '否'}",
        f"6. 是否符合人物/主角要求：{'是' if self_check.get('character_requirement_fits') else '否'}",
        f"7. 是否符合配音要求：{'是' if self_check.get('voice_fits') else '否'}",
        f"8. 是否符合背景音乐要求：{'是' if self_check.get('music_fits') else '否'}",
        f"9. 是否可以进入 Stage 02 分镜拆解：{'是' if self_check.get('ready_for_storyboard') else '否'}",
        "",
        "- 下一步：待用户确认后进入 Stage 02。",
    ])


def write_stage01_outputs(
    brief: dict[str, Any],
    llm_output: dict[str, Any],
    source_brief_path: Path,
    llm_output_path: Path,
    script_json_path: Path,
) -> dict[str, Any]:
    ensure_shape(llm_output)
    script_payload = build_script_payload(brief, llm_output, source_brief_path)
    script_dir = script_json_path.parent
    script_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path = script_dir / "stage01_llm_output.json"
    raw_output_path.write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    story_direction_json, story_direction_md = render_story_direction(script_payload)
    plot_structure_json, plot_structure_md = render_plot_structure(script_payload)
    script_md = render_script_md(script_payload)
    review_md = render_script_review(script_payload)
    script_json_path.write_text(json.dumps(script_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (script_dir / "story_direction.json").write_text(json.dumps(story_direction_json, ensure_ascii=False, indent=2), encoding="utf-8")
    write_text(script_dir / "story_direction.md", story_direction_md)
    (script_dir / "plot_structure.json").write_text(json.dumps(plot_structure_json, ensure_ascii=False, indent=2), encoding="utf-8")
    write_text(script_dir / "plot_structure.md", plot_structure_md)
    write_text(script_dir / "script.md", script_md)
    write_text(script_dir / "script_review.md", review_md)
    return script_payload


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: python write_stage01_outputs.py <locked_brief.json> <stage01_llm_output.json> <script.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    llm_output_path = Path(argv[2])
    script_json_path = Path(argv[3])
    brief = load_json(brief_path)
    data = load_json(llm_output_path)
    write_stage01_outputs(brief, data, brief_path, llm_output_path, script_json_path)
    print(f"STAGE01_OUTPUTS_WRITTEN: {script_json_path.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
