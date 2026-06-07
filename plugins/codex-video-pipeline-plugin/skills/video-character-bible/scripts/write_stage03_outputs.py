#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import routing_from_brief, strategy_bundle  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.reference_image_readiness import (  # noqa: E402
    build_reference_image_plan,
    build_reference_image_status,
    build_stage05_execution_readiness,
)
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def ensure_shape(data: dict[str, Any]) -> None:
    required = ["characters", "reference_image_required", "reference_image_handoff", "self_check"]
    missing = [key for key in required if key not in data]
    if missing:
        raise SystemExit(f"ERROR: missing required keys in llm output: {', '.join(missing)}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_reference_image_start_here(
    stage03_dir: Path,
    *,
    reference_handoff: dict[str, Any],
    reference_plan: dict[str, Any],
    reference_status: dict[str, Any],
    stage05_execution_readiness: dict[str, Any],
) -> None:
    reference_dir = stage03_dir / "reference_images"
    reference_dir.mkdir(parents=True, exist_ok=True)
    missing_paths = reference_status.get("missing_paths") if isinstance(reference_status.get("missing_paths"), list) else []
    capture_focus = reference_handoff.get("capture_focus") if isinstance(reference_handoff.get("capture_focus"), list) else []
    lines = [
        "# 角色参考图补齐入口",
        "",
        "这一步是给普通创作者准备的默认入口，不需要先理解 manifest。",
        "",
        f"- 当前判断摘要：{str(reference_handoff.get('summary') or '').strip() or '未提供'}",
        f"- 角色参考图是否已齐：{'是' if reference_status.get('all_present') else '否'}",
        f"- 是否可安全自动进入 Stage 05：{'是' if stage05_execution_readiness.get('safe_to_auto_generate') else '否'}",
        f"- 参考图目录：`{str(reference_dir).replace(chr(92), '/')}`",
        "",
        "## 现在该做什么",
        "",
    ]
    if missing_paths:
        lines.extend([
            f"- {str(reference_handoff.get('next_action') or '').strip() or '先补齐角色参考图，再继续后续阶段。'}",
            "- 这次补图要优先保住这些识别锚点：",
            *[f"  - {str(item).strip()}" for item in capture_focus if str(item).strip()],
            "- 把图片放到下面这些目标路径里：",
            *[f"  - `{path_text}`" for path_text in missing_paths],
        ])
    else:
        lines.extend([
            f"- {str(reference_handoff.get('next_action') or '').strip() or '当前角色参考图已经就绪，可以继续进入下一阶段。'}",
        ])
    write_text(stage03_dir / "reference_image_start_here.md", "\n".join(lines))


def write_stage03_companions(
    out_path: Path,
    template: dict[str, Any],
    *,
    reference_handoff: dict[str, Any],
    reference_plan: dict[str, Any],
    reference_status: dict[str, Any],
    stage05_execution_readiness: dict[str, Any],
) -> None:
    characters = template.get("characters") if isinstance(template.get("characters"), list) else []
    bible_lines = ["# Stage 03 Character Bible", ""]
    role_labels = {
        "main": "主角",
        "supporting": "配角",
    }
    for character in characters:
        if not isinstance(character, dict):
            continue
        appearance = character.get("appearance") if isinstance(character.get("appearance"), dict) else {}
        performance = character.get("performance_profile") if isinstance(character.get("performance_profile"), dict) else {}
        role_label = role_labels.get(str(character.get("role") or "").strip(), str(character.get("role") or "角色"))
        age = str(character.get("age") or "").strip()
        positioning = f"{role_label}，{age}" if age else role_label
        bible_lines.extend([
            f"## {character.get('name')} ({character.get('character_id')})",
            f"- 定位：{positioning}",
            f"- 核心气质：{character.get('personality')}",
            (
                "- 外形锚点："
                f"{appearance.get('face')} / {appearance.get('hair')} / {appearance.get('clothing')} / {appearance.get('accessories')}"
            ),
            f"- 表演基线：{performance.get('baseline_expression')}",
            f"- 情绪推进：{' / '.join(character.get('emotional_arc') or [])}",
            f"- 连续性锚点：{performance.get('continuity_anchor')}",
            f"- 声音建议：{(character.get('voice_profile') or {}).get('suggested_voice')}",
            "",
        ])
    missing_paths = reference_status.get("missing_paths") if isinstance(reference_status.get("missing_paths"), list) else []
    review_lines = [
        "# Stage 03 Character Review",
        "",
        f"- 是否匹配 brief/script/storyboard：{'是' if ((template.get('self_check') or {}).get('matches_storyboard')) else '否'}",
        f"- 角色参考图计划：{'已生成' if reference_plan.get('reference_images') else '未生成'}",
        f"- 角色参考图就绪：{'是' if reference_status.get('all_present') else '否'}",
        f"- 是否准备好进入 Stage 04：{'是' if ((template.get('self_check') or {}).get('ready_for_keyframe_stage')) else '否'}",
        f"- 是否准备好安全自动进入 Stage 05：{'是' if stage05_execution_readiness.get('safe_to_auto_generate') else '否'}",
        f"- 当前判断：{str(reference_handoff.get('summary') or '').strip() or '未提供'}",
        f"- 下一步：{str(reference_handoff.get('next_action') or '').strip() or ('待用户确认后进入 Stage 04。' if not missing_paths else '先补角色参考图。')}",
    ]
    write_text(out_path.parent / "character_bible.md", "\n".join(bible_lines))
    write_text(out_path.parent / "character_review.md", "\n".join(review_lines))
    (out_path.parent / "reference_image_plan.json").write_text(json.dumps(reference_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    write_reference_image_start_here(
        out_path.parent,
        reference_handoff=reference_handoff,
        reference_plan=reference_plan,
        reference_status=reference_status,
        stage05_execution_readiness=stage05_execution_readiness,
    )


def build_character_bible_payload(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    llm_output: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    storyboard_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    ensure_shape(llm_output)
    characters = [item for item in list(llm_output.get("characters") or []) if isinstance(item, dict)]
    reference_handoff = dict(llm_output.get("reference_image_handoff") or {})
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_03")
    anchors = resolve_upstream_story_anchors(storyboard, script)
    reference_plan = build_reference_image_plan(
        str(brief.get("project_id") or storyboard.get("project_id") or ""),
        characters,
        required=bool(llm_output.get("reference_image_required")),
    )
    reference_status = build_reference_image_status(out_path.parent, reference_plan)
    stage05_execution_readiness = build_stage05_execution_readiness(
        continuity_mode=str(compiled.get("continuity_mode") or ""),
        reference_image_required=bool(llm_output.get("reference_image_required")),
        reference_image_status=reference_status,
        stage05_ready_from_codex=bool(reference_handoff.get("ready_for_stage05")),
    )
    self_check = dict(llm_output.get("self_check") or {})
    self_check["reference_images_planned"] = bool(reference_plan.get("reference_images"))
    self_check["reference_images_ready"] = bool(reference_status.get("all_present"))
    self_check["safe_for_character_locked_image_generation"] = bool(reference_handoff.get("ready_for_stage05"))
    notes = self_check.get("notes") if isinstance(self_check.get("notes"), list) else []
    missing_paths = reference_status.get("missing_paths") if isinstance(reference_status.get("missing_paths"), list) else []
    if missing_paths:
        notes = [
            *notes,
            "Reference images still missing for character-locked continuity: " + ", ".join(str(path_text) for path_text in missing_paths),
        ]
    self_check["notes"] = notes
    return {
        "schema_version": "0.4.0",
        "stage": "STAGE_03_CHARACTER_BIBLE",
        "status": str(llm_output.get("status") or "draft"),
        "project_id": str(brief.get("project_id") or storyboard.get("project_id") or script.get("project_id") or ""),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_script": str(script_path.resolve()).replace("\\", "/"),
        "source_storyboard": str(storyboard_path.resolve()).replace("\\", "/"),
        "characters": characters,
        "reference_image_required": bool(llm_output.get("reference_image_required")),
        "reference_image_handoff": reference_handoff,
        "reference_image_plan": reference_plan,
        "reference_image_status": reference_status,
        "stage05_execution_readiness": stage05_execution_readiness,
        "story_anchors": anchors,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": self_check,
        "allowed_next_stage": None,
    }


def write_stage03_outputs(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    llm_output: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    storyboard_path: Path,
    llm_output_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    payload = build_character_bible_payload(brief, script, storyboard, llm_output, brief_path, script_path, storyboard_path, out_path)
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stage03_llm_output.json").write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage03_companions(
        out_path,
        payload,
        reference_handoff=payload["reference_image_handoff"],
        reference_plan=payload["reference_image_plan"],
        reference_status=payload["reference_image_status"],
        stage05_execution_readiness=payload["stage05_execution_readiness"],
    )
    return payload


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print("Usage: python write_stage03_outputs.py <locked_brief.json> <script.json> <storyboard.json> <stage03_llm_output.json> <character_bible.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    llm_output_path = Path(argv[4])
    out_path = Path(argv[5])
    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    llm_output = load_json(llm_output_path)
    write_stage03_outputs(brief, script, storyboard, llm_output, brief_path, script_path, storyboard_path, llm_output_path, out_path)
    print(f"STAGE03_OUTPUTS_WRITTEN: {out_path.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
