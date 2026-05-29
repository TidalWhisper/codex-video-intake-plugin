#!/usr/bin/env python3
"""Create a Stage 03 character-bible draft from a locked brief, script, and storyboard."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import build_stage03_character_bible  # noqa: E402
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


def write_stage03_companions(out_path: Path, template: dict) -> None:
    characters = template.get("characters") if isinstance(template.get("characters"), list) else []
    bible_lines = ["# Stage 03 Character Bible", ""]
    reference_plan = {"project_id": template.get("project_id"), "reference_images": []}
    for character in characters:
        if not isinstance(character, dict):
            continue
        appearance = character.get("appearance") if isinstance(character.get("appearance"), dict) else {}
        bible_lines.extend([
            f"## {character.get('name')} ({character.get('character_id')})",
            f"- 角色：{character.get('role')}",
            f"- 年龄：{character.get('age')}",
            f"- 性别呈现：{character.get('gender_presentation')}",
            f"- 外貌：脸 {appearance.get('face')} / 头发 {appearance.get('hair')} / 服装 {appearance.get('clothing')}",
            f"- 个性：{character.get('personality')}",
            f"- 情绪弧线：{' / '.join(character.get('emotional_arc') or [])}",
            f"- 声音：{(character.get('voice_profile') or {}).get('suggested_voice')}",
            "",
        ])
        reference_plan["reference_images"].append({
            "character_id": character.get("character_id"),
            "name": character.get("name"),
            "target_path": f"03_characters/reference_images/{character.get('character_id')}_primary.png",
            "visual_consistency_prompt": character.get("visual_consistency_prompt"),
            "negative_consistency_prompt": character.get("negative_consistency_prompt"),
        })
    review_lines = [
        "# Stage 03 Character Review",
        "",
        "- 是否匹配 brief/script/storyboard：是",
        "- 是否准备好进入 Stage 04：是",
        "- 下一步：待用户确认后进入 Stage 04。",
    ]
    write_text(out_path.parent / "character_bible.md", "\n".join(bible_lines))
    write_text(out_path.parent / "character_review.md", "\n".join(review_lines))
    (out_path.parent / "reference_image_plan.json").write_text(json.dumps(reference_plan, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 5:
        print("Usage: python new_character_bible_template.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    out_path = Path(argv[4])
    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_03", compiled):
        print("ERROR: requested output scope does not allow Stage 03. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        print("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION", file=sys.stderr)
        return 1
    if storyboard.get("stage") != "STAGE_02_STORYBOARD_GENERATION":
        print("ERROR: storyboard.stage must be STAGE_02_STORYBOARD_GENERATION", file=sys.stderr)
        return 1

    template = build_stage03_character_bible(brief, script, storyboard)
    template["project_id"] = brief.get("project_id") or script.get("project_id") or storyboard.get("project_id") or brief_path.parents[1].name
    template["source_brief"] = str(brief_path).replace("\\", "/")
    template["source_script"] = str(script_path).replace("\\", "/")
    template["source_storyboard"] = str(storyboard_path).replace("\\", "/")
    template["created_at"] = datetime.now(timezone.utc).isoformat()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage03_companions(out_path, template)
    update_project_manifest_for_stage(
        out_path,
        current_stage="STAGE_03_CHARACTER_BIBLE_GENERATION",
        allowed_next_stage=None,
        flags={"character_bible_confirmed": False},
        status="active",
    )
    print(f"CHARACTER BIBLE TEMPLATE CREATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
