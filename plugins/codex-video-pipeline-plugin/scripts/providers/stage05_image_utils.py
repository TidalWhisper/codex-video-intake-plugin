#!/usr/bin/env python3
from __future__ import annotations

import json
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.stage05_quality_gates import build_auto_repair_plan, build_creator_review_card, build_quality_gate, summarize_quality_review, UMBRELLA_HINTS  # noqa: E402

KNOWN_PLUGIN_ROOT_CHILDREN = {
    "video_projects",
    "templates",
    "config",
    "workflows",
    "skills",
    "scripts",
    "tests",
    "docs",
    "prompts",
}

DEFAULT_STAGE05_NEGATIVE_HINTS = (
    "text",
    "typography",
    "letters",
    "caption",
    "subtitle",
    "watermark",
    "logo",
)

GAME_CG_NEGATIVE_HINTS = (
    "wordmark",
    "headline text",
    "title card",
    "title plaque",
    "cover layout",
    "badge emblem",
    "ui frame",
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def plugin_root_for_manifest(manifest_path: Path) -> Path | None:
    return next(
        (anchor.resolve() for anchor in [manifest_path.parent, *manifest_path.parents] if anchor.name == "codex-video-pipeline-plugin"),
        None,
    )


def resolve_path(base_json: Path, raw: Any) -> Path:
    p = Path(str(raw))
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    special_roots: list[Path] = []
    plugin_root = next(
        (anchor.resolve() for anchor in [base_json.parent, *base_json.parents] if anchor.name == "codex-video-pipeline-plugin"),
        None,
    )
    repo_root = plugin_root.parent.parent.resolve() if plugin_root and plugin_root.parent.name == "plugins" else None
    if p.parts:
        first = p.parts[0].lower()
        if first == "plugins" and repo_root is not None:
            special_roots.append(repo_root)
        elif first in KNOWN_PLUGIN_ROOT_CHILDREN and plugin_root is not None:
            special_roots.append(plugin_root)
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [*special_roots, Path.cwd(), base_json.parent, *base_json.parents]:
        key = str(anchor.resolve()).lower()
        if key not in seen:
            anchors.append(anchor)
            seen.add(key)
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.exists():
            return candidate
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.parent.exists():
            return candidate
    return (base_json.parent / p).resolve()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mentions_any(text: str, hints: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(hint.lower() in lowered for hint in hints)


def _prop_guardrail_sections(job: dict[str, Any]) -> list[str]:
    joined = " ".join(
        str(job.get(key) or "")
        for key in ["prompt", "style_prompt", "consistency_prompt", "camera_prompt", "negative_prompt"]
    )
    if _mentions_any(joined, UMBRELLA_HINTS):
        return [
            "Composition: one person only and one umbrella only in the entire frame, no second umbrella, no duplicate canopy, no extra umbrella in background or foreground, no mirrored accessory duplication",
            "Pose: single subject, exactly two arms and two hands, natural shoulder and elbow anatomy, one umbrella with one handle only, umbrella held by one believable visible hand or by both hands on the same single handle, the other hand must not hold a second prop, no duplicated hand or floating prop interaction",
            "Avoid: extra hands, extra fingers, duplicated arm, broken wrist, umbrella handle detached from hand, floating umbrella, impossible grip, second umbrella, duplicate umbrella canopy, overlapping parasol, mirrored limb anatomy",
        ]
    return []


def _route_guardrail_sections(job: dict[str, Any]) -> list[str]:
    route_key = str(job.get("stage05_route_key") or "").strip()
    if route_key == "game_cg":
        return [
            "Output: deliver clean full-bleed artwork only for downstream video use, not a finished poster, cover, title card, or marketing layout",
            "Composition: no footer title plaque, no centered wordmark, no logo badge, no caption band, no UI frame, no floating emblem, and no fake engraved scene text",
            "Instruction: if the request implies splash art or key art, interpret it as artwork-only image content without any rendered lettering or branding elements",
        ]
    return []


def effective_negative_prompt(job: dict[str, Any]) -> str:
    existing = [item.strip() for item in str(job.get("negative_prompt") or "").split(",") if item.strip()]
    existing.extend(
        item.strip()
        for item in (job.get("repair_negative_prompt_additions") or [])
        if isinstance(item, str) and item.strip()
    )
    seen = {item.lower() for item in existing}
    merged = list(existing)
    for hint in DEFAULT_STAGE05_NEGATIVE_HINTS:
        if hint.lower() not in seen:
            merged.append(hint)
            seen.add(hint.lower())
    if str(job.get("stage05_route_key") or "").strip() == "game_cg":
        for hint in GAME_CG_NEGATIVE_HINTS:
            if hint.lower() not in seen:
                merged.append(hint)
                seen.add(hint.lower())
    return ", ".join(merged)


def build_provider_prompt(job: dict[str, Any]) -> str:
    sections: list[str] = []
    base_prompt = str(job.get("prompt") or "").strip()
    if base_prompt:
        sections.append(base_prompt)
    for label, key in [
        ("Style", "style_prompt"),
        ("Consistency", "consistency_prompt"),
        ("Identity", "identity_anchor_prompt"),
        ("Camera", "camera_prompt"),
    ]:
        value = str(job.get(key) or "").strip()
        if value:
            sections.append(f"{label}: {value}")
    sections.extend(_prop_guardrail_sections(job))
    sections.extend(_route_guardrail_sections(job))
    for item in job.get("repair_prompt_sections") or []:
        if isinstance(item, str) and item.strip():
            sections.append(item.strip())
    negative = effective_negative_prompt(job)
    if negative:
        sections.append(f"Avoid: {negative}")
    return "\n".join(sections).strip()


def append_error(job: dict[str, Any], provider_name: str, message: str) -> None:
    job["status"] = "failed"
    job["provider"] = provider_name
    job.setdefault("errors", [])
    job["errors"].append({
        "type": "provider_error",
        "provider": provider_name,
        "message": message,
        "created_at": utc_now(),
    })
    job.setdefault("evidence", {})
    job["evidence"]["created_at"] = None


def missing_character_reference_block(job: dict[str, Any]) -> dict[str, Any] | None:
    gate = build_quality_gate(job)
    risk_tags = [str(tag).strip() for tag in (gate.get("risk_tags") or []) if str(tag).strip()]
    missing_reference_images = [
        str(item).replace("\\", "/")
        for item in (job.get("missing_reference_images") or [])
        if isinstance(item, str) and str(item).strip()
    ]
    if "missing_character_reference" not in risk_tags or not missing_reference_images:
        return None
    return {
        "image_id": str(job.get("image_id") or "").strip() or None,
        "shot_id": str(job.get("shot_id") or "").strip() or None,
        "frame_role": str(job.get("frame_role") or "").strip() or None,
        "risk_tags": risk_tags,
        "reason": (
            "Blocked before generation: this character-locked high-risk shot is missing a Stage 03 reference image, "
            "so prompt-only Stage 05 generation would likely drift into a different person."
        ),
        "creator_summary": "当前镜头缺少角色参考图，继续生图最容易出现 start / mid / end 不是同一个人。",
        "missing_reference_images": missing_reference_images,
        "reference_images": [
            str(item).replace("\\", "/")
            for item in (job.get("reference_images") or [])
            if isinstance(item, str) and str(item).strip()
        ],
        "recovery_steps": [
            "先补齐 Stage 03 角色参考图，再重跑当前关键帧。",
            "至少提供主角正向清晰参考图，保证脸型、发型、服装轮廓和主要随身物跨帧固定。",
            "补图后优先重跑 start / mid / end 全套关键帧，再人工横向核对是不是同一个人。",
        ],
    }


def append_blocked(
    job: dict[str, Any],
    provider_name: str,
    message: str,
    *,
    error_type: str = "preflight_blocked",
    details: dict[str, Any] | None = None,
) -> None:
    job["status"] = "blocked"
    job["provider"] = provider_name
    job.setdefault("errors", [])
    job["errors"].append({
        "type": error_type,
        "provider": provider_name,
        "message": message,
        "details": details or {},
        "created_at": utc_now(),
    })
    job.setdefault("evidence", {})
    job["evidence"].update({
        "file_exists": False,
        "file_size_bytes": 0,
        "created_at": None,
    })
    job["notes"] = message


def _sync_stage05_manifest_command(manifest_path: Path) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "sync_keyframe_image_manifest.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/sync_keyframe_image_manifest.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    return f"python {runner_text} {manifest_text}"


def _reference_bootstrap_command(manifest_path: Path, *, target_reference_path: str, source_image_id: str | None = None) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "bootstrap_reference_image_from_keyframe.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/bootstrap_reference_image_from_keyframe.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    command = f"python {runner_text} {manifest_text} --target-reference {target_reference_path}"
    if source_image_id:
        command += f" --source-image-id {source_image_id}"
    return command


def reference_bootstrap_candidates(
    manifest_path: Path,
    *,
    missing_reference_images: list[str],
) -> list[dict[str, Any]]:
    data = load_json(manifest_path)
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    missing_set = {
        str(item).replace("\\", "/")
        for item in missing_reference_images
        if isinstance(item, str) and str(item).strip()
    }
    candidates: list[dict[str, Any]] = []
    review_rank = {
        "approved": 220,
        "not_required": 180,
        "pending": 80,
    }
    frame_rank = {
        "start": 30,
        "end": 20,
        "mid": 10,
    }
    for job in jobs:
        if not isinstance(job, dict):
            continue
        reference_images = {
            str(item).replace("\\", "/")
            for item in (job.get("reference_images") or [])
            if isinstance(item, str) and str(item).strip()
        }
        matched_targets = sorted(reference_images & missing_set)
        if not matched_targets:
            continue
        output_raw = job.get("evidence", {}).get("file_path") or job.get("output_path")
        if not output_raw:
            continue
        output_path = resolve_path(manifest_path, output_raw)
        if not output_path.exists() or not output_path.is_file() or output_path.stat().st_size <= 0:
            continue
        gate = job.get("quality_gate") if isinstance(job.get("quality_gate"), dict) else {}
        risk_tags = {
            str(tag).strip()
            for tag in (gate.get("risk_tags") or [])
            if str(tag).strip()
        }
        score = 1000
        score += review_rank.get(str(gate.get("manual_review_status") or "").strip(), 0)
        score += frame_rank.get(str(job.get("frame_role") or "").strip(), 0)
        if "umbrella_prop_contact" not in risk_tags:
            score += 40
        if "missing_character_reference" not in risk_tags:
            score += 20
        candidates.append({
            "image_id": str(job.get("image_id") or "").strip() or None,
            "shot_id": str(job.get("shot_id") or "").strip() or None,
            "frame_role": str(job.get("frame_role") or "").strip() or None,
            "source_path": str(output_path).replace("\\", "/"),
            "target_reference_paths": matched_targets,
            "score": score,
        })
    candidates.sort(
        key=lambda item: (
            -int(item.get("score") or 0),
            str(item.get("shot_id") or ""),
            str(item.get("frame_role") or ""),
            str(item.get("image_id") or ""),
        )
    )
    return candidates


def build_missing_reference_manual_recovery(manifest_path: Path, blocked_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    keyframes_dir = manifest_path.parent / "keyframes"
    keyframes_dir_text = str(keyframes_dir).replace("\\", "/")
    missing_paths: list[str] = []
    blocked_image_ids: list[str] = []
    for item in blocked_jobs:
        blocked_image_ids.append(str(item.get("image_id") or ""))
        for path_text in item.get("missing_reference_images") or []:
            normalized = str(path_text).replace("\\", "/")
            if normalized not in missing_paths:
                missing_paths.append(normalized)
    bootstrap_candidates = reference_bootstrap_candidates(
        manifest_path,
        missing_reference_images=missing_paths,
    )
    suggested_command = None
    if bootstrap_candidates:
        preferred = bootstrap_candidates[0]
        target_path = str((preferred.get("target_reference_paths") or [None])[0] or "")
        if target_path:
            suggested_command = _reference_bootstrap_command(
                manifest_path,
                target_reference_path=target_path,
                source_image_id=str(preferred.get("image_id") or "").strip() or None,
            )
    steps = [
        "1. 先补齐 Stage 03 角色参考图，至少提供主角清晰正向参考图。",
        f"2. 缺失参考图优先补到这些路径：{', '.join(missing_paths) if missing_paths else '03_characters/reference_images/...'}。",
    ]
    if suggested_command:
        steps.append(f"3. 如果当前项目里已经有一张可用关键帧，可以直接回填角色锚图：`{suggested_command}`。")
        steps.append("4. 回填后会自动刷新 Stage 03 / Stage 05 状态，并把 realistic 路线切到 reference-guided 工作流。")
        steps.append("5. 再重跑当前 Stage 05 执行器，并横向核对 start / mid / end 是否为同一人物。")
    else:
        steps.append("3. 补图后重新运行当前 Stage 05 执行器，并横向核对 start / mid / end 是否为同一人物。")
    steps.append(f"6. 如需人工兜底，也请把修正后的关键帧放到 {keyframes_dir_text} 后再执行 `{_sync_stage05_manifest_command(manifest_path)}`。")
    return {
        "status": "required",
        "reason": "高风险 character-locked 镜头缺少 Stage 03 角色参考图，已阻断自动生图。",
        "blocked_image_ids": blocked_image_ids,
        "missing_reference_images": missing_paths,
        "bootstrap_candidates": bootstrap_candidates[:3],
        "suggested_bootstrap_command": suggested_command,
        "steps": steps,
        "created_at": utc_now(),
    }


def _review_queue_markdown_lines(data: dict[str, Any], manifest_path: Path | None = None) -> list[str]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []
    runtime = data.get("creator_runtime_status") if isinstance(data.get("creator_runtime_status"), dict) else {}
    manual_recovery = data.get("manual_recovery") if isinstance(data.get("manual_recovery"), dict) else {}
    lines = [
        "# Stage 05 Manual Review",
        "",
        f"- 项目：`{data.get('project_id')}`",
        f"- 当前状态：`{data.get('status')}`",
        f"- 高风险图片数：{quality_review.get('risky_image_count', 0)}",
        f"- 待人工复核数：{quality_review.get('pending_count', 0)}",
        f"- 可直接进入 Stage 06：`{'yes' if data.get('self_check', {}).get('ready_for_video_clip_generation') else 'no'}`",
        "",
    ]
    if runtime.get("headline"):
        lines.extend([
            "## 运行提示",
            "",
            f"- {runtime.get('headline')}",
        ])
        if runtime.get("detail"):
            lines.append(f"- {runtime.get('detail')}")
        if runtime.get("review_headline"):
            lines.append(f"- {runtime.get('review_headline')}")
        lines.append("")
    bootstrap_command = str(manual_recovery.get("suggested_bootstrap_command") or "").strip()
    if bootstrap_command:
        lines.extend([
            "## 先补角色锚图",
            "",
            f"- 推荐先执行：`{bootstrap_command}`",
            "- 这会把当前项目里已生成的一张关键帧回填为 Stage 03 角色参考图，并自动刷新 Stage 03 / Stage 05 状态。",
            "",
        ])
        bootstrap_candidates = manual_recovery.get("bootstrap_candidates") if isinstance(manual_recovery.get("bootstrap_candidates"), list) else []
        if bootstrap_candidates:
            lines.extend([
                "## 可用回填候选",
                "",
            ])
            for item in bootstrap_candidates:
                if not isinstance(item, dict):
                    continue
                image_id = str(item.get("image_id") or "").strip() or "unknown"
                shot_id = str(item.get("shot_id") or "").strip() or "-"
                frame_role = str(item.get("frame_role") or "").strip() or "-"
                source_path = str(item.get("source_path") or "").strip() or "-"
                targets = ", ".join(str(path_text) for path_text in (item.get("target_reference_paths") or []) if str(path_text).strip())
                lines.append(f"- `{image_id}` (`{shot_id}` / `{frame_role}`) -> `{targets or '03_characters/reference_images/...'}`")
                lines.append(f"  来源：`{source_path}`")
            lines.append("")
    if not queue:
        lines.extend([
            "## 复核结论",
            "",
            "当前没有高风险镜头，按常规抽查关键帧即可。",
            "",
        ])
        return lines
    next_ids = quality_review.get("next_review_image_ids") if isinstance(quality_review.get("next_review_image_ids"), list) else []
    if next_ids:
        lines.extend([
            "## 建议先看",
            "",
            "- " + " -> ".join(f"`{item}`" for item in next_ids if str(item).strip()),
            "",
        ])
    if manifest_path is not None:
        lines.extend([
            "## 看完后的推进",
            "",
            f"- 如果想用本地可点击工作台，先启动：`{_workbench_payload(data, manifest_path).get('quick_actions', {}).get('serve_workbench_command')}`",
            f"- 这批图确认可用后，可先执行：`{_approve_command_for_manifest(manifest_path, top=min(3, max(1, len(next_ids) or 1)))}`",
            "- 批准时必须补上 `--content-aligned --content-alignment-note \"...\"`，明确确认图片内容与镜头文字描述一致。",
            "- 如果只想放行单张，也可以改成 `--image-id IMG_...`。",
            "",
        ])
    top_cards = quality_review.get("top_review_cards") if isinstance(quality_review.get("top_review_cards"), list) else []
    if top_cards:
        lines.extend([
            "## Top 3 快速问题卡",
            "",
        ])
        for card in top_cards:
            if not isinstance(card, dict):
                continue
            image_id = str(card.get("image_id") or "").strip() or "unknown"
            shot_id = str(card.get("shot_id") or "").strip() or "-"
            frame_role = str(card.get("frame_role") or "").strip() or "-"
            lines.append(f"### #{card.get('rank') or '-'} {image_id}")
            lines.append("")
            lines.append(f"- 镜头：`{shot_id}` / `{frame_role}`")
            lines.append(f"- 为什么先看：{card.get('headline') or '高风险镜头'}")
            if card.get("first_check"):
                lines.append(f"- 第一检查点：{card.get('first_check')}")
            if card.get("quick_fix"):
                lines.append(f"- 第一改法：{card.get('quick_fix')}")
            lines.append("")
    lines.extend([
        "## 复核队列",
        "",
    ])
    for item in queue:
        if not isinstance(item, dict):
            continue
        image_id = str(item.get("image_id") or "").strip() or "unknown"
        shot_id = str(item.get("shot_id") or "").strip() or "-"
        frame_role = str(item.get("frame_role") or "").strip() or "-"
        lines.append(f"### {image_id}")
        lines.append("")
        lines.append(f"- 镜头：`{shot_id}` / `{frame_role}`")
        lines.append(f"- 优先级：{item.get('priority_label') or '待定'} ({item.get('priority_score') or 0})")
        if item.get("risk_summary"):
            lines.append(f"- 风险摘要：{item.get('risk_summary')}")
        if item.get("review_focus"):
            lines.append(f"- 先看什么：{item.get('review_focus')}")
        card = None
        jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
        for job in jobs:
            if isinstance(job, dict) and str(job.get("image_id") or "").strip() == image_id:
                card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else None
                preview = str(job.get("repair_preview_path") or "").strip()
                output = str(job.get("evidence", {}).get("file_path") or job.get("output_path") or "").strip()
                blocked_note = str(job.get("notes") or "").strip() if str(job.get("status") or "").strip() == "blocked" else ""
                if output:
                    lines.append(f"- 当前结果：`{output}`")
                if preview:
                    lines.append(f"- 一修前预检：`{preview}`")
                if blocked_note:
                    lines.append(f"- 当前阻断：{blocked_note}")
                break
        checklist = item.get("checklist") if isinstance(item.get("checklist"), list) else []
        if checklist:
            lines.append("- 复核清单：")
            for check in checklist[:3]:
                lines.append(f"  - {check}")
        suggestions = []
        if isinstance(card, dict) and isinstance(card.get("suggestions"), list):
            suggestions = [str(s).strip() for s in card["suggestions"] if str(s).strip()]
        if suggestions:
            lines.append("- 改法建议：")
            for suggestion in suggestions[:3]:
                lines.append(f"  - {suggestion}")
        if isinstance(card, dict) and card.get("next_step"):
            lines.append(f"- 下一步：{card.get('next_step')}")
        lines.append("")
    return lines


def _job_by_image_id(data: dict[str, Any], image_id: str) -> dict[str, Any] | None:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    for job in jobs:
        if isinstance(job, dict) and str(job.get("image_id") or "").strip() == image_id:
            return job
    return None


def _rerun_command_for_image(manifest_path: Path, image_id: str) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "auto_repair_stage05_review_queue.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/auto_repair_stage05_review_queue.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    return f"python {runner_text} {manifest_text} --image-id {image_id}"


def _approve_command_for_manifest(manifest_path: Path, *, top: int = 1) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = plugin_root / "skills" / "video-keyframe-images" / "scripts" / "approve_stage05_review_queue.py" if plugin_root else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/approve_stage05_review_queue.py")
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    return (
        f'python {runner_text} {manifest_text} --top {max(1, top)} '
        '--content-aligned --content-alignment-note "confirmed content matches shot description"'
    )


def _auto_repair_command_for_manifest(manifest_path: Path, *, image_id: str | None = None, top: int | None = None) -> str:
    plugin_root = plugin_root_for_manifest(manifest_path)
    runner = (
        plugin_root / "skills" / "video-keyframe-images" / "scripts" / "auto_repair_stage05_review_queue.py"
        if plugin_root
        else Path("plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/auto_repair_stage05_review_queue.py")
    )
    runner_text = str(runner.resolve() if isinstance(runner, Path) and runner.is_absolute() else runner).replace("\\", "/")
    manifest_text = str(manifest_path.resolve()).replace("\\", "/")
    command = f"python {runner_text} {manifest_text}"
    if image_id:
        command += f" --image-id {image_id}"
    elif top is not None:
        command += f" --limit {max(1, top)}"
    return command


def _path_to_uri(raw_path: str | None) -> str | None:
    if not raw_path:
        return None
    try:
        return Path(raw_path).resolve().as_uri()
    except ValueError:
        return None


def _workbench_payload(data: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    review_queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []
    runtime = data.get("creator_runtime_status") if isinstance(data.get("creator_runtime_status"), dict) else {}
    provider_decisions = data.get("provider_decisions") if isinstance(data.get("provider_decisions"), list) else []
    top_cards = quality_review.get("top_review_cards") if isinstance(quality_review.get("top_review_cards"), list) else []
    top_limit = min(3, max(1, len(top_cards) or len(review_queue) or 1))
    plugin_root = plugin_root_for_manifest(manifest_path)
    manifest_path_text = str(manifest_path.resolve()).replace("\\", "/")
    if plugin_root:
        serve_script = (plugin_root / "skills" / "video-keyframe-images" / "scripts" / "serve_stage05_review_workbench.py").resolve()
        serve_script_text = str(serve_script).replace("\\", "/")
        serve_workbench_command = f"python {serve_script_text} {manifest_path_text}"
    else:
        serve_workbench_command = (
            "python plugins/codex-video-pipeline-plugin/skills/video-keyframe-images/scripts/serve_stage05_review_workbench.py "
            + manifest_path_text
        )

    cards: list[dict[str, Any]] = []
    for item in review_queue:
        if not isinstance(item, dict):
            continue
        image_id = str(item.get("image_id") or "").strip()
        if not image_id:
            continue
        job = _job_by_image_id(data, image_id)
        if not isinstance(job, dict):
            continue
        evidence_path = str(job.get("evidence", {}).get("file_path") or job.get("output_path") or "").strip()
        preview_path = str(job.get("repair_preview_path") or "").strip() or None
        creator_review_card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else {}
        cards.append({
            "image_id": image_id,
            "shot_id": str(job.get("shot_id") or "").strip() or None,
            "frame_role": str(job.get("frame_role") or "").strip() or None,
            "priority_label": item.get("priority_label"),
            "priority_score": item.get("priority_score"),
            "risk_summary": item.get("risk_summary"),
            "review_focus": item.get("review_focus"),
            "checklist": list(item.get("checklist") or []),
            "suggestions": list(creator_review_card.get("suggestions") or item.get("suggestions") or []),
            "manual_review_status": item.get("manual_review_status"),
            "auto_repair_status": job.get("auto_repair_status"),
            "result_image_path": evidence_path or None,
            "result_image_uri": _path_to_uri(evidence_path),
            "repair_preview_path": preview_path,
            "repair_preview_uri": _path_to_uri(preview_path),
            "approve_command": _approve_command_for_manifest(manifest_path, top=1).replace("--top 1", f"--image-id {image_id}"),
            "auto_repair_command": _auto_repair_command_for_manifest(manifest_path, image_id=image_id),
            "sync_command": _sync_stage05_manifest_command(manifest_path),
        })

    return {
        "project_id": data.get("project_id"),
        "manifest_path": str(manifest_path.resolve()).replace("\\", "/"),
        "generated_at": utc_now(),
        "status": data.get("status"),
        "summary": data.get("summary") if isinstance(data.get("summary"), dict) else {},
        "self_check": data.get("self_check") if isinstance(data.get("self_check"), dict) else {},
        "quality_review": quality_review,
        "creator_runtime_status": runtime,
        "provider_decisions": provider_decisions[-5:],
        "quick_actions": {
            "approve_top_command": _approve_command_for_manifest(manifest_path, top=top_limit),
            "auto_repair_top_command": _auto_repair_command_for_manifest(manifest_path, top=top_limit),
            "sync_manifest_command": _sync_stage05_manifest_command(manifest_path),
            "serve_workbench_command": serve_workbench_command,
            "manual_review_markdown_path": str((manifest_path.parent / "manual_review.md").resolve()).replace("\\", "/"),
            "prompt_patch_plan_path": str((manifest_path.parent / "prompt_patch_plan.json").resolve()).replace("\\", "/"),
        },
        "top_review_cards": top_cards,
        "cards": cards,
    }


def _workbench_html(payload: dict[str, Any]) -> str:
    runtime = payload.get("creator_runtime_status") if isinstance(payload.get("creator_runtime_status"), dict) else {}
    quality_review = payload.get("quality_review") if isinstance(payload.get("quality_review"), dict) else {}
    quick_actions = payload.get("quick_actions") if isinstance(payload.get("quick_actions"), dict) else {}
    cards = payload.get("cards") if isinstance(payload.get("cards"), list) else []

    def _copy_button(command: str, label: str) -> str:
        encoded = json.dumps(command, ensure_ascii=False)
        return f"<button class=\"btn secondary\" type=\"button\" onclick='copyCommand({encoded})'>{html.escape(label)}</button>"

    def _action_button(action: str, image_id: str | None, command: str, label: str, *, secondary: bool = False) -> str:
        action_text = json.dumps(action, ensure_ascii=False)
        image_text = json.dumps(image_id, ensure_ascii=False)
        command_text = json.dumps(command, ensure_ascii=False)
        css_class = "btn secondary" if secondary else "btn"
        return (
            f"<button class=\"{css_class}\" type=\"button\" "
            f"onclick='runWorkbenchAction({action_text}, {image_text}, {command_text})'>{html.escape(label)}</button>"
        )

    card_html: list[str] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        image_uri = str(card.get("result_image_uri") or "").strip()
        image_path = str(card.get("result_image_path") or "").strip()
        preview_uri = str(card.get("repair_preview_uri") or "").strip()
        preview_block = ""
        if preview_uri:
            preview_block = f"""
            <div class="preview-stack">
              <div class="preview-label">一修前预检</div>
              <a href="{html.escape(preview_uri)}" data-local-path="{html.escape(str(card.get('repair_preview_path') or ''))}" target="_blank" rel="noreferrer">
                <img src="{html.escape(preview_uri)}" data-local-path="{html.escape(str(card.get('repair_preview_path') or ''))}" alt="{html.escape(str(card.get('image_id') or 'preview'))}" />
              </a>
            </div>
            """
        checklist = "".join(f"<li>{html.escape(str(item))}</li>" for item in (card.get("checklist") or []))
        suggestions = "".join(f"<li>{html.escape(str(item))}</li>" for item in (card.get("suggestions") or []))
        approve_command = str(card.get("approve_command") or "").strip()
        auto_repair_command = str(card.get("auto_repair_command") or "").strip()
        sync_command = str(card.get("sync_command") or "").strip()
        card_html.append(
            f"""
            <section class="card">
              <div class="visual">
                <div class="preview-stack">
                  <div class="preview-label">当前关键帧</div>
                  <a href="{html.escape(image_uri or '#')}" data-local-path="{html.escape(image_path)}" target="_blank" rel="noreferrer">
                    <img src="{html.escape(image_uri or '')}" data-local-path="{html.escape(image_path)}" alt="{html.escape(str(card.get('image_id') or 'image'))}" />
                  </a>
                </div>
                {preview_block}
              </div>
              <div class="meta">
                <div class="meta-top">
                  <h2>{html.escape(str(card.get("image_id") or ""))}</h2>
                  <span class="badge">{html.escape(str(card.get("priority_label") or "待复核"))}</span>
                </div>
                <p class="muted">镜头：{html.escape(str(card.get("shot_id") or "-"))} / {html.escape(str(card.get("frame_role") or "-"))}</p>
                <p class="summary">{html.escape(str(card.get("risk_summary") or ""))}</p>
                <p><strong>先看什么：</strong>{html.escape(str(card.get("review_focus") or ""))}</p>
                <p><strong>当前状态：</strong>manual={html.escape(str(card.get("manual_review_status") or "-"))}，repair={html.escape(str(card.get("auto_repair_status") or "not_started"))}</p>
                <p><strong>图片路径：</strong><code>{html.escape(image_path)}</code></p>
                <div class="grid">
                  <div>
                    <h3>复核清单</h3>
                    <ul>{checklist or '<li>暂无</li>'}</ul>
                  </div>
                  <div>
                    <h3>修正建议</h3>
                    <ul>{suggestions or '<li>暂无</li>'}</ul>
                  </div>
                </div>
                <div class="actions">
                  <a class="btn" href="{html.escape(image_uri or '#')}" target="_blank" rel="noreferrer">查看原图</a>
                  {_action_button("auto_repair_image", str(card.get("image_id") or "").strip() or None, auto_repair_command, "执行自动二修")}
                  {_action_button("approve_image", str(card.get("image_id") or "").strip() or None, approve_command, "通过当前镜头", secondary=True)}
                  {_copy_button(auto_repair_command, "复制命令")}
                </div>
                <div class="cmd-block">
                  <div class="cmd-label">自动二修</div>
                  <pre>{html.escape(auto_repair_command)}</pre>
                </div>
                <div class="cmd-block">
                  <div class="cmd-label">通过当前镜头</div>
                  <pre>{html.escape(approve_command)}</pre>
                </div>
                <div class="cmd-block">
                  <div class="cmd-label">刷新 manifest</div>
                  <pre>{html.escape(sync_command)}</pre>
                </div>
              </div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Stage 05 审图工作台 - {html.escape(str(payload.get("project_id") or ""))}</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: #fffaf4;
      --panel-2: #ffffff;
      --ink: #2d241f;
      --muted: #6e6057;
      --accent: #b74f2f;
      --accent-soft: #f3d8cd;
      --line: #e7d8cb;
      --shadow: 0 16px 40px rgba(77, 53, 38, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #f8e9d7 0, transparent 26%),
        radial-gradient(circle at top right, #e7f0f8 0, transparent 24%),
        linear-gradient(180deg, #f7f1ea 0%, #efe6db 100%);
    }}
    .shell {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 32px 20px 56px;
    }}
    .hero, .toolbar, .card {{
      background: rgba(255, 250, 244, 0.92);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 28px;
      margin-bottom: 20px;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: 32px;
      line-height: 1.1;
    }}
    .hero p {{
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 16px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      padding: 16px;
      border-radius: 18px;
      background: var(--panel-2);
      border: 1px solid var(--line);
    }}
    .stat strong {{
      display: block;
      font-size: 26px;
      margin-bottom: 6px;
    }}
    .toolbar {{
      padding: 20px;
      margin-bottom: 20px;
    }}
    .toolbar-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      align-items: start;
    }}
    .toolbar pre, .cmd-block pre {{
      margin: 10px 0 0;
      padding: 12px 14px;
      border-radius: 16px;
      background: #241d18;
      color: #fff6ef;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .card {{
      display: grid;
      grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
      gap: 20px;
      padding: 20px;
      margin-bottom: 18px;
    }}
    .visual {{
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .preview-stack {{
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: #f7eee4;
    }}
    .preview-label {{
      padding: 10px 14px;
      font-size: 13px;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      background: rgba(255,255,255,0.8);
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      background: #eadfd3;
    }}
    .meta-top {{
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
    }}
    .meta h2 {{
      margin: 0;
      font-size: 24px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
    }}
    .muted, .summary {{
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin: 16px 0;
    }}
    .grid h3, .cmd-label {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
      color: var(--ink);
    }}
    li {{
      margin-bottom: 8px;
    }}
    .actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin: 18px 0 10px;
    }}
    .btn {{
      appearance: none;
      border: 0;
      cursor: pointer;
      text-decoration: none;
      padding: 12px 16px;
      border-radius: 999px;
      font-weight: 600;
      background: var(--accent);
      color: white;
    }}
    .btn.secondary {{
      background: #fff0e7;
      color: var(--accent);
      border: 1px solid #edc4b2;
    }}
    .empty {{
      padding: 30px;
      border-radius: 24px;
      background: rgba(255,255,255,0.82);
      border: 1px dashed var(--line);
      color: var(--muted);
      text-align: center;
    }}
    .toast {{
      position: fixed;
      right: 16px;
      bottom: 16px;
      background: #241d18;
      color: white;
      padding: 12px 14px;
      border-radius: 14px;
      opacity: 0;
      transform: translateY(10px);
      transition: opacity .2s ease, transform .2s ease;
      pointer-events: none;
    }}
    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
    @media (max-width: 920px) {{
      .card {{ grid-template-columns: 1fr; }}
      .hero h1 {{ font-size: 28px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <h1>Stage 05 审图工作台</h1>
      <p>只保留创作者最关心的信息：先看哪张、哪里最危险、如果不对该怎么重修。</p>
      <p>{html.escape(str(runtime.get("headline") or "当前关键帧已生成，等待人工复核。"))}</p>
      <p>{html.escape(str(runtime.get("detail") or ""))}</p>
      <div class="stats">
        <div class="stat"><strong>{html.escape(str(quality_review.get("pending_count", 0)))}</strong><span>待人工复核</span></div>
        <div class="stat"><strong>{html.escape(str(quality_review.get("risky_image_count", 0)))}</strong><span>高风险镜头</span></div>
        <div class="stat"><strong>{html.escape(str((payload.get("summary") or {{}}).get("generated_image_count", 0)))}</strong><span>已生成关键帧</span></div>
        <div class="stat"><strong>{html.escape('yes' if (payload.get('self_check') or {{}}).get('ready_for_video_clip_generation') else 'no')}</strong><span>可进入 Stage 06</span></div>
      </div>
    </section>

    <section class="toolbar">
      <div class="toolbar-grid">
        <div>
          <h2>一键推进</h2>
          <p class="muted">看完没问题时，直接放行当前 top 队列。</p>
          <div class="actions">
            {_action_button("approve_top", None, str(quick_actions.get("approve_top_command") or ""), "直接通过 Top 队列", secondary=True)}
          </div>
          <pre>{html.escape(str(quick_actions.get("approve_top_command") or ""))}</pre>
        </div>
        <div>
          <h2>自动二修入口</h2>
          <p class="muted">看出明显问题时，优先走 provider-aware 自动二修，而不是手动翻 runner。</p>
          <div class="actions">
            {_action_button("auto_repair_top", None, str(quick_actions.get("auto_repair_top_command") or ""), "执行 Top 队列自动二修")}
          </div>
          <pre>{html.escape(str(quick_actions.get("auto_repair_top_command") or ""))}</pre>
        </div>
        <div>
          <h2>刷新状态</h2>
          <p class="muted">人工替换图片后，用它回写 evidence 和复核状态。</p>
          <div class="actions">
            {_action_button("sync_manifest", None, str(quick_actions.get("sync_manifest_command") or ""), "刷新当前工作台", secondary=True)}
          </div>
          <pre>{html.escape(str(quick_actions.get("sync_manifest_command") or ""))}</pre>
        </div>
      </div>
      <div class="toolbar-grid" style="margin-top:16px;">
        <div>
          <h2>本地工作台服务</h2>
          <p class="muted">如果你希望按钮直接可点生效，而不是只复制命令，先启动这个本地服务入口。</p>
          <pre>{html.escape(str(quick_actions.get("serve_workbench_command") or ""))}</pre>
        </div>
      </div>
    </section>

    {"".join(card_html) if card_html else '<section class="empty">当前没有待复核高风险镜头，可以按常规抽查后继续推进。</section>'}
  </div>
  <div class="toast" id="toast">命令已复制</div>
  <script>
    function localApiUrl(path, localPath) {{
      const encoded = encodeURIComponent(localPath || "");
      return `${{path}}?path=${{encoded}}`;
    }}

    function rewriteLocalFileLinks() {{
      if (!window.location.protocol.startsWith("http")) {{
        return;
      }}
      document.querySelectorAll("[data-local-path]").forEach((node) => {{
        const localPath = node.getAttribute("data-local-path");
        if (!localPath) {{
          return;
        }}
        const targetUrl = localApiUrl("/api/file", localPath);
        if (node.tagName === "IMG") {{
          node.src = targetUrl;
        }} else if (node.tagName === "A") {{
          node.href = targetUrl;
        }}
      }});
    }}

    function showToast(text) {{
      const toast = document.getElementById("toast");
      toast.textContent = text;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 1600);
    }}

    async function copyCommand(text) {{
      try {{
        await navigator.clipboard.writeText(text);
        showToast("命令已复制");
      }} catch (err) {{
        window.prompt("复制下面这条命令：", text);
      }}
    }}

    async function runWorkbenchAction(action, imageId, fallbackCommand) {{
      if (!window.location.protocol.startsWith("http")) {{
        copyCommand(fallbackCommand);
        return;
      }}
      showToast("正在执行，请稍候");
      try {{
        const response = await fetch("/api/action", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{action, image_id: imageId}})
        }});
        const payload = await response.json();
        if (!response.ok || payload.ok !== true) {{
          const detail = payload.output || payload.error || "动作执行失败";
          window.alert(detail);
          showToast("执行失败");
          return;
        }}
        showToast("执行完成，正在刷新");
        window.location.reload();
      }} catch (err) {{
        window.alert(`执行失败：${{err}}`);
        showToast("执行失败");
      }}
    }}

    rewriteLocalFileLinks();
  </script>
</body>
</html>
"""


def _prompt_patch_plan_payload(data: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    top_cards = quality_review.get("top_review_cards") if isinstance(quality_review.get("top_review_cards"), list) else []
    review_queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []

    def build_patch_from_card(card: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(card, dict):
            return None
        image_id = str(card.get("image_id") or "").strip()
        if not image_id:
            return None
        job = _job_by_image_id(data, image_id)
        if not isinstance(job, dict):
            return None
        auto_repair_plan = job.get("auto_repair_plan") if isinstance(job.get("auto_repair_plan"), dict) else None
        if not isinstance(auto_repair_plan, dict):
            auto_repair_plan = build_auto_repair_plan(job, job.get("quality_gate") if isinstance(job.get("quality_gate"), dict) else None)
        creator_review_card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else {}
        prompt_sections = [str(item).strip() for item in (auto_repair_plan.get("repair_prompt_sections") or []) if str(item).strip()]
        negative_hints = [str(item).strip() for item in (auto_repair_plan.get("repair_negative_hints") or []) if str(item).strip()]
        current_negative = [item.strip() for item in str(job.get("negative_prompt") or "").split(",") if item.strip()]
        merged_negative = current_negative[:]
        for hint in negative_hints:
            if hint.lower() not in {item.lower() for item in merged_negative}:
                merged_negative.append(hint)
        return {
            "rank": card.get("rank"),
            "image_id": image_id,
            "shot_id": job.get("shot_id"),
            "frame_role": job.get("frame_role"),
            "priority_label": card.get("priority_label"),
            "priority_score": card.get("priority_score"),
            "risk_summary": card.get("headline"),
            "current_prompt": job.get("prompt"),
            "prompt_patch_sections": prompt_sections,
            "patched_prompt_preview": "\n".join([str(job.get("prompt") or "").strip(), *prompt_sections]).strip(),
            "current_negative_prompt": str(job.get("negative_prompt") or "").strip(),
            "negative_prompt_additions": negative_hints,
            "patched_negative_prompt_preview": ", ".join(merged_negative),
            "quick_fix": card.get("quick_fix") or ((creator_review_card.get("suggestions") or [None])[0] if isinstance(creator_review_card, dict) else None),
            "review_focus": card.get("review_focus") or card.get("first_check"),
            "repair_preview_path": job.get("repair_preview_path"),
            "result_image_path": (job.get("evidence", {}) or {}).get("file_path") or job.get("output_path"),
            "rerun_command": _rerun_command_for_image(manifest_path, image_id),
            "creator_review_card": creator_review_card,
        }

    all_patches: list[dict[str, Any]] = []
    for index, item in enumerate(review_queue):
        if not isinstance(item, dict):
            continue
        queue_card = dict(item)
        queue_card.setdefault("rank", index + 1)
        patch = build_patch_from_card(queue_card)
        if patch:
            all_patches.append(patch)

    top_patches: list[dict[str, Any]] = []
    for card in top_cards:
        patch = build_patch_from_card(card)
        if patch:
            top_patches.append(patch)
    return {
        "project_id": data.get("project_id"),
        "manifest_path": str(manifest_path.resolve()).replace("\\", "/"),
        "generated_at": utc_now(),
        "patch_count": len(top_patches),
        "queue_patch_count": len(all_patches),
        "top_prompt_patches": top_patches,
        "all_prompt_patches": all_patches,
    }


def _prompt_patch_markdown_lines(plan: dict[str, Any]) -> list[str]:
    patches = plan.get("top_prompt_patches") if isinstance(plan.get("top_prompt_patches"), list) else []
    lines = [
        "# Stage 05 Prompt Patch Cards",
        "",
        f"- 项目：`{plan.get('project_id')}`",
        f"- Patch 数量：{plan.get('patch_count', 0)}",
        "",
    ]
    if not patches:
        lines.extend([
            "当前没有需要生成 prompt patch 的高风险镜头。",
            "",
        ])
        return lines
    for patch in patches:
        if not isinstance(patch, dict):
            continue
        lines.append(f"## #{patch.get('rank') or '-'} {patch.get('image_id') or 'unknown'}")
        lines.append("")
        lines.append(f"- 镜头：`{patch.get('shot_id') or '-'}` / `{patch.get('frame_role') or '-'}`")
        if patch.get("risk_summary"):
            lines.append(f"- 风险：{patch.get('risk_summary')}")
        if patch.get("review_focus"):
            lines.append(f"- 先改什么：{patch.get('review_focus')}")
        if patch.get("quick_fix"):
            lines.append(f"- 最短改法：{patch.get('quick_fix')}")
        lines.append("- Prompt 补丁：")
        for item in patch.get("prompt_patch_sections") or []:
            lines.append(f"  - {item}")
        lines.append("- Negative 补丁：")
        for item in patch.get("negative_prompt_additions") or []:
            lines.append(f"  - {item}")
        if patch.get("rerun_command"):
            lines.append(f"- 单图重跑：`{patch.get('rerun_command')}`")
        lines.append("")
    return lines


def write_stage05_manual_review_files(data: dict[str, Any], manifest_path: Path) -> None:
    lines = _review_queue_markdown_lines(data, manifest_path)
    content = "\n".join(lines)
    write_text(manifest_path.parent / "manual_review.md", content)
    write_text(manifest_path.parent / "image_review.md", content)


def write_stage05_prompt_patch_files(data: dict[str, Any], manifest_path: Path) -> None:
    plan = _prompt_patch_plan_payload(data, manifest_path)
    write_json(manifest_path.parent / "prompt_patch_plan.json", plan)
    write_text(manifest_path.parent / "prompt_patch_cards.md", "\n".join(_prompt_patch_markdown_lines(plan)))


def write_stage05_review_workbench_files(data: dict[str, Any], manifest_path: Path) -> None:
    payload = _workbench_payload(data, manifest_path)
    write_json(manifest_path.parent / "stage05_review_workbench.json", payload)
    write_text(manifest_path.parent / "stage05_review_workbench.html", _workbench_html(payload))


def update_manifest_state(data: dict[str, Any], manifest_path: Path) -> None:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    generated = 0
    failed = 0
    shots: dict[str, set[str]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        shot_id = job.get("shot_id")
        frame_role = job.get("frame_role")
        if isinstance(shot_id, str) and isinstance(frame_role, str):
            shots.setdefault(shot_id, set()).add(frame_role)
        output_path = job.get("output_path") or job.get("evidence", {}).get("file_path")
        resolved = resolve_path(manifest_path, output_path)
        exists = resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0
        job.setdefault("evidence", {})
        job["evidence"]["file_path"] = str(resolved).replace("\\", "/")
        job["evidence"]["file_exists"] = exists
        job["evidence"]["file_size_bytes"] = resolved.stat().st_size if exists else 0
        job["quality_gate"] = build_quality_gate(job)
        creator_review_card = build_creator_review_card(
            job,
            job["quality_gate"],
            auto_repair_status=str(job.get("auto_repair_status") or "").strip() or None,
        )
        if creator_review_card:
            existing_card = job.get("creator_review_card") if isinstance(job.get("creator_review_card"), dict) else {}
            creator_review_card.update(existing_card)
            if "auto_repair_status" not in creator_review_card and job.get("auto_repair_status"):
                creator_review_card["auto_repair_status"] = job.get("auto_repair_status")
            if job.get("repair_preview_path") and "repair_preview_path" not in creator_review_card:
                creator_review_card["repair_preview_path"] = job.get("repair_preview_path")
            job["creator_review_card"] = creator_review_card
        if exists:
            generated += 1
        elif job.get("status") in {"failed", "blocked"}:
            failed += 1
    expected = len(jobs)
    all_exist = expected > 0 and generated == expected
    quality_review = summarize_quality_review(jobs)
    manual_review_cleared = bool(quality_review.get("manual_review_cleared"))
    data.setdefault("summary", {})
    data["summary"].update({
        "shot_count": len(shots),
        "expected_image_count": expected,
        "generated_image_count": generated,
        "failed_image_count": failed if failed else max(0, expected - generated),
    })
    data["quality_review"] = quality_review
    provider_status = data.get("creator_runtime_status")
    if not isinstance(provider_status, dict):
        provider_status = {}
    if isinstance(data.get("provider_decisions"), list):
        latest_decision = data["provider_decisions"][-1] if data["provider_decisions"] else None
        if isinstance(latest_decision, dict):
            provider = str(latest_decision.get("provider") or "").strip()
            decision = str(latest_decision.get("decision") or "").strip()
            reason = str(latest_decision.get("reason") or "").strip()
            if provider == "comfyui_txt2img" and decision == "auto_fallback_selected":
                provider_status.update({
                    "headline": "OpenAI 不可用，已自动切到本地 ComfyUI。",
                    "detail": "本地生成通常更慢，但当前任务会继续完成。",
                    "reason": reason,
                })
            elif provider == "manual" and "manual_recovery_required" in decision:
                if reason == "missing_character_reference_before_generation":
                    provider_status.update({
                        "headline": "高风险关键帧已阻断，先补角色参考图。",
                        "detail": "当前镜头缺少 Stage 03 角色参考图，继续自动生图最容易出现 start / mid / end 换人。",
                        "reason": reason,
                    })
                else:
                    provider_status.update({
                        "headline": "自动 provider 无法继续，当前需要人工补位。",
                        "detail": "请按 manifest 中的 manual recovery 指引放置或补修关键帧。",
                        "reason": reason,
                    })
    if quality_review.get("risky_image_count"):
        provider_status["review_headline"] = quality_review.get("creator_feedback_headline")
    if provider_status:
        data["creator_runtime_status"] = provider_status
    data.setdefault("self_check", {})
    notes: list[str] = []
    if not manual_review_cleared and quality_review.get("blocking_image_ids"):
        notes.append(
            "Manual review required before Stage 06 for: "
            + ", ".join(str(item) for item in quality_review["blocking_image_ids"])
        )
    if quality_review.get("next_review_image_ids"):
        notes.append(
            "Review priority queue starts with: "
            + ", ".join(str(item) for item in quality_review["next_review_image_ids"])
        )
    data["self_check"].update({
        "covers_all_keyframe_prompts": expected > 0,
        "has_start_and_end_for_each_shot": all({"start", "end"}.issubset(roles) for roles in shots.values()) if shots else False,
        "all_required_images_exist": all_exist,
        "manual_review_cleared": manual_review_cleared,
        "ready_for_video_clip_generation": all_exist and manual_review_cleared,
        "notes": notes,
    })
    if all_exist:
        data["status"] = "generated"
    elif generated > 0 or failed > 0:
        data["status"] = "in_progress"
    data["allowed_next_stage"] = (
        next_stage_after("STAGE_05_KEYFRAME_IMAGES", routing, "STAGE_06_VIDEO_CLIPS")
        if all_exist and manual_review_cleared
        else None
    )
    data["updated_at"] = utc_now()
    write_stage05_manual_review_files(data, manifest_path)
    write_stage05_prompt_patch_files(data, manifest_path)
    write_stage05_review_workbench_files(data, manifest_path)
