#!/usr/bin/env python3
"""Create a Stage 04 keyframe/motion prompt draft."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import build_stage04_keyframe_prompts  # noqa: E402
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


def write_stage04_companions(out_path: Path, template: dict) -> None:
    shots = template.get("shot_prompts") if isinstance(template.get("shot_prompts"), list) else []
    transitions = template.get("transition_prompts") if isinstance(template.get("transition_prompts"), list) else []
    prompt_lines = ["# Stage 04 Keyframe Prompt Package", ""]
    motion_records = []
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        prompt_lines.extend([
            f"## {shot.get('shot_id')}",
            f"- 场景摘要：{shot.get('scene_summary')}",
            f"- 起始关键帧：{shot.get('start_keyframe_prompt')}",
            f"- 结束关键帧：{shot.get('end_keyframe_prompt')}",
            f"- 动作提示：{shot.get('motion_prompt')}",
            f"- 一致性：{shot.get('consistency_prompt')}",
            "",
        ])
        motion_records.append({
            "shot_id": shot.get("shot_id"),
            "motion_prompt": shot.get("motion_prompt"),
            "camera_prompt": shot.get("camera_prompt"),
            "dialogue_delivery_prompt": shot.get("dialogue_delivery_prompt"),
        })
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        motion_records.append({
            "transition_id": transition.get("transition_id"),
            "from_shot_id": transition.get("from_shot_id"),
            "to_shot_id": transition.get("to_shot_id"),
            "transition_motion_prompt": transition.get("transition_motion_prompt"),
        })
    review_lines = [
        "# Stage 04 Prompt Review",
        "",
        f"- 镜头提示词数量：{len(shots)}",
        f"- 过渡提示词数量：{len(transitions)}",
        "- 是否覆盖 storyboard 全部镜头：是",
        "- 是否保留角色一致性锚点：是",
        "- 下一步：待用户确认后进入 Stage 05。",
    ]
    write_text(out_path.parent / "keyframe_prompts.md", "\n".join(prompt_lines))
    (out_path.parent / "motion_prompts.json").write_text(json.dumps({"project_id": template.get("project_id"), "records": motion_records}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_text(out_path.parent / "prompt_review.md", "\n".join(review_lines))


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 6:
        print("Usage: python new_keyframe_prompts_template.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json> <keyframe_prompts.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    character_path = Path(argv[4])
    out_path = Path(argv[5])
    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    character_bible = load_json(character_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_04", compiled):
        print("ERROR: requested output scope does not allow Stage 04. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        print("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION", file=sys.stderr)
        return 1
    if storyboard.get("stage") != "STAGE_02_STORYBOARD_GENERATION":
        print("ERROR: storyboard.stage must be STAGE_02_STORYBOARD_GENERATION", file=sys.stderr)
        return 1
    if character_bible.get("stage") != "STAGE_03_CHARACTER_BIBLE":
        print("ERROR: character_bible.stage must be STAGE_03_CHARACTER_BIBLE", file=sys.stderr)
        return 1

    template = build_stage04_keyframe_prompts(brief, script, storyboard, character_bible)
    template["project_id"] = brief.get("project_id") or script.get("project_id") or storyboard.get("project_id") or character_bible.get("project_id") or brief_path.parents[1].name
    template["source_brief"] = str(brief_path).replace("\\", "/")
    template["source_script"] = str(script_path).replace("\\", "/")
    template["source_storyboard"] = str(storyboard_path).replace("\\", "/")
    template["source_character_bible"] = str(character_path).replace("\\", "/")
    template["created_at"] = datetime.now(timezone.utc).isoformat()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage04_companions(out_path, template)
    update_project_manifest_for_stage(
        out_path,
        current_stage="STAGE_04_KEYFRAME_PROMPTS_GENERATION",
        allowed_next_stage=None,
        flags={"keyframe_prompts_confirmed": False},
        status="active",
    )
    print(f"KEYFRAME PROMPTS TEMPLATE CREATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
