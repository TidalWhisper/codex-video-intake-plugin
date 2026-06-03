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
from pipeline_core.reference_image_readiness import build_stage05_execution_readiness  # noqa: E402
from pipeline_core.upstream_story_anchors import resolve_upstream_story_anchors  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    try:
        return load_json_file(path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}") from exc


def ensure_shape(data: dict[str, Any]) -> None:
    required = ["shot_prompts", "transition_prompts", "global_negative_prompt", "self_check"]
    missing = [key for key in required if key not in data]
    if missing:
        raise SystemExit(f"ERROR: missing required keys in llm output: {', '.join(missing)}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_stage04_reference_handoff(out_path: Path, template: dict[str, Any]) -> None:
    readiness = template.get("stage05_execution_readiness") if isinstance(template.get("stage05_execution_readiness"), dict) else {}
    missing_paths = readiness.get("missing_reference_images") if isinstance(readiness.get("missing_reference_images"), list) else []
    lines = [
        "# Stage 04 到 Stage 05 之前先看这里",
        "",
        f"- 角色参考图是否已齐：{'是' if ((template.get('reference_image_status') or {}).get('all_present')) else '否'}",
        f"- 是否可安全自动进入 Stage 05：{'是' if readiness.get('safe_to_auto_generate') else '否'}",
        "",
    ]
    if missing_paths:
        lines.extend([
            "系统已经知道你现在卡在角色参考图，而不是卡在 prompt。",
            "",
            "下一步请直接去这里补图：",
            "`03_characters/reference_image_start_here.md`",
            "",
            "缺失目标路径：",
            *[f"- `{path_text}`" for path_text in missing_paths],
        ])
    else:
        lines.extend([
            "角色参考图已经就绪。",
            "确认当前 prompt 包后，可以继续进入 Stage 05 自动生图。",
        ])
    write_text(out_path.parent / "stage05_start_here.md", "\n".join(lines))


def write_stage04_companions(out_path: Path, template: dict[str, Any]) -> None:
    shots = template.get("shot_prompts") if isinstance(template.get("shot_prompts"), list) else []
    transitions = template.get("transition_prompts") if isinstance(template.get("transition_prompts"), list) else []
    prompt_lines = ["# Stage 04 Keyframe Prompt Package", ""]
    motion_records = []
    for shot in shots:
        if not isinstance(shot, dict):
            continue
        prompt_lines.extend([
            f"## {shot.get('shot_id')}",
            f"- 镜头意图：{shot.get('intent_summary') or '未提供'}",
            f"- 场景摘要：{shot.get('scene_summary')}",
            f"- 地点：{(shot.get('story_anchor_bundle') or {}).get('location') or '未指定'}",
            f"- 天气：{(shot.get('story_anchor_bundle') or {}).get('weather') or '未指定'}",
            f"- 关键道具：{(shot.get('story_anchor_bundle') or {}).get('key_prop') or '无'}",
            f"- 情绪变化：{(shot.get('story_anchor_bundle') or {}).get('emotion') or '未指定'}",
            f"- 构图重点：{(shot.get('story_anchor_bundle') or {}).get('composition_focus') or '未指定'}",
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
        f"- 是否覆盖 storyboard 全部镜头：{'是' if ((template.get('self_check') or {}).get('covers_all_storyboard_shots')) else '否'}",
        f"- 是否保留角色一致性锚点：{'是' if ((template.get('self_check') or {}).get('uses_character_consistency')) else '否'}",
        f"- 角色参考图就绪：{'是' if ((template.get('reference_image_status') or {}).get('all_present')) else '否'}",
        f"- 是否可安全自动进入 Stage 05：{'是' if ((template.get('stage05_execution_readiness') or {}).get('safe_to_auto_generate')) else '否'}",
        (
            "- 下一步：先补齐这些角色参考图，再运行 Stage 05 自动生图："
            + "、".join(str(path_text) for path_text in ((template.get("stage05_execution_readiness") or {}).get("missing_reference_images") or []))
        )
        if ((template.get("stage05_execution_readiness") or {}).get("missing_reference_images"))
        else "- 下一步：待用户确认后进入 Stage 05。"
    ]
    write_text(out_path.parent / "keyframe_prompts.md", "\n".join(prompt_lines))
    (out_path.parent / "motion_prompts.json").write_text(json.dumps({"project_id": template.get("project_id"), "records": motion_records}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_text(out_path.parent / "prompt_review.md", "\n".join(review_lines))
    write_stage04_reference_handoff(out_path, template)


def build_keyframe_payload(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    character_bible: dict[str, Any],
    llm_output: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    storyboard_path: Path,
    character_path: Path,
) -> dict[str, Any]:
    ensure_shape(llm_output)
    compiled, quality_contract, quality_targets = strategy_bundle(brief, "STAGE_04")
    anchors = resolve_upstream_story_anchors(character_bible, storyboard, script)
    shot_prompts = [item for item in list(llm_output.get("shot_prompts") or []) if isinstance(item, dict)]
    for shot in shot_prompts:
        consistency_prompt = str(shot.get("consistency_prompt") or "").strip()
        scene_summary = str(shot.get("scene_summary") or "").strip()
        motion_prompt = str(shot.get("motion_prompt") or "").strip()
        shot.setdefault("identity_anchor_prompt", consistency_prompt or "Preserve the same protagonist identity across frames.")
        shot.setdefault("performance_prompt", motion_prompt or scene_summary or "Keep movement natural and emotionally restrained.")
        shot.setdefault("dialogue_delivery_prompt", "")
        shot.setdefault("intent_summary", scene_summary or "Keep the shot aligned with the approved storyboard intent.")
    reference_image_status = character_bible.get("reference_image_status") if isinstance(character_bible.get("reference_image_status"), dict) else {}
    stage05_execution_readiness = build_stage05_execution_readiness(
        continuity_mode=str(compiled.get("continuity_mode") or ""),
        reference_image_required=bool(character_bible.get("reference_image_required")),
        reference_image_status=reference_image_status,
    )
    self_check = dict(llm_output.get("self_check") or {})
    self_check["character_reference_images_ready"] = bool(reference_image_status.get("all_present"))
    self_check["safe_for_auto_image_generation"] = bool(stage05_execution_readiness.get("safe_to_auto_generate"))
    notes = self_check.get("notes") if isinstance(self_check.get("notes"), list) else []
    missing_reference_images = stage05_execution_readiness.get("missing_reference_images") if isinstance(stage05_execution_readiness.get("missing_reference_images"), list) else []
    if missing_reference_images:
        notes = [
            *notes,
            "Stage 05 automatic generation is not safe yet because character reference images are still missing: "
            + ", ".join(str(path_text) for path_text in missing_reference_images),
        ]
    self_check["notes"] = notes
    return {
        "schema_version": "0.5.0",
        "stage": "STAGE_04_KEYFRAME_PROMPTS",
        "status": str(llm_output.get("status") or "draft"),
        "project_id": str(brief.get("project_id") or character_bible.get("project_id") or storyboard.get("project_id") or ""),
        "source_brief": str(brief_path.resolve()).replace("\\", "/"),
        "source_script": str(script_path.resolve()).replace("\\", "/"),
        "source_storyboard": str(storyboard_path.resolve()).replace("\\", "/"),
        "source_character_bible": str(character_path.resolve()).replace("\\", "/"),
        "prompt_language": str(llm_output.get("prompt_language") or "English generation prompts with Chinese review notes"),
        "visual_strategy": dict(llm_output.get("visual_strategy") or {
            "keyframe_mode": "start_and_end_keyframes_per_shot",
            "video_mode": "image_to_video_per_shot",
            "continuity_strategy": "reuse character consistency prompts and adjacent-shot transition requirements",
        }),
        "story_anchors": anchors,
        "shot_prompts": shot_prompts,
        "transition_prompts": list(llm_output.get("transition_prompts") or []),
        "global_negative_prompt": str(llm_output.get("global_negative_prompt") or ""),
        "reference_image_status": reference_image_status,
        "stage05_execution_readiness": stage05_execution_readiness,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing_from_brief(brief),
        "self_check": self_check,
        "allowed_next_stage": None,
    }


def write_stage04_outputs(
    brief: dict[str, Any],
    script: dict[str, Any],
    storyboard: dict[str, Any],
    character_bible: dict[str, Any],
    llm_output: dict[str, Any],
    brief_path: Path,
    script_path: Path,
    storyboard_path: Path,
    character_path: Path,
    llm_output_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    payload = build_keyframe_payload(brief, script, storyboard, character_bible, llm_output, brief_path, script_path, storyboard_path, character_path)
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stage04_llm_output.json").write_text(json.dumps(llm_output, ensure_ascii=False, indent=2), encoding="utf-8")
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage04_companions(out_path, payload)
    return payload


def main(argv: list[str]) -> int:
    if len(argv) != 7:
        print("Usage: python write_stage04_outputs.py <locked_brief.json> <script.json> <storyboard.json> <character_bible.json> <stage04_llm_output.json> <keyframe_prompts.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    script_path = Path(argv[2])
    storyboard_path = Path(argv[3])
    character_path = Path(argv[4])
    llm_output_path = Path(argv[5])
    out_path = Path(argv[6])
    brief = load_json(brief_path)
    script = load_json(script_path)
    storyboard = load_json(storyboard_path)
    character_bible = load_json(character_path)
    llm_output = load_json(llm_output_path)
    write_stage04_outputs(brief, script, storyboard, character_bible, llm_output, brief_path, script_path, storyboard_path, character_path, llm_output_path, out_path)
    print(f"STAGE04_OUTPUTS_WRITTEN: {out_path.parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
