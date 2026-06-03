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
    required = ["characters", "reference_image_required", "self_check"]
    missing = [key for key in required if key not in data]
    if missing:
        raise SystemExit(f"ERROR: missing required keys in llm output: {', '.join(missing)}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_reference_image_start_here(
    stage03_dir: Path,
    *,
    reference_plan: dict[str, Any],
    reference_status: dict[str, Any],
    stage05_execution_readiness: dict[str, Any],
) -> None:
    reference_dir = stage03_dir / "reference_images"
    reference_dir.mkdir(parents=True, exist_ok=True)
    missing_paths = reference_status.get("missing_paths") if isinstance(reference_status.get("missing_paths"), list) else []
    lines = [
        "# 角色参考图补齐入口",
        "",
        "这一步是给普通创作者准备的默认入口，不需要先理解 manifest。",
        "",
        f"- 角色参考图是否已齐：{'是' if reference_status.get('all_present') else '否'}",
        f"- 是否可安全自动进入 Stage 05：{'是' if stage05_execution_readiness.get('safe_to_auto_generate') else '否'}",
        f"- 参考图目录：`{str(reference_dir).replace(chr(92), '/')}`",
        "",
        "## 现在该做什么",
        "",
    ]
    if missing_paths:
        lines.extend([
            "- 请先为主角补一张清晰、正面的角色参考图。",
            "- 建议优先保证脸型、发型、服装轮廓和主要随身物一眼可认。",
            "- 把图片放到下面这些目标路径里：",
            *[f"  - `{path_text}`" for path_text in missing_paths],
            "",
            "## 放好以后",
            "",
            "- 继续进入 Stage 04 / Stage 05 时，系统会自动重新检查这些参考图。",
            "- 如果后面 Stage 05 已经先出过一版关键帧，也可以用已有关键帧回填角色参考图。",
        ])
    else:
        lines.extend([
            "- 当前角色参考图已经就绪。",
            "- 可以继续进入 Stage 04，并在确认后安全自动进入 Stage 05。",
        ])
    write_text(stage03_dir / "reference_image_start_here.md", "\n".join(lines))


def write_stage03_companions(
    out_path: Path,
    template: dict[str, Any],
    *,
    reference_plan: dict[str, Any],
    reference_status: dict[str, Any],
    stage05_execution_readiness: dict[str, Any],
) -> None:
    characters = template.get("characters") if isinstance(template.get("characters"), list) else []
    bible_lines = ["# Stage 03 Character Bible", ""]
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
    missing_paths = reference_status.get("missing_paths") if isinstance(reference_status.get("missing_paths"), list) else []
    review_lines = [
        "# Stage 03 Character Review",
        "",
        f"- 是否匹配 brief/script/storyboard：{'是' if ((template.get('self_check') or {}).get('matches_storyboard')) else '否'}",
        f"- 角色参考图计划：{'已生成' if reference_plan.get('reference_images') else '未生成'}",
        f"- 角色参考图就绪：{'是' if reference_status.get('all_present') else '否'}",
        f"- 是否准备好进入 Stage 04：{'是' if ((template.get('self_check') or {}).get('ready_for_keyframe_stage')) else '否'}",
        f"- 是否准备好安全自动进入 Stage 05：{'是' if stage05_execution_readiness.get('safe_to_auto_generate') else '否'}",
        (
            "- 下一步：先补齐这些角色参考图，再进入安全自动 Stage 05："
            + "、".join(str(path_text) for path_text in missing_paths)
        ) if missing_paths else "- 下一步：待用户确认后进入 Stage 04。",
    ]
    write_text(out_path.parent / "character_bible.md", "\n".join(bible_lines))
    write_text(out_path.parent / "character_review.md", "\n".join(review_lines))
    (out_path.parent / "reference_image_plan.json").write_text(json.dumps(reference_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    write_reference_image_start_here(
        out_path.parent,
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
    for character in characters:
        performance_profile = character.get("performance_profile") if isinstance(character.get("performance_profile"), dict) else {}
        appearance = character.get("appearance") if isinstance(character.get("appearance"), dict) else {}
        accessories = str(appearance.get("accessories") or "").strip()
        continuity_parts = [str(character.get("name") or "").strip(), str(appearance.get("clothing") or "").strip(), accessories]
        continuity_anchor = " / ".join(part for part in continuity_parts if part)
        if "baseline_expression" not in performance_profile:
            emotional_arc = character.get("emotional_arc") if isinstance(character.get("emotional_arc"), list) else []
            performance_profile["baseline_expression"] = str((emotional_arc or ["平静"])[0] or "平静")
        performance_profile.setdefault("movement_style", "slow and restrained")
        gesture_rules = performance_profile.get("gesture_rules") if isinstance(performance_profile.get("gesture_rules"), list) else []
        if not gesture_rules:
            performance_profile["gesture_rules"] = [
                "动作幅度偏小",
                "表情变化自然克制",
                "跨镜头保持身体姿态稳定",
            ]
        performance_profile.setdefault("dialogue_delivery", "自然、克制、可停顿")
        performance_profile.setdefault("continuity_anchor", continuity_anchor or str(character.get("name") or "角色连续性"))
        character["performance_profile"] = performance_profile
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_03")
    anchors = resolve_upstream_story_anchors(storyboard, script)
    reference_plan = build_reference_image_plan(str(brief.get("project_id") or storyboard.get("project_id") or ""), characters)
    reference_status = build_reference_image_status(out_path.parent, reference_plan)
    stage05_execution_readiness = build_stage05_execution_readiness(
        continuity_mode=str(compiled.get("continuity_mode") or ""),
        reference_image_required=bool(llm_output.get("reference_image_required")),
        reference_image_status=reference_status,
    )
    self_check = dict(llm_output.get("self_check") or {})
    self_check["reference_images_planned"] = bool(reference_plan.get("reference_images"))
    self_check["reference_images_ready"] = bool(reference_status.get("all_present"))
    self_check["safe_for_character_locked_image_generation"] = bool(stage05_execution_readiness.get("safe_to_auto_generate"))
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
