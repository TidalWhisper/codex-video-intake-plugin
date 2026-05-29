#!/usr/bin/env python3
"""Create a Stage 01 script draft from a locked project brief."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import build_stage01_script  # noqa: E402
from pipeline_core.project_state import load_json_file, update_project_manifest_for_stage  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage  # noqa: E402


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_stage01_companions(out_path: Path, template: dict) -> None:
    beats = (template.get("duration_plan") or {}).get("beats") or []
    sections = (template.get("script") or {}).get("sections") or []
    contract = template.get("creative_contract") if isinstance(template.get("creative_contract"), dict) else {}
    story_direction_json = {
        "project_id": template.get("project_id"),
        "title_candidates": [template.get("title")],
        "core_theme": template.get("theme"),
        "protagonist_state": contract.get("subject") or "主角进入故事空间",
        "emotional_arc": [beat.get("emotion") for beat in beats if isinstance(beat, dict)],
        "narrative_conflict_or_movement": template.get("logline"),
        "ending_direction": beats[-1].get("summary") if beats else "",
        "genre": contract.get("genre") or "",
        "style": contract.get("style") or "",
        "avoid": ["不要偏离 locked brief 的题材、风格和配音约束"],
    }
    plot_structure_json = {
        "project_id": template.get("project_id"),
        "target_duration_sec": (template.get("duration_plan") or {}).get("target_duration_sec"),
        "beats": beats,
    }
    story_direction_md = "\n".join([
        "# Stage 01 Story Direction",
        "",
        f"- 标题候选：{template.get('title')}",
        f"- 核心主题：{template.get('theme')}",
        f"- 主体：{contract.get('subject') or '主角'}",
        f"- 场景：{contract.get('scene') or ''}",
        f"- 类型/风格：{contract.get('genre') or ''} / {contract.get('style') or ''}",
        f"- 叙事推进：{template.get('logline')}",
        f"- 结尾方向：{story_direction_json['ending_direction']}",
        "- 不应包含：不要偏离 locked brief 的题材、风格和配音约束",
    ])
    plot_structure_lines = ["# Stage 01 Plot Structure", ""]
    for beat in beats:
        if not isinstance(beat, dict):
            continue
        plot_structure_lines.append(f"- {beat.get('start')} - {beat.get('end')} | {beat.get('summary')} | 情绪：{beat.get('emotion')}")
    script_lines = ["# Stage 01 Script", "", f"## {template.get('title')}", "", f"{template.get('logline')}", ""]
    for section in sections:
        if not isinstance(section, dict):
            continue
        script_lines.extend([
            f"### {section.get('time')}",
            f"- 画面：{section.get('visual')}",
            f"- 旁白：{section.get('voiceover') or '无'}",
            f"- 对白：{section.get('dialogue') or '无'}",
            f"- 音乐：{section.get('music_cue') or '无'}",
            "",
        ])
    review_lines = [
        "# Stage 01 Script Review",
        "",
        "- 是否严格遵守 locked brief：是",
        "- 是否符合目标时长：是",
        "- 是否符合题材与风格：是",
        "- 是否符合人物与画面要求：是",
        "- 是否符合配音与音乐要求：是",
        "- 下一步：待用户确认后进入 Stage 02。",
    ]

    write_text(out_path.parent / "story_direction.md", story_direction_md)
    (out_path.parent / "story_direction.json").write_text(json.dumps(story_direction_json, ensure_ascii=False, indent=2), encoding="utf-8")
    write_text(out_path.parent / "plot_structure.md", "\n".join(plot_structure_lines))
    (out_path.parent / "plot_structure.json").write_text(json.dumps(plot_structure_json, ensure_ascii=False, indent=2), encoding="utf-8")
    write_text(out_path.parent / "script.md", "\n".join(script_lines))
    write_text(out_path.parent / "script_review.md", "\n".join(review_lines))


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 3:
        print("Usage: python new_script_template.py <locked_brief.json> <script.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    out_path = Path(argv[2])
    brief = load_json(brief_path)
    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_01", compiled):
        print("ERROR: requested output scope does not allow Stage 01. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1

    template = build_stage01_script(brief)
    template["project_id"] = brief.get("project_id") or brief_path.parents[1].name
    template["source_brief"] = str(brief_path).replace("\\", "/")
    template["created_at"] = datetime.now(timezone.utc).isoformat()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage01_companions(out_path, template)
    update_project_manifest_for_stage(
        out_path,
        current_stage="STAGE_01_SCRIPT_GENERATION",
        allowed_next_stage=None,
        flags={"script_confirmed": False},
        status="active",
    )
    print(f"SCRIPT TEMPLATE CREATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
