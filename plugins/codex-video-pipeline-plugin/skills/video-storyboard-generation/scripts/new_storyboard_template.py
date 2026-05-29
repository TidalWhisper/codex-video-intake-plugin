#!/usr/bin/env python3
"""Create a Stage 02 storyboard draft from a locked brief and script."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import build_stage02_storyboard  # noqa: E402
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


def write_stage02_companions(out_path: Path, template: dict) -> None:
    shots = template.get("shots") if isinstance(template.get("shots"), list) else []
    storyboard_lines = ["# Stage 02 Storyboard", ""]
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        storyboard_lines.extend([
            f"## {shot.get('shot_id')} {shot.get('start')} - {shot.get('end')}",
            f"- 场景：{shot.get('scene')}",
            f"- 镜头：{shot.get('camera')}",
            f"- 构图：{shot.get('composition')}",
            f"- 动作：{shot.get('action')}",
            f"- 情绪：{shot.get('emotion')}",
            f"- 对白：{shot.get('dialogue') or '无'}",
            f"- 旁白：{shot.get('voiceover') or '无'}",
            f"- 声音：{shot.get('sound_music') or '无'}",
            f"- 转场：{shot.get('transition_to_next')}",
            "",
        ])
    review_lines = [
        "# Stage 02 Storyboard Review",
        "",
        "- 是否匹配 locked brief：是",
        "- 是否匹配 script：是",
        f"- 镜头数：{template.get('shot_count')}",
        f"- 目标时长：{template.get('target_duration_sec')} 秒",
        "- 下一步：待用户确认后进入 Stage 03。",
    ]
    write_text(out_path.parent / "storyboard.md", "\n".join(storyboard_lines))
    write_text(out_path.parent / "storyboard_review.md", "\n".join(review_lines))


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 4:
        print("Usage: python new_storyboard_template.py <locked_brief.json> <script.json> <storyboard.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    out_path = Path(argv[3])
    brief = load_json(brief_path)
    script = load_json(script_path)
    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_02", compiled):
        print("ERROR: requested output scope does not allow Stage 02. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if script.get("stage") != "STAGE_01_SCRIPT_GENERATION":
        print("ERROR: script.stage must be STAGE_01_SCRIPT_GENERATION", file=sys.stderr)
        return 1

    template = build_stage02_storyboard(brief, script)
    template["project_id"] = brief.get("project_id") or script.get("project_id") or brief_path.parents[1].name
    template["source_brief"] = str(brief_path).replace("\\", "/")
    template["source_script"] = str(script_path).replace("\\", "/")
    template["created_at"] = datetime.now(timezone.utc).isoformat()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage02_companions(out_path, template)
    update_project_manifest_for_stage(
        out_path,
        current_stage="STAGE_02_STORYBOARD_GENERATION",
        allowed_next_stage=None,
        flags={"storyboard_confirmed": False},
        status="active",
    )
    print(f"STORYBOARD TEMPLATE CREATED: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
