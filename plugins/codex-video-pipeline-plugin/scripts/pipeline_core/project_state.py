from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .media_evidence import MIN_PRODUCTION_VIDEO_BYTES, assembly_output_ready, provider_is_nonproduction


STAGE03_MANIFEST = Path("03_characters/character_bible.json")
STAGE04_MANIFEST = Path("04_keyframes/keyframe_prompts.json")
STAGE05_MANIFEST = Path("05_images/keyframe_image_manifest.json")
STAGE06_MANIFEST = Path("06_video_clips/video_clip_manifest.json")
STAGE07_MANIFEST = Path("07_audio/audio_manifest.json")
STAGE08_MANIFEST = Path("08_assembly/assembly_manifest.json")

EARLY_STAGE_SEQUENCE = [
    ("brief_locked", "STAGE_00_BRIEF_LOCKED", "STAGE_01_SCRIPT_GENERATION"),
    ("script_confirmed", "STAGE_01_SCRIPT_CONFIRMED", "STAGE_02_STORYBOARD"),
    ("storyboard_confirmed", "STAGE_02_STORYBOARD_CONFIRMED", "STAGE_03_CHARACTER_BIBLE"),
    ("character_bible_confirmed", "STAGE_03_CHARACTER_BIBLE_CONFIRMED", "STAGE_04_KEYFRAME_PROMPTS"),
    ("keyframe_prompts_confirmed", "STAGE_04_KEYFRAME_PROMPTS_CONFIRMED", "STAGE_05_KEYFRAME_IMAGES"),
]

CREATOR_STEP_ORDER = ["立项", "剧本", "分镜", "关键帧", "成片"]
ORIGIN_KEYS = ["provider_output", "fallback_output", "manual_import", "placeholder_or_incomplete"]
MANUAL_PROVIDER_PREFIXES = ("manual",)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def load_json_file(path: Path, *, allow_bom: bool = True) -> dict[str, Any]:
    encoding = "utf-8-sig" if allow_bom else "utf-8"
    return json.loads(path.read_text(encoding=encoding))


def write_json_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json_file_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return load_json_file(path)
    except Exception:
        return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any) -> bool:
    return bool(value)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _list_of_str(value: Any) -> list[str]:
    return [str(item).strip() for item in _as_list(value) if str(item or "").strip()]


def _stage01_locked_brief_path(project_dir: Path) -> Path:
    return project_dir / "00_intake" / "project_brief.locked.json"


def _stage01_script_json_path(project_dir: Path) -> Path:
    return project_dir / "01_script" / "script.json"


def _stage01_runner_command(project_dir: Path) -> str:
    locked_brief = _stage01_locked_brief_path(project_dir)
    script_json = _stage01_script_json_path(project_dir)
    return (
        "python skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py "
        f"{as_posix(locked_brief)} {as_posix(script_json)}"
    )


def _stage01_generated(data: dict[str, Any], project_dir: Path) -> bool:
    current_stage = _text(data.get("current_stage"))
    if current_stage == "STAGE_01_SCRIPT_GENERATION":
        return True
    return _stage01_script_json_path(project_dir).exists()


def _origin_counts() -> dict[str, int]:
    return {key: 0 for key in ORIGIN_KEYS}


def classify_evidence_origin(
    *,
    provider: Any,
    file_exists: bool,
    file_size_bytes: int,
    primary_provider: str | None = None,
    fallback_providers: list[str] | None = None,
    production_ready: bool | None = None,
) -> str:
    provider_name = _text(provider).lower()
    fallback_names = {_text(item).lower() for item in (fallback_providers or []) if _text(item)}
    if production_ready is None:
        production_ready = file_exists and file_size_bytes > 0 and not provider_is_nonproduction(provider_name)
    if not file_exists or file_size_bytes <= 0 or not production_ready:
        return "placeholder_or_incomplete"
    if any(provider_name.startswith(prefix) for prefix in MANUAL_PROVIDER_PREFIXES):
        return "manual_import"
    if primary_provider and provider_name == _text(primary_provider).lower():
        return "provider_output"
    if provider_name and provider_name in fallback_names:
        return "fallback_output"
    if provider_name:
        return "provider_output"
    return "placeholder_or_incomplete"


def annotate_evidence_origin(
    evidence: dict[str, Any],
    *,
    provider: Any,
    file_exists: bool,
    file_size_bytes: int,
    primary_provider: str | None = None,
    fallback_providers: list[str] | None = None,
    production_ready: bool | None = None,
) -> str:
    origin = classify_evidence_origin(
        provider=provider,
        file_exists=file_exists,
        file_size_bytes=file_size_bytes,
        primary_provider=primary_provider,
        fallback_providers=fallback_providers,
        production_ready=production_ready,
    )
    evidence["origin_type"] = origin
    evidence["is_production_ready"] = bool(production_ready if production_ready is not None else origin != "placeholder_or_incomplete")
    return origin


def _evidence_summary_text(counts: dict[str, int]) -> str:
    parts: list[str] = []
    mapping = {
        "provider_output": "正式 provider",
        "fallback_output": "fallback",
        "manual_import": "人工导入",
        "placeholder_or_incomplete": "占位/未完成",
    }
    for key in ORIGIN_KEYS:
        count = _int(counts.get(key))
        if count > 0:
            parts.append(f"{mapping[key]} {count}")
    return "，".join(parts) if parts else "暂无产物"


def _read_stage_manifest(project_dir: Path, relative_path: Path) -> tuple[Path, dict[str, Any] | None]:
    manifest_path = project_dir / relative_path
    return manifest_path, load_json_file_if_exists(manifest_path)


def _path_uri(path: Path | str | None) -> str:
    if not path:
        return ""
    try:
        return Path(path).resolve().as_uri()
    except Exception:
        return ""


def _reference_image_actions(project_dir: Path, missing_paths: list[str], bootstrap_command: str) -> list[dict[str, Any]]:
    actions = [{
        "label": "打开角色参考图说明",
        "path": as_posix(project_dir / "03_characters" / "reference_image_start_here.md"),
        "kind": "file",
        "description": "先看系统为普通创作者整理好的补图入口。",
    }]
    if missing_paths:
        actions.append({
            "label": "打开参考图目录",
            "path": as_posix(project_dir / "03_characters" / "reference_images"),
            "kind": "folder",
            "description": "把主角参考图直接放进这个目录。",
        })
    if bootstrap_command:
        actions.append({
            "label": "用现有关键帧回填参考图",
            "command": bootstrap_command,
            "kind": "command",
            "description": "如果 Stage 05 已有一张可用关键帧，可以直接回填成角色锚图。",
        })
    return actions


def _file_size_from_evidence(evidence: dict[str, Any]) -> int:
    return _int(evidence.get("file_size_bytes"))


def _status_from_counts(*, has_jobs: bool, any_output: bool, blocked: bool, manifest_status: str) -> str:
    if blocked:
        return "blocked"
    if any_output:
        return "generated"
    if manifest_status in {"in_progress", "generated"}:
        return "in_progress"
    return "draft" if has_jobs else "draft"


def _derive_stage05_state(project_dir: Path) -> dict[str, Any] | None:
    manifest_path, data = _read_stage_manifest(project_dir, STAGE05_MANIFEST)
    if data is None:
        return None
    strategy = _as_dict(data.get("image_provider_strategy"))
    primary = _text(strategy.get("primary")) or None
    fallback = _list_of_str(strategy.get("fallback"))
    jobs = _as_list(data.get("jobs"))
    counts = _origin_counts()
    blocking_ids = _list_of_str(_as_dict(data.get("quality_review")).get("blocking_image_ids"))
    pending_ids = _list_of_str(_as_dict(data.get("quality_review")).get("next_review_image_ids"))
    generated = 0
    blocked = False
    for job in jobs:
        if not isinstance(job, dict):
            continue
        evidence = job.setdefault("evidence", {})
        file_exists = _bool(evidence.get("file_exists"))
        file_size = _file_size_from_evidence(evidence)
        origin = annotate_evidence_origin(
            evidence,
            provider=job.get("provider"),
            file_exists=file_exists,
            file_size_bytes=file_size,
            primary_provider=primary,
            fallback_providers=fallback,
            production_ready=file_exists and file_size > 0 and not provider_is_nonproduction(job.get("provider")),
        )
        counts[origin] += 1
        if file_exists and file_size > 0:
            generated += 1
        if _text(job.get("status")).lower() == "blocked":
            blocked = True
    self_check = _as_dict(data.get("self_check"))
    quality_review = _as_dict(data.get("quality_review"))
    all_exist = _bool(self_check.get("all_required_images_exist")) or _bool(self_check.get("ready_for_video_clip_generation"))
    manual_review_cleared = (
        _bool(self_check.get("manual_review_cleared"))
        or _bool(quality_review.get("manual_review_cleared"))
        or _bool(self_check.get("ready_for_video_clip_generation"))
    )
    manifest_status = _text(data.get("status")).lower()
    if all_exist and manual_review_cleared:
        normalized = "confirmed"
    elif all_exist and not manual_review_cleared:
        normalized = "review_required"
    else:
        normalized = _status_from_counts(
            has_jobs=bool(jobs),
            any_output=generated > 0,
            blocked=blocked,
            manifest_status=manifest_status,
        )
    blockers: list[str] = []
    if not all_exist:
        blockers.append("Stage 05 关键帧仍未全部生成完成。")
    if all_exist and not manual_review_cleared:
        if blocking_ids:
            blockers.append("Stage 05 仍有高风险图片待人工复核：" + "、".join(blocking_ids[:3]))
        else:
            blockers.append("Stage 05 高风险关键帧尚未清审，不能可信推进到 Stage 06。")
    next_action = (
        "继续生成缺失关键帧。"
        if not all_exist
        else ("优先处理 Stage 05 审图工作台里的待复核图片。" if not manual_review_cleared else "可以安全推进到 Stage 06 视频片段生成。")
    )
    return {
        "manifest_path": as_posix(manifest_path),
        "normalized_status": normalized,
        "confirmed": normalized == "confirmed",
        "all_required_exist": all_exist,
        "ready_for_next_stage": _bool(self_check.get("ready_for_video_clip_generation")),
        "blocking_reasons": blockers,
        "evidence_origin_summary": counts,
        "evidence_summary_text": _evidence_summary_text(counts),
        "provider_summary": {
            "primary": primary,
            "fallback": fallback,
            "headline": _text(_as_dict(data.get("creator_runtime_status")).get("headline")),
            "detail": _text(_as_dict(data.get("creator_runtime_status")).get("detail")),
            "reason": _text(_as_dict(data.get("creator_runtime_status")).get("reason")),
        },
        "pending_review_ids": pending_ids,
        "current_result": f"{generated}/{len(jobs)} 张关键帧已落盘，{_evidence_summary_text(counts)}。",
        "current_blocker": blockers[0] if blockers else "",
        "next_action": next_action,
        "risk_hint": _text(_as_dict(data.get("creator_runtime_status")).get("review_headline")) or (_text(quality_review.get("creator_feedback_headline"))),
    }


def _derive_stage06_state(project_dir: Path) -> dict[str, Any] | None:
    manifest_path, data = _read_stage_manifest(project_dir, STAGE06_MANIFEST)
    if data is None:
        return None
    strategy = _as_dict(data.get("video_provider_strategy"))
    primary = _text(strategy.get("primary")) or None
    fallback = _list_of_str(strategy.get("fallback"))
    jobs = _as_list(data.get("jobs"))
    counts = _origin_counts()
    ready_count = 0
    any_exists = False
    blocked = False
    nonprod = 0
    for job in jobs:
        if not isinstance(job, dict):
            continue
        evidence = job.setdefault("evidence", {})
        file_exists = _bool(evidence.get("file_exists"))
        file_size = _file_size_from_evidence(evidence)
        any_exists = any_exists or file_exists
        production_ready = file_exists and file_size >= MIN_PRODUCTION_VIDEO_BYTES and not provider_is_nonproduction(job.get("provider"))
        origin = annotate_evidence_origin(
            evidence,
            provider=job.get("provider"),
            file_exists=file_exists,
            file_size_bytes=file_size,
            primary_provider=primary,
            fallback_providers=fallback,
            production_ready=production_ready,
        )
        counts[origin] += 1
        if production_ready:
            ready_count += 1
        if origin == "placeholder_or_incomplete":
            nonprod += 1
        if _text(job.get("status")).lower() == "blocked":
            blocked = True
    self_check = _as_dict(data.get("self_check"))
    all_exist = _bool(self_check.get("all_required_clips_exist")) or _bool(self_check.get("ready_for_audio_stage"))
    source_stage05_ready = _bool(self_check.get("source_stage05_ready_for_video_clip_generation"))
    formal_progression_ready = _bool(self_check.get("formal_progression_ready")) or _bool(self_check.get("ready_for_audio_stage"))
    formal_promotion_status = _text(data.get("formal_promotion_status")).lower()
    if all_exist and ready_count == 0 and jobs:
        ready_count = len(jobs)
    if all_exist and nonprod == len(jobs) and jobs:
        nonprod = 0
        counts["provider_output"] = max(counts["provider_output"], len(jobs))
        counts["placeholder_or_incomplete"] = 0
    manifest_status = _text(data.get("status")).lower()
    if formal_progression_ready and all_exist and nonprod == 0:
        normalized = "confirmed"
    elif all_exist and (nonprod > 0 or not source_stage05_ready or formal_promotion_status == "draft_only"):
        normalized = "review_required"
    elif any_exists or manifest_status in {"generated", "in_progress"}:
        normalized = "review_required" if nonprod > 0 else "generated"
    else:
        normalized = _status_from_counts(
            has_jobs=bool(jobs),
            any_output=any_exists,
            blocked=blocked,
            manifest_status=manifest_status,
        )
    blockers: list[str] = []
    if not all_exist:
        blockers.append("Stage 06 片段还不齐，不能正式进入 Stage 07。")
    if all_exist and not source_stage05_ready:
        blockers.append("Stage 05 仍未正式清审，当前 Stage 06 结果只能按草稿态展示。")
    if nonprod > 0:
        blockers.append("Stage 06 仍包含占位或证据不足的 clip，需要真实 provider 输出。")
    next_action = "补齐缺失或占位 clip，并重新同步 Stage 06 manifest。"
    if all_exist and not source_stage05_ready:
        next_action = "先完成 Stage 05 审图清审，再把当前 clip 作为正式结果推进到 Stage 07。"
    if normalized == "confirmed":
        next_action = "可以安全推进到 Stage 07 音频阶段。"
    current_result = f"{ready_count}/{len(jobs)} 个正式 clip 已就绪，{_evidence_summary_text(counts)}。"
    if all_exist and not source_stage05_ready:
        current_result = f"{ready_count}/{len(jobs)} 个 clip 已生成，但 Stage 05 未正式清审，当前仅为草稿态。"
    return {
        "manifest_path": as_posix(manifest_path),
        "normalized_status": normalized,
        "confirmed": normalized == "confirmed",
        "all_required_exist": all_exist,
        "ready_for_next_stage": formal_progression_ready,
        "blocking_reasons": blockers,
        "evidence_origin_summary": counts,
        "evidence_summary_text": _evidence_summary_text(counts),
        "provider_summary": {"primary": primary, "fallback": fallback},
        "current_result": current_result,
        "current_blocker": blockers[0] if blockers else "",
        "next_action": next_action,
        "risk_hint": (
            "当前 clip 已生成，但由于 Stage 05 未正式清审，只能按草稿态展示。"
            if all_exist and not source_stage05_ready
            else ("草稿 clip 和正式 clip 已被分开统计。" if nonprod > 0 else "")
        ),
    }


def _derive_stage07_state(project_dir: Path) -> dict[str, Any] | None:
    manifest_path, data = _read_stage_manifest(project_dir, STAGE07_MANIFEST)
    if data is None:
        return None
    voice_strategy = _as_dict(data.get("voice_provider_strategy"))
    music_strategy = _as_dict(data.get("music_provider_strategy"))
    voice_primary = _text(voice_strategy.get("primary")) or None
    music_primary = _text(music_strategy.get("primary")) or None
    voice_fallback = _list_of_str(voice_strategy.get("fallback"))
    music_fallback = _list_of_str(music_strategy.get("fallback"))
    jobs = _as_list(data.get("jobs"))
    counts = _origin_counts()
    ready_count = 0
    any_exists = False
    for job in jobs:
        if not isinstance(job, dict):
            continue
        evidence = job.setdefault("evidence", {})
        file_exists = _bool(evidence.get("file_exists"))
        file_size = _file_size_from_evidence(evidence)
        any_exists = any_exists or file_exists
        is_music = _text(job.get("audio_type")).lower() == "music"
        origin = annotate_evidence_origin(
            evidence,
            provider=job.get("provider"),
            file_exists=file_exists,
            file_size_bytes=file_size,
            primary_provider=music_primary if is_music else voice_primary,
            fallback_providers=music_fallback if is_music else voice_fallback,
            production_ready=file_exists and file_size > 0 and not provider_is_nonproduction(job.get("provider")),
        )
        counts[origin] += 1
        if file_exists and file_size > 0:
            ready_count += 1
    self_check = _as_dict(data.get("self_check"))
    all_audio = _bool(self_check.get("all_required_audio_files_exist")) or _bool(self_check.get("ready_for_assembly_stage"))
    if all_audio and ready_count == 0 and jobs:
        ready_count = len(jobs)
    if all_audio and counts["placeholder_or_incomplete"] == len(jobs) and jobs:
        counts["provider_output"] = max(counts["provider_output"], len(jobs))
        counts["placeholder_or_incomplete"] = 0
    manifest_status = _text(data.get("status")).lower()
    if all_audio:
        normalized = "confirmed"
    elif any_exists or manifest_status in {"generated", "in_progress"}:
        normalized = "generated"
    else:
        normalized = "draft"
    blockers: list[str] = []
    if not all_audio:
        blockers.append("Stage 07 音频仍未补齐，成片阶段还不能正式推进。")
    next_action = "补齐缺失音频并刷新 Stage 07 音频状态。"
    if normalized == "confirmed":
        next_action = "可以安全推进到 Stage 08 粗剪装配。"
    return {
        "manifest_path": as_posix(manifest_path),
        "normalized_status": normalized,
        "confirmed": normalized == "confirmed",
        "all_required_exist": all_audio,
        "ready_for_next_stage": _bool(self_check.get("ready_for_assembly_stage")),
        "blocking_reasons": blockers,
        "evidence_origin_summary": counts,
        "evidence_summary_text": _evidence_summary_text(counts),
        "provider_summary": {
            "voice_primary": voice_primary,
            "music_primary": music_primary,
            "music_fallback": music_fallback,
        },
        "current_result": f"{ready_count}/{len(jobs)} 条音频已就绪，{_evidence_summary_text(counts)}。",
        "current_blocker": blockers[0] if blockers else "",
        "next_action": next_action,
        "risk_hint": "",
    }


def _derive_stage08_state(project_dir: Path) -> dict[str, Any] | None:
    manifest_path, data = _read_stage_manifest(project_dir, STAGE08_MANIFEST)
    if data is None:
        return None
    evidence = _as_dict(data.setdefault("evidence", {}))
    final_output = Path(_text(data.get("final_output_path") or evidence.get("file_path")))
    output_ready = False
    if final_output.is_absolute():
        output_ready = assembly_output_ready(data, final_output, min_bytes=MIN_PRODUCTION_VIDEO_BYTES)
    else:
        candidate = project_dir / final_output
        output_ready = assembly_output_ready(data, candidate, min_bytes=MIN_PRODUCTION_VIDEO_BYTES)
    file_exists = _bool(evidence.get("file_exists"))
    file_size = _file_size_from_evidence(evidence)
    origin = annotate_evidence_origin(
        evidence,
        provider=data.get("assembly_provider") or "ffmpeg",
        file_exists=file_exists,
        file_size_bytes=file_size,
        primary_provider="ffmpeg",
        fallback_providers=["manual"],
        production_ready=output_ready,
    )
    counts = _origin_counts()
    counts[origin] += 1
    summary = _as_dict(data.get("summary"))
    fallback_segments = _int(summary.get("fallback_visual_segment_count"))
    if fallback_segments <= 0:
        timeline = _as_list(data.get("timeline"))
        fallback_segments = sum(
            1
            for item in timeline
            if isinstance(item, dict)
            and isinstance(item.get("fallback_visual"), dict)
            and not _bool(_as_dict(item.get("fallback_visual")).get("source_clip_ready"))
            and _text(_as_dict(item.get("fallback_visual")).get("preferred_image_path"))
        )
        summary["fallback_visual_segment_count"] = fallback_segments
        data["summary"] = summary
    self_check = _as_dict(data.get("self_check"))
    notes = _list_of_str(self_check.get("notes"))
    blockers = [note.split(":", 1)[1] for note in notes if note.startswith("upstream_blocker:")]
    if not output_ready:
        blockers.insert(0, "Stage 08 粗剪还不是可信完成态，当前输出仍需继续装配或替换正式素材。")
    if fallback_segments > 0:
        blockers.append(f"粗剪中仍有 {fallback_segments} 段使用关键帧 fallback reel。")
    normalized = "confirmed" if output_ready and not blockers else ("review_required" if file_exists else "in_progress")
    next_action = "重新装配粗剪并补齐上游正式素材。"
    if normalized == "confirmed":
        next_action = "可以推进到 Stage 09 QA 交付检查。"
    return {
        "manifest_path": as_posix(manifest_path),
        "normalized_status": normalized,
        "confirmed": normalized == "confirmed",
        "all_required_exist": output_ready,
        "ready_for_next_stage": _bool(self_check.get("ready_for_qa_stage")) and not blockers,
        "blocking_reasons": blockers,
        "evidence_origin_summary": counts,
        "evidence_summary_text": _evidence_summary_text(counts),
        "provider_summary": {"assembly_provider": _text(data.get("assembly_provider") or "ffmpeg")},
        "current_result": f"粗剪输出状态：{_evidence_summary_text(counts)}，fallback 片段 {fallback_segments} 段。",
        "current_blocker": blockers[0] if blockers else "",
        "next_action": next_action,
        "risk_hint": "当前成片链路会明确区分真实 clip 与关键帧 fallback 段落。" if fallback_segments > 0 else "",
    }


def _derive_reference_readiness_state(project_dir: Path) -> dict[str, Any] | None:
    _, character_bible = _read_stage_manifest(project_dir, STAGE03_MANIFEST)
    _, keyframe_prompts = _read_stage_manifest(project_dir, STAGE04_MANIFEST)
    if character_bible is None and keyframe_prompts is None:
        return None
    source = character_bible if character_bible is not None else keyframe_prompts or {}
    reference_status = _as_dict(source.get("reference_image_status"))
    readiness = _as_dict(source.get("stage05_execution_readiness"))
    missing_paths = _list_of_str(reference_status.get("missing_paths") or readiness.get("missing_reference_images"))
    if not missing_paths:
        return {
            "reference_ready": True,
            "safe_to_auto_generate": _bool(readiness.get("safe_to_auto_generate")) or _bool(reference_status.get("all_present")),
            "missing_reference_images": [],
            "current_result": "角色参考图已就绪，关键帧阶段可以按正常路径推进。",
            "current_blocker": "",
            "next_action": "确认当前关键帧提示词后，进入 Stage 05 自动生图。",
            "risk_hint": "",
            "actions": [{
                "label": "打开 Stage 04 交接说明",
                "path": as_posix(project_dir / "04_keyframes" / "stage05_start_here.md"),
                "kind": "file",
                "description": "查看进入 Stage 05 前的默认说明。",
            }],
        }

    _, stage05_manifest = _read_stage_manifest(project_dir, STAGE05_MANIFEST)
    manual_recovery = _as_dict(_as_dict(stage05_manifest).get("manual_recovery"))
    bootstrap_command = _text(manual_recovery.get("suggested_bootstrap_command"))
    return {
        "reference_ready": False,
        "safe_to_auto_generate": False,
        "missing_reference_images": missing_paths,
        "current_result": f"角色参考图还缺 {len(missing_paths)} 张，系统不会冒险自动进入 Stage 05。",
        "current_blocker": "主角参考图还没补齐，所以系统先把关键帧自动生成挡住了。",
        "next_action": (
            "先补一张清晰的主角参考图到 `03_characters/reference_images/`，再继续进入 Stage 05。"
            if not bootstrap_command
            else "先补主角参考图；如果 Stage 05 已经有一张可用关键帧，也可以直接用现有关键帧回填角色参考图。"
        ),
        "risk_hint": "这一步是在避免 start / mid / end 关键帧里的角色换脸或换人。",
        "actions": _reference_image_actions(project_dir, missing_paths, bootstrap_command),
    }


def _creator_steps(
    data: dict[str, Any],
    stage_truth: dict[str, dict[str, Any]],
    reference_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    project_dir = Path(_text(data.get("project_dir")) or ".")
    stage01_command = _stage01_runner_command(project_dir) if _bool(data.get("brief_locked")) else ""
    script_generated = _stage01_generated(data, project_dir)
    early = [
        {
            "step": "立项",
            "status": "confirmed" if _bool(data.get("brief_locked")) else "current",
            "current_result": "项目 brief 已锁定。" if _bool(data.get("brief_locked")) else "项目 brief 仍未锁定。",
            "current_blocker": "" if _bool(data.get("brief_locked")) else "先锁定立项 brief，系统才有可信输入。",
            "next_action": "锁定项目 brief。" if not _bool(data.get("brief_locked")) else "锁 brief 后，自动进入 Stage 01 剧本生成。",
            "risk_hint": "",
        },
        {
            "step": "剧本",
            "status": (
                "confirmed"
                if _bool(data.get("script_confirmed"))
                else ("generated" if script_generated else ("current" if _bool(data.get("brief_locked")) else "pending"))
            ),
            "current_result": (
                "剧本已确认。"
                if _bool(data.get("script_confirmed"))
                else (
                    "Stage 01 剧本已生成，待用户确认。"
                    if script_generated
                    else ("Stage 01 自动剧本生成尚未执行。" if _bool(data.get("brief_locked")) else "剧本仍待确认。")
                )
            ),
            "current_blocker": (
                ""
                if _bool(data.get("script_confirmed"))
                else (
                    "剧本还未确认，不能正式推进到 Stage 02 分镜。"
                    if script_generated
                    else ("锁 brief 后还没跑 Stage 01 自动剧本生成。" if _bool(data.get("brief_locked")) else "剧本未确认前，不建议推进到后续正式链路。")
                )
            ),
            "next_action": (
                "进入分镜阶段。"
                if _bool(data.get("script_confirmed"))
                else ("确认剧本内容。" if script_generated else ("运行 Stage 01 自动剧本生成。" if _bool(data.get("brief_locked")) else "先完成立项并锁定 brief。"))
            ),
            "risk_hint": "",
            "command": stage01_command if _bool(data.get("brief_locked")) and not _bool(data.get("script_confirmed")) and not script_generated else "",
        },
    ]
    storyboard_ready = _bool(data.get("storyboard_confirmed")) and _bool(data.get("character_bible_confirmed")) and _bool(data.get("keyframe_prompts_confirmed"))
    early.append({
        "step": "分镜",
        "status": "confirmed" if storyboard_ready else ("current" if _bool(data.get("script_confirmed")) else "pending"),
        "current_result": "分镜、角色设定和关键帧提示词已齐。" if storyboard_ready else "分镜链路仍在准备中。",
        "current_blocker": "" if storyboard_ready else "Stage 02-04 任一步未确认，关键帧阶段就不应被当成完全就绪。",
        "next_action": "补齐分镜、角色设定和关键帧提示词确认。" if not storyboard_ready else "进入关键帧阶段。",
        "risk_hint": "",
    })
    stage05 = stage_truth.get("stage05")
    keyframe_step = {
        "step": "关键帧",
        "status": stage05.get("normalized_status") if stage05 else ("confirmed" if _bool(data.get("keyframe_images_confirmed")) else "pending"),
        "current_result": stage05.get("current_result") if stage05 else "尚未进入 Stage 05。",
        "current_blocker": stage05.get("current_blocker") if stage05 else "",
        "next_action": stage05.get("next_action") if stage05 else "开始关键帧生成。",
        "risk_hint": stage05.get("risk_hint") if stage05 else "",
    }
    if stage05 is None and reference_state and not reference_state.get("safe_to_auto_generate"):
        keyframe_step = {
            "step": "关键帧",
            "status": "current" if storyboard_ready else "pending",
            "current_result": reference_state.get("current_result") or "角色参考图仍未补齐。",
            "current_blocker": reference_state.get("current_blocker") or "",
            "next_action": reference_state.get("next_action") or "先补角色参考图。",
            "risk_hint": reference_state.get("risk_hint") or "",
        }
    early.append(keyframe_step)
    stage08 = stage_truth.get("stage08")
    final_stage = stage08 or stage_truth.get("stage07") or stage_truth.get("stage06") or {}
    early.append({
        "step": "成片",
        "status": final_stage.get("normalized_status") if final_stage else "pending",
        "current_result": final_stage.get("current_result") if final_stage else "尚未进入后半段成片链路。",
        "current_blocker": final_stage.get("current_blocker") if final_stage else "",
        "next_action": final_stage.get("next_action") if final_stage else "先生成视频片段和音频。",
        "risk_hint": final_stage.get("risk_hint") if final_stage else "",
    })
    return early


def _derive_project_stage(data: dict[str, Any], stage_truth: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    if not stage_truth:
        current_stage = _text(data.get("current_stage")) or "STAGE_00_INTAKE"
        return current_stage, data.get("allowed_next_stage")
    if _bool(data.get("qa_confirmed")) and (_bool(data.get("assembly_confirmed")) or _bool(stage_truth.get("stage08", {}).get("confirmed"))):
        return "STAGE_09_QA_CONFIRMED", "PROJECT_DELIVERED" if _bool(data.get("delivery_complete")) else "PROJECT_DELIVERED"
    stage05 = stage_truth.get("stage05")
    stage06 = stage_truth.get("stage06")
    stage07 = stage_truth.get("stage07")
    stage08 = stage_truth.get("stage08")
    if stage05 and not stage05.get("confirmed"):
        return "STAGE_05_KEYFRAME_IMAGES", None
    if stage05 and stage05.get("confirmed") and stage06 is None:
        return "STAGE_05_KEYFRAME_IMAGES_CONFIRMED", "STAGE_06_VIDEO_CLIPS"
    if stage06 and not stage06.get("confirmed"):
        return "STAGE_06_VIDEO_CLIPS", None
    if stage06 and stage06.get("confirmed") and stage07 is None:
        return "STAGE_06_VIDEO_CLIPS_CONFIRMED", "STAGE_07_AUDIO"
    if stage07 and not stage07.get("confirmed"):
        return "STAGE_07_AUDIO", None
    if stage07 and stage07.get("confirmed") and stage08 is None:
        return "STAGE_07_AUDIO_CONFIRMED", "STAGE_08_ASSEMBLY"
    if stage08 and not stage08.get("confirmed"):
        fallback_reasons = _list_of_str(stage08.get("blocking_reasons"))
        for reason in fallback_reasons:
            if "Stage 07" in reason or "audio" in reason.lower():
                return "STAGE_07_AUDIO", None
            if "Stage 06" in reason or "clip" in reason.lower():
                return "STAGE_06_VIDEO_CLIPS", None
        return "STAGE_08_ASSEMBLY", None
    if stage08 and stage08.get("confirmed"):
        return "STAGE_08_ASSEMBLY_CONFIRMED", "STAGE_09_QA"
    for flag_key, stage_name, next_stage in reversed(EARLY_STAGE_SEQUENCE):
        if _bool(data.get(flag_key)):
            return stage_name, next_stage
    if _bool(data.get("brief_locked")):
        return "STAGE_00_BRIEF_LOCKED", "STAGE_01_SCRIPT_GENERATION"
    return "STAGE_00_INTAKE", None


def _project_blockers(stage_truth: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for key in ["stage05", "stage06", "stage07", "stage08"]:
        truth = stage_truth.get(key)
        if not truth:
            continue
        for reason in _list_of_str(truth.get("blocking_reasons")):
            if reason not in blockers:
                blockers.append(reason)
    return blockers


def _project_provider_summary(stage_truth: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    stage05 = stage_truth.get("stage05")
    if stage05:
        provider = _as_dict(stage05.get("provider_summary"))
        primary = _text(provider.get("primary"))
        if primary:
            lines.append(f"Stage 05 当前主 provider：{primary}")
        headline = _text(provider.get("headline"))
        detail = _text(provider.get("detail"))
        if headline:
            lines.append(headline if not detail else f"{headline} {detail}")
    stage06 = stage_truth.get("stage06")
    if stage06:
        primary = _text(_as_dict(stage06.get("provider_summary")).get("primary"))
        if primary:
            lines.append(f"Stage 06 当前主 provider：{primary}")
    stage07 = stage_truth.get("stage07")
    if stage07:
        provider = _as_dict(stage07.get("provider_summary"))
        music_primary = _text(provider.get("music_primary"))
        if music_primary:
            lines.append(f"Stage 07 音乐 provider：{music_primary}")
    stage08 = stage_truth.get("stage08")
    if stage08:
        assembly_provider = _text(_as_dict(stage08.get("provider_summary")).get("assembly_provider"))
        if assembly_provider:
            lines.append(f"Stage 08 装配执行器：{assembly_provider}")
    return lines


def _recommended_entry(
    project_dir: Path,
    *,
    stage_truth: dict[str, dict[str, Any]],
    reference_state: dict[str, Any] | None,
    current_step: dict[str, Any],
) -> dict[str, Any]:
    current_step_name = _text(current_step.get("step"))
    current_step_command = _text(current_step.get("command"))
    if current_step_name == "剧本" and current_step_command:
        return {
            "label": "运行 Stage 01 自动剧本生成",
            "command": current_step_command,
            "kind": "command",
            "description": "Stage 00 锁 brief 后，$video-production-pipeline 的下一步就是自动进入 Stage 01 并调用官方 Stage 01 执行脚本。",
        }
    stage05 = stage_truth.get("stage05")
    workbench_path = project_dir / "05_images" / "stage05_review_workbench.html"
    if stage05 is not None:
        return {
            "label": "打开 Stage 05 审图工作台",
            "path": as_posix(workbench_path),
            "kind": "file",
            "description": "默认从这里看图、审图、通过或重跑，不必先读 manifest 和脚本名。",
        }
    if reference_state and not reference_state.get("safe_to_auto_generate"):
        actions = reference_state.get("actions") if isinstance(reference_state.get("actions"), list) else []
        if actions:
            return actions[0]
    return {
        "label": "打开创作者主页",
        "path": as_posix(project_dir / "creator_home.html"),
        "kind": "file",
        "description": _text(current_step.get("next_action")) or "从这里继续当前项目。",
    }


def build_creator_status_overview(project_dir: Path, data: dict[str, Any], stage_truth: dict[str, dict[str, Any]]) -> dict[str, Any]:
    trusted_stage, allowed_next = _derive_project_stage(data, stage_truth)
    blockers = _project_blockers(stage_truth)
    reference_state = _derive_reference_readiness_state(project_dir)
    steps = _creator_steps(data, stage_truth, reference_state)
    provider_lines = _project_provider_summary(stage_truth)
    current_step = next((step for step in steps if step.get("status") in {"current", "generated", "review_required", "blocked", "in_progress"}), steps[-1] if steps else {})
    human_gate_message = (
        f"{_text(current_step.get('current_blocker'))} 下一步：{_text(current_step.get('next_action'))}"
        if _text(current_step.get("current_blocker"))
        else _text(current_step.get("next_action"))
    )
    return {
        "project_display_name": _text(data.get("project_title")) or project_dir.name,
        "trusted_stage": trusted_stage,
        "allowed_next_stage": allowed_next,
        "blocking_reasons": blockers,
        "provider_summary": provider_lines,
        "current_result": _text(current_step.get("current_result")),
        "current_blocker": _text(current_step.get("current_blocker")) or (blockers[0] if blockers else ""),
        "next_action": _text(current_step.get("next_action")),
        "risk_hint": _text(current_step.get("risk_hint")),
        "human_gate_message": human_gate_message,
        "recommended_entry": _recommended_entry(
            project_dir,
            stage_truth=stage_truth,
            reference_state=reference_state,
            current_step=current_step,
        ),
        "reference_guidance": reference_state or {},
        "steps": steps,
    }


def _creator_overview_markdown(project_dir: Path, overview: dict[str, Any]) -> str:
    lines = [
        "# 创作者主页",
        "",
        f"- 项目：`{_text(overview.get('project_display_name')) or project_dir.name}`",
        f"- 当前可信阶段：`{_text(overview.get('trusted_stage'))}`",
        f"- 当前结果：{_text(overview.get('current_result')) or '暂无结果'}",
        f"- 当前卡点：{_text(overview.get('current_blocker')) or '暂无阻断'}",
        f"- 下一步动作：{_text(overview.get('next_action')) or '继续当前阶段'}",
        f"- 安全下一步：`{_text(overview.get('allowed_next_stage')) or 'none'}`",
        "",
        "## 推荐入口",
        "",
    ]
    recommended = _as_dict(overview.get("recommended_entry"))
    if recommended:
        if _text(recommended.get("path")):
            lines.append(f"- {recommended.get('label')}：`{_text(recommended.get('path'))}`")
        if _text(recommended.get("command")):
            lines.append(f"- {recommended.get('label')}命令：`{_text(recommended.get('command'))}`")
        if _text(recommended.get("description")):
            lines.append(f"- 说明：{_text(recommended.get('description'))}")
    lines.extend([
        "",
        "## Provider / Fallback",
        "",
    ])
    provider_lines = _list_of_str(overview.get("provider_summary"))
    if provider_lines:
        lines.extend([f"- {item}" for item in provider_lines])
    else:
        lines.append("- 当前没有可总结的 provider 轨迹。")
    lines.extend(["", "## 五步视图", ""])
    for step in _as_list(overview.get("steps")):
        if not isinstance(step, dict):
            continue
        lines.append(f"- {step.get('step')}：{_text(step.get('status')) or 'pending'}")
        lines.append(f"  当前结果：{_text(step.get('current_result')) or '暂无'}")
        lines.append(f"  当前卡点：{_text(step.get('current_blocker')) or '无'}")
        lines.append(f"  下一步：{_text(step.get('next_action')) or '继续当前步骤'}")
        risk_hint = _text(step.get("risk_hint"))
        if risk_hint:
            lines.append(f"  风险提示：{risk_hint}")
    return "\n".join(lines).rstrip() + "\n"


def _creator_overview_html(project_dir: Path, overview: dict[str, Any]) -> str:
    recommended = _as_dict(overview.get("recommended_entry"))
    provider_lines = _list_of_str(overview.get("provider_summary"))
    steps = [step for step in _as_list(overview.get("steps")) if isinstance(step, dict)]

    def render_entry(entry: dict[str, Any]) -> str:
        if not entry:
            return ""
        path_text = _text(entry.get("path"))
        command_text = _text(entry.get("command"))
        link = _path_uri(path_text) if path_text else ""
        path_block = (
            f'<a class="cta" href="{html.escape(link)}">{html.escape(_text(entry.get("label")) or "打开入口")}</a>'
            if link else ""
        )
        command_block = f"<pre>{html.escape(command_text)}</pre>" if command_text else ""
        description = html.escape(_text(entry.get("description")) or "")
        path_hint = f"<div class=\"hint\">{html.escape(path_text)}</div>" if path_text else ""
        return f"""
        <section class="hero-card">
          <div class="eyebrow">推荐入口</div>
          <h2>{html.escape(_text(entry.get("label")) or "继续当前项目")}</h2>
          <p>{description}</p>
          {path_block}
          {path_hint}
          {command_block}
        </section>
        """

    step_cards: list[str] = []
    for step in steps:
        status = html.escape(_text(step.get("status")) or "pending")
        step_cards.append(f"""
        <article class="step-card">
          <div class="step-top">
            <strong>{html.escape(_text(step.get("step")) or "步骤")}</strong>
            <span class="status">{status}</span>
          </div>
          <p><strong>当前结果：</strong>{html.escape(_text(step.get("current_result")) or "暂无")}</p>
          <p><strong>当前卡点：</strong>{html.escape(_text(step.get("current_blocker")) or "无")}</p>
          <p><strong>下一步：</strong>{html.escape(_text(step.get("next_action")) or "继续当前步骤")}</p>
          <p class="muted">{html.escape(_text(step.get("risk_hint")) or "")}</p>
        </article>
        """)

    provider_html = "".join(f"<li>{html.escape(item)}</li>" for item in provider_lines) or "<li>当前没有可总结的 provider 轨迹。</li>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(_text(overview.get("project_display_name")) or project_dir.name)} · 创作者主页</title>
  <style>
    :root {{
      --paper: #f6efe1;
      --ink: #1e1c17;
      --accent: #9d5033;
      --accent-soft: #f0d5c7;
      --panel: rgba(255,255,255,0.78);
      --line: rgba(37,28,20,0.12);
      --muted: #675c4f;
    }}
    body {{
      margin: 0;
      font-family: "Microsoft YaHei UI", "Noto Serif SC", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(157,80,51,0.22), transparent 30%),
        linear-gradient(160deg, #f7f1e7 0%, var(--paper) 55%, #efe2d0 100%);
    }}
    .shell {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .headline {{
      display: grid;
      gap: 16px;
      margin-bottom: 24px;
    }}
    .headline h1 {{
      margin: 0;
      font-size: 36px;
      line-height: 1.1;
    }}
    .headline p {{
      margin: 0;
      color: var(--muted);
      font-size: 16px;
    }}
    .hero-card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 20px;
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 45px rgba(63, 39, 18, 0.08);
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 16px;
      margin-bottom: 18px;
    }}
    .eyebrow {{
      color: var(--accent);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .cta {{
      display: inline-block;
      margin-top: 10px;
      padding: 11px 16px;
      border-radius: 999px;
      background: var(--accent);
      color: #fff7f1;
      text-decoration: none;
      font-weight: 700;
    }}
    .hint {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
      word-break: break-all;
    }}
    pre {{
      margin: 12px 0 0;
      padding: 12px;
      border-radius: 14px;
      background: #fff7f1;
      border: 1px dashed rgba(157,80,51,0.28);
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .meta-list, .provider-list {{
      margin: 0;
      padding-left: 18px;
    }}
    .meta-list li, .provider-list li {{
      margin: 8px 0;
    }}
    .steps {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 18px;
    }}
    .step-card {{
      background: rgba(255,255,255,0.68);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
    }}
    .step-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .status {{
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
    }}
    .muted {{
      color: var(--muted);
    }}
    @media (max-width: 900px) {{
      .hero-grid, .steps {{
        grid-template-columns: 1fr;
      }}
      .headline h1 {{
        font-size: 30px;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="headline">
      <div class="eyebrow">Creator Home</div>
      <h1>{html.escape(_text(overview.get("project_display_name")) or project_dir.name)}</h1>
      <p>{html.escape(_text(overview.get("human_gate_message")) or "系统已整理当前项目状态。")}</p>
    </section>
    <section class="hero-grid">
      <div class="panel">
        <div class="eyebrow">当前项目</div>
        <ul class="meta-list">
          <li><strong>当前可信阶段：</strong>{html.escape(_text(overview.get("trusted_stage")) or "未知")}</li>
          <li><strong>当前结果：</strong>{html.escape(_text(overview.get("current_result")) or "暂无结果")}</li>
          <li><strong>当前卡点：</strong>{html.escape(_text(overview.get("current_blocker")) or "暂无阻断")}</li>
          <li><strong>下一步动作：</strong>{html.escape(_text(overview.get("next_action")) or "继续当前阶段")}</li>
        </ul>
      </div>
      {render_entry(recommended)}
    </section>
    <section class="panel">
      <div class="eyebrow">Provider / Fallback</div>
      <ul class="provider-list">{provider_html}</ul>
    </section>
    <section class="steps">
      {''.join(step_cards)}
    </section>
  </div>
</body>
</html>
"""


def sync_project_manifest_truth(manifest_path: Path) -> Path | None:
    if not manifest_path.exists() or not manifest_path.is_file():
        return None
    try:
        data = load_json_file(manifest_path)
    except Exception:
        return None
    project_dir = manifest_path.parent
    data.setdefault("project_id", project_dir.name)
    data.setdefault("project_dir", as_posix(project_dir))
    stage_truth: dict[str, dict[str, Any]] = {}
    for key, builder in [
        ("stage05", _derive_stage05_state),
        ("stage06", _derive_stage06_state),
        ("stage07", _derive_stage07_state),
        ("stage08", _derive_stage08_state),
    ]:
        state = builder(project_dir)
        if state is not None:
            stage_truth[key] = state
    overview = build_creator_status_overview(project_dir, data, stage_truth)
    trusted_stage, allowed_next = _derive_project_stage(data, stage_truth)
    data["current_stage"] = trusted_stage
    data["allowed_next_stage"] = allowed_next
    data["updated_at"] = utc_now()
    data["keyframe_images_confirmed"] = bool(stage_truth.get("stage05", {}).get("confirmed", data.get("keyframe_images_confirmed")))
    data["video_clips_confirmed"] = bool(stage_truth.get("stage06", {}).get("confirmed", data.get("video_clips_confirmed"))) and data["keyframe_images_confirmed"]
    data["audio_confirmed"] = bool(stage_truth.get("stage07", {}).get("confirmed", data.get("audio_confirmed"))) and data["video_clips_confirmed"]
    data["assembly_confirmed"] = bool(stage_truth.get("stage08", {}).get("confirmed", data.get("assembly_confirmed"))) and data["audio_confirmed"]
    if not data["keyframe_images_confirmed"]:
        data["video_clips_confirmed"] = False
        data["audio_confirmed"] = False
        data["assembly_confirmed"] = False
    elif not data["video_clips_confirmed"]:
        data["audio_confirmed"] = False
        data["assembly_confirmed"] = False
    elif not data["audio_confirmed"]:
        data["assembly_confirmed"] = False
    data["state_truth"] = {
        "blocking_reasons": overview["blocking_reasons"],
        "stage_states": {
            key: {
                "normalized_status": value.get("normalized_status"),
                "confirmed": value.get("confirmed"),
                "evidence_origin_summary": value.get("evidence_origin_summary"),
                "current_result": value.get("current_result"),
                "current_blocker": value.get("current_blocker"),
                "next_action": value.get("next_action"),
            }
            for key, value in stage_truth.items()
        },
    }
    data["creator_status_overview"] = overview
    if overview["blocking_reasons"]:
        data["status"] = "blocked"
    elif trusted_stage.endswith("_CONFIRMED"):
        data["status"] = "active"
    else:
        data["status"] = _text(data.get("status")) or "active"
    write_json_file(manifest_path, data)
    overview_json = project_dir / "creator_status_overview.json"
    write_json_file(overview_json, overview)
    overview_markdown = _creator_overview_markdown(project_dir, overview)
    overview_html = _creator_overview_html(project_dir, overview)
    (project_dir / "creator_status_overview.md").write_text(overview_markdown, encoding="utf-8")
    (project_dir / "creator_status_overview.html").write_text(overview_html, encoding="utf-8")
    write_json_file(project_dir / "creator_home.json", overview)
    (project_dir / "creator_home.md").write_text(overview_markdown, encoding="utf-8")
    (project_dir / "creator_home.html").write_text(overview_html, encoding="utf-8")
    return manifest_path


def find_project_manifest(start: Path) -> Path | None:
    anchor = start if start.is_dir() else start.parent
    for directory in [anchor, *anchor.parents]:
        candidate = directory / "project_manifest.json"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def update_project_manifest_for_stage(
    source_path: Path,
    *,
    current_stage: str,
    allowed_next_stage: str | None,
    flags: dict[str, bool] | None = None,
    status: str | None = None,
) -> Path | None:
    manifest_path = find_project_manifest(source_path)
    if manifest_path is None:
        return None

    try:
        data = load_json_file(manifest_path)
    except Exception:
        return None

    project_dir = manifest_path.parent
    data.setdefault("project_id", project_dir.name)
    data.setdefault("project_dir", as_posix(project_dir))
    data["current_stage"] = current_stage
    data["allowed_next_stage"] = allowed_next_stage
    data["updated_at"] = utc_now()
    if status is not None:
        data["status"] = status
    for key, value in (flags or {}).items():
        data[key] = bool(value)

    write_json_file(manifest_path, data)
    return sync_project_manifest_truth(manifest_path)
