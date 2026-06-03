#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import normal_brief, routing_from_brief, strategy_bundle  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def ensure_shape(data: dict[str, Any]) -> None:
    required = ["target_duration_sec", "shots", "self_check"]
    missing = [key for key in required if key not in data]
    if missing:
        raise SystemExit(f"ERROR: missing required keys in llm output: {', '.join(missing)}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def build_storyboard_payload(
    brief: dict[str, Any],
    script: dict[str, Any],
    llm_output: dict[str, Any],
    brief_path: Path,
    script_path: Path,
) -> dict[str, Any]:
    ensure_shape(llm_output)
    normalized = normal_brief(brief)
    shots = [shot for shot in list(llm_output.get("shots") or []) if isinstance(shot, dict)]
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_02")
    anchors = resolve_upstream_story_anchors({"shots": shots}, script)
    return {
        "schema_version": "0.3.0",
        "stage": "STAGE_02_STORYBOARD_GENERATION",
        "status": str(llm_output.get("status") or "draft"),
        "project_id": str(brief.get("project_id") or script.get("project_id") or ""),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_script": str(script_path.resolve()).replace("\\", "/"),
        "target_duration_sec": int(llm_output.get("target_duration_sec") or (script.get("duration_plan") or {}).get("target_duration_sec") or normalized.get("target_duration_sec") or 30),
        "shot_count": len(shots),
        "shots": shots,
        "story_anchors": anchors,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": dict(llm_output.get("self_check") or {}),
        "allowed_next_stage": None,
    }


def write_stage02_companions(out_path: Path, template: dict[str, Any]) -> None:
    shots = template.get("shots") if isinstance(template.get("shots"), list) else []
    storyboard_lines = ["# Stage 02 Storyboard", ""]
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        storyboard_lines.extend([
            f"## {shot.get('shot_id')} {shot.get('start')} - {shot.get('end')}",
            f"- 场景：{shot.get('scene')}",
            f"- 地点/天气：{shot.get('location') or shot.get('scene')} / {shot.get('weather') or '按故事气氛执行'}",
            f"- 镜头：{shot.get('camera')}",
            f"- 构图：{shot.get('composition')}",
            f"- 关键道具：{shot.get('key_prop') or '无'}",
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
        f"- 是否匹配 locked brief：{'是' if ((template.get('self_check') or {}).get('matches_locked_brief')) else '否'}",
        f"- 是否匹配 script：{'是' if ((template.get('self_check') or {}).get('matches_script')) else '否'}",
        f"- 镜头数：{template.get('shot_count')}",
        f"- 目标时长：{template.get('target_duration_sec')} 秒",
        "- 下一步：待用户确认后进入 Stage 03。",
    ]
    write_text(out_path.parent / "storyboard.md", "\n".join(storyboard_lines))
    write_text(out_path.parent / "storyboard_review.md", "\n".join(review_lines))


def write_stage02_outputs(
    brief: dict[str, Any],
    script: dict[str, Any],
    llm_output: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    llm_output_path: Path,
    storyboard_json_path: Path,
) -> dict[str, Any]:
    payload = build_storyboard_payload(brief, script, llm_output, brief_path, script_path)
    out_dir = storyboard_json_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stage02_llm_output.json").write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    storyboard_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage02_companions(storyboard_json_path, payload)
    return payload


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print("Usage: python write_stage02_outputs.py <locked_brief.json> <script.json> <stage02_llm_output.json> <storyboard.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    llm_output_path = Path(argv[3])
    storyboard_json_path = Path(argv[4])
    brief = load_json(brief_path)
    script = load_json(script_path)
    llm_output = load_json(llm_output_path)
    write_stage02_outputs(brief, script, llm_output, brief_path, script_path, llm_output_path, storyboard_json_path)
    print(f"STAGE02_OUTPUTS_WRITTEN: {storyboard_json_path.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
