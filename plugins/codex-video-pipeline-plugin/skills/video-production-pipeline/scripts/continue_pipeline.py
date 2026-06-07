#!/usr/bin/env python3
"""Continue the official video-production pipeline from project manifest state.

This script dispatches the real Stage 01-05 Codex-first pipeline runners based
on manifest truth, and re-surfaces the formal Stage 01/02 review gates when
generation has already completed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "skills" / "video-script-generation" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "video-storyboard-generation" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "video-keyframe-images" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "video-video-clips" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "video-audio" / "scripts"))

from pipeline_core.project_state import load_json_file, sync_project_manifest_truth  # noqa: E402
import run_stage00_controller  # noqa: E402
import run_stage01_from_locked_brief  # noqa: E402
import run_stage02_from_confirmed_script  # noqa: E402
import run_stage03_from_confirmed_storyboard  # noqa: E402
import run_stage04_from_confirmed_character_bible  # noqa: E402
import run_stage05_from_confirmed_keyframe_prompts  # noqa: E402
import run_stage06_from_confirmed_keyframe_images  # noqa: E402
import run_stage07_from_confirmed_video_clips  # noqa: E402
import sync_keyframe_image_manifest  # noqa: E402
import sync_video_clip_manifest  # noqa: E402
import validate_script  # noqa: E402
import validate_storyboard  # noqa: E402
import validate_video_clip_manifest  # noqa: E402
import validate_audio_manifest  # noqa: E402


def _latest_project(root: Path) -> Path | None:
    if not root.exists() or not root.is_dir():
        return None
    candidates: list[tuple[str, float, Path]] = []
    for item in root.iterdir():
        manifest = item / "project_manifest.json"
        if not item.is_dir() or not manifest.exists():
            continue
        try:
            data = load_json_file(manifest)
            stamp = str(data.get("updated_at") or data.get("created_at") or "")
        except Exception:
            stamp = ""
        candidates.append((stamp, item.stat().st_mtime, item))
    if not candidates:
        return None
    candidates.sort(key=lambda record: (record[0], record[1]), reverse=True)
    return candidates[0][2]


def _resolve_manifest(args: argparse.Namespace) -> Path | None:
    if args.manifest:
        return Path(args.manifest).resolve()
    if args.project_dir:
        return (Path(args.project_dir).resolve() / "project_manifest.json").resolve()
    latest = _latest_project(Path(args.root))
    if latest is None:
        return None
    return (latest / "project_manifest.json").resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="video_projects", help="Project root used when no project is explicitly provided")
    parser.add_argument("--project-dir", default=None, help="Specific project directory to continue")
    parser.add_argument("--manifest", default=None, help="Explicit project_manifest.json path")
    parser.add_argument("--stage00-state", default=str(run_stage00_controller.default_state_path()), help="Workspace Stage 00 intake state path used before a project folder exists")
    return parser.parse_args(argv)


def _load_stage00_state_if_active(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = load_json_file(path)
    except Exception:
        return None
    status = str(data.get("status") or "").strip()
    if status in {"collecting", "draft_ready"}:
        return data
    return None


def _yes_no(value: object) -> str:
    return "是" if bool(value) else "否"


def _stage01_review_gate(project_dir: Path, script_path: Path) -> int:
    script_dir = script_path.parent
    try:
        script_data = load_json_file(script_path)
    except Exception as exc:
        print(f"ERROR: unable to load Stage 01 script: {exc}")
        return 1
    ok, errors, _warnings = validate_script.validate(script_data, mode="final")
    if not ok:
        return _stage01_block_surface(project_dir, script_path, errors)
    duration_plan = script_data.get("duration_plan") if isinstance(script_data.get("duration_plan"), dict) else {}
    self_check = script_data.get("self_check") if isinstance(script_data.get("self_check"), dict) else {}
    print("PIPELINE_REVIEW_STAGE: STAGE_01_SCRIPT_REVIEW")
    print(f"PIPELINE_REVIEW_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_REVIEW_CONFIRM_COMMAND: python skills/video-production-pipeline/scripts/confirm_stage01_and_continue.py {str(project_dir).replace(chr(92), '/')}")
    print("Stage 01 剧本包已生成：")
    for name in [
        "story_direction.md",
        "story_direction.json",
        "plot_structure.md",
        "plot_structure.json",
        "script.md",
        "script.json",
        "script_review.md",
    ]:
        print(f"- {str((script_dir / name).resolve()).replace(chr(92), '/')}")
    print("")
    print("当前摘要：")
    print(f"- 标题：{str(script_data.get('title') or '').strip() or '未提供'}")
    print(f"- Logline：{str(script_data.get('logline') or '').strip() or '未提供'}")
    print(f"- 目标时长：{duration_plan.get('target_duration_sec') or ''} 秒")
    print(f"- 严格遵守 locked brief：{_yes_no(self_check.get('matches_locked_brief'))}")
    print(f"- 可进入 Stage 02：{_yes_no(self_check.get('ready_for_storyboard'))}")
    print("")
    print("请确认：")
    print("A. 剧本可以，自动进入 Stage 02 分镜拆解")
    print("B. 修改故事走向")
    print("C. 修改人物设定")
    print("D. 修改旁白/对白")
    print("E. 修改视频节奏")
    print("F. 重新生成剧本")
    return 0


def _stage01_block_surface(project_dir: Path, script_path: Path, errors: list[str]) -> int:
    script_dir = script_path.parent
    print("PIPELINE_BLOCKED_STAGE: STAGE_01_SCRIPT_GENERATION")
    print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_BLOCKED_SCRIPT_PATH: {str(script_path.resolve()).replace(chr(92), '/')}")
    print("Stage 01 剧本正式校验未通过，当前不能进入 review gate。")
    print("阻断原因：")
    for error in errors:
        print(f"- {error}")
    validation_errors_path = script_dir / "stage01_validation_errors.json"
    repair_packet_path = script_dir / "stage01_repair_packet.json"
    if validation_errors_path.exists():
        print(f"PIPELINE_BLOCKED_VALIDATION_ERRORS: {str(validation_errors_path.resolve()).replace(chr(92), '/')}")
    if repair_packet_path.exists():
        print(f"PIPELINE_BLOCKED_REPAIR_PACKET: {str(repair_packet_path.resolve()).replace(chr(92), '/')}")
    return 1


def _stage02_review_gate(project_dir: Path, storyboard_path: Path) -> int:
    storyboard_dir = storyboard_path.parent
    try:
        storyboard_data = load_json_file(storyboard_path)
    except Exception as exc:
        print(f"ERROR: unable to load Stage 02 storyboard: {exc}")
        return 1
    ok, errors, _warnings = validate_storyboard.validate(storyboard_data, mode="final")
    if not ok:
        return _stage02_block_surface(project_dir, storyboard_path, errors)
    self_check = storyboard_data.get("self_check") if isinstance(storyboard_data.get("self_check"), dict) else {}
    print("PIPELINE_REVIEW_STAGE: STAGE_02_STORYBOARD_REVIEW")
    print(f"PIPELINE_REVIEW_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_REVIEW_CONFIRM_COMMAND: python skills/video-production-pipeline/scripts/confirm_stage02_and_continue.py {str(project_dir).replace(chr(92), '/')}")
    print("Stage 02 分镜脚本已生成：")
    for name in [
        "storyboard.md",
        "storyboard.json",
        "storyboard_review.md",
    ]:
        print(f"- {str((storyboard_dir / name).resolve()).replace(chr(92), '/')}")
    print("")
    print("当前摘要：")
    print(f"- 镜头数：{storyboard_data.get('shot_count') or 0}")
    print(f"- 目标时长：{storyboard_data.get('target_duration_sec') or ''} 秒")
    print(f"- 匹配 locked brief：{_yes_no(self_check.get('matches_locked_brief'))}")
    print(f"- 匹配已确认剧本：{_yes_no(self_check.get('matches_script'))}")
    print(f"- 可进入 Stage 03：{_yes_no(self_check.get('ready_for_character_stage'))}")
    print("")
    print("请确认：")
    print("A. 分镜可以，自动进入 Stage 03 人物画像")
    print("B. 修改镜头节奏")
    print("C. 修改镜头数量")
    print("D. 修改某个镜头")
    print("E. 重新生成分镜")
    return 0


def _stage02_block_surface(project_dir: Path, storyboard_path: Path, errors: list[str]) -> int:
    storyboard_dir = storyboard_path.parent
    print("PIPELINE_BLOCKED_STAGE: STAGE_02_STORYBOARD_GENERATION")
    print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_BLOCKED_STORYBOARD_PATH: {str(storyboard_path.resolve()).replace(chr(92), '/')}")
    print("Stage 02 分镜正式校验未通过，当前不能进入 review gate。")
    print("阻断原因：")
    for error in errors:
        print(f"- {error}")
    validation_errors_path = storyboard_dir / "stage02_validation_errors.json"
    repair_packet_path = storyboard_dir / "stage02_repair_packet.json"
    if validation_errors_path.exists():
        print(f"PIPELINE_BLOCKED_VALIDATION_ERRORS: {str(validation_errors_path.resolve()).replace(chr(92), '/')}")
    if repair_packet_path.exists():
        print(f"PIPELINE_BLOCKED_REPAIR_PACKET: {str(repair_packet_path.resolve()).replace(chr(92), '/')}")
    return 1


def _stage03_review_gate(project_dir: Path, character_path: Path) -> int:
    character_dir = character_path.parent
    try:
        character_data = load_json_file(character_path)
    except Exception as exc:
        print(f"ERROR: unable to load Stage 03 character bible: {exc}")
        return 1
    self_check = character_data.get("self_check") if isinstance(character_data.get("self_check"), dict) else {}
    reference_status = character_data.get("reference_image_status") if isinstance(character_data.get("reference_image_status"), dict) else {}
    reference_ready = bool(reference_status.get("all_present"))
    reference_entry = character_dir / "reference_image_start_here.md"
    print("PIPELINE_REVIEW_STAGE: STAGE_03_CHARACTER_BIBLE_REVIEW")
    print(f"PIPELINE_REVIEW_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_REVIEW_CONFIRM_COMMAND: python skills/video-production-pipeline/scripts/confirm_stage03_and_continue.py {str(project_dir).replace(chr(92), '/')}")
    print("Stage 03 人物画像包已生成：")
    for name in [
        "character_bible.md",
        "character_bible.json",
        "character_review.md",
        "reference_image_plan.json",
    ]:
        print(f"- {str((character_dir / name).resolve()).replace(chr(92), '/')}")
    if reference_entry.exists() and not reference_ready:
        print("")
        print("先看：")
        print(str(reference_entry.resolve()).replace(chr(92), '/'))
    print("")
    print("当前摘要：")
    print(f"- 角色数：{len(character_data.get('characters') or [])}")
    print(f"- 匹配 brief/script/storyboard：{_yes_no(self_check.get('matches_locked_brief') and self_check.get('matches_script') and self_check.get('matches_storyboard'))}")
    print(f"- 可进入 Stage 04：{_yes_no(self_check.get('ready_for_keyframe_stage'))}")
    print(f"- 参考图已齐：{_yes_no(reference_ready)}")
    print("")
    print("请确认：")
    print("A. 人物设定可以，后续进入 Stage 04 关键帧提示词")
    print("B. 修改人物外貌")
    print("C. 修改人物服装")
    print("D. 修改人物年龄/气质")
    print("E. 修改人物声音设定")
    print("F. 重新生成人物画像")
    return 0


def _stage04_review_gate(project_dir: Path, keyframe_path: Path) -> int:
    keyframe_dir = keyframe_path.parent
    try:
        keyframe_data = load_json_file(keyframe_path)
    except Exception as exc:
        print(f"ERROR: unable to load Stage 04 keyframe prompts: {exc}")
        return 1
    self_check = keyframe_data.get("self_check") if isinstance(keyframe_data.get("self_check"), dict) else {}
    reference_status = keyframe_data.get("reference_image_status") if isinstance(keyframe_data.get("reference_image_status"), dict) else {}
    stage05_handoff = keyframe_data.get("stage05_handoff") if isinstance(keyframe_data.get("stage05_handoff"), dict) else {}
    readiness = keyframe_data.get("stage05_execution_readiness") if isinstance(keyframe_data.get("stage05_execution_readiness"), dict) else {}
    reference_ready = bool(reference_status.get("all_present"))
    must_open_reference_entry = bool(stage05_handoff.get("must_open_reference_entry"))
    stage05_entry = keyframe_dir / "stage05_start_here.md"
    print("PIPELINE_REVIEW_STAGE: STAGE_04_KEYFRAME_PROMPTS_REVIEW")
    print(f"PIPELINE_REVIEW_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_REVIEW_CONFIRM_COMMAND: python skills/video-production-pipeline/scripts/confirm_stage04_and_continue.py {str(project_dir).replace(chr(92), '/')}")
    print("Stage 04 关键帧提示词包已生成：")
    for name in [
        "keyframe_prompts.md",
        "keyframe_prompts.json",
        "motion_prompts.json",
        "prompt_review.md",
        "stage05_start_here.md",
    ]:
        print(f"- {str((keyframe_dir / name).resolve()).replace(chr(92), '/')}")
    if stage05_entry.exists() and (must_open_reference_entry or not reference_ready):
        print("")
        print("先看：")
        print(str(stage05_entry.resolve()).replace(chr(92), '/'))
    print("")
    print("当前摘要：")
    print(f"- 镜头提示词数量：{len(keyframe_data.get('shot_prompts') or [])}")
    print(f"- 过渡提示词数量：{len(keyframe_data.get('transition_prompts') or [])}")
    print(f"- 覆盖全部 storyboard 镜头：{_yes_no(self_check.get('covers_all_storyboard_shots'))}")
    print(f"- 保留角色一致性：{_yes_no(self_check.get('uses_character_consistency'))}")
    print(f"- 角色参考图已齐：{_yes_no(reference_ready)}")
    print(f"- 是否可安全自动进入 Stage 05：{_yes_no(stage05_handoff.get('ready_for_stage05') if 'ready_for_stage05' in stage05_handoff else readiness.get('safe_to_auto_generate'))}")
    print(f"- 当前判断：{str(stage05_handoff.get('summary') or '').strip() or '未提供'}")
    print(f"- 下一步：{str(stage05_handoff.get('next_action') or '').strip() or '待用户确认后进入 Stage 05。'}")
    print("")
    print("请确认：")
    print("A. 提示词可以，后续进入 Stage 05 关键帧图片生成")
    print("B. 修改某个镜头的关键帧提示词")
    print("C. 修改过渡动作提示词")
    print("D. 修改角色一致性提示词")
    print("E. 修改负面提示词")
    print("F. 重新生成 Stage 04 提示词包")
    return 0


def _load_stage05_manifest(stage05_manifest_path: Path) -> dict:
    try:
        return load_json_file(stage05_manifest_path)
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {stage05_manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {stage05_manifest_path}: {exc}") from exc


def _stage05_manifest_uses_codex_contract(stage05_data: dict) -> bool:
    summary = stage05_data.get("stage05_semantic_contract_summary")
    if isinstance(summary, dict) and str(summary.get("mode") or "").strip() == "codex_contract":
        return True
    jobs = stage05_data.get("jobs") if isinstance(stage05_data.get("jobs"), list) else []
    if not jobs:
        return False
    return all(
        isinstance(job, dict)
        and str(job.get("semantic_source") or "").strip() == "codex_contract"
        and str(job.get("prompt_composition_mode") or "").strip() == "codex_contract"
        for job in jobs
    )


def _stage04_prompts_use_stage05_codex_contract(project_dir: Path) -> bool:
    keyframe_json = project_dir / "04_keyframes" / "keyframe_prompts.json"
    if not keyframe_json.exists():
        return False
    try:
        keyframe_data = load_json_file(keyframe_json)
    except Exception:
        return False
    if isinstance(keyframe_data.get("stage05_semantic_contract"), dict):
        return True
    summary = keyframe_data.get("stage05_semantic_contract_summary")
    return isinstance(summary, dict) and str(summary.get("mode") or "").strip() == "codex_contract"


def _stage05_active_job_count(stage05_data: dict) -> int:
    jobs = stage05_data.get("jobs") if isinstance(stage05_data.get("jobs"), list) else []
    active_states = {"queued", "running", "submitting", "in_progress"}
    return sum(
        1
        for job in jobs
        if isinstance(job, dict) and str(job.get("status") or "").strip().lower() in active_states
    )


def _stage05_progress_surface(project_dir: Path, stage05_manifest_path: Path, stage05_data: dict) -> int:
    images_dir = stage05_manifest_path.parent
    summary = stage05_data.get("summary") if isinstance(stage05_data.get("summary"), dict) else {}
    self_check = stage05_data.get("self_check") if isinstance(stage05_data.get("self_check"), dict) else {}
    quality_review = stage05_data.get("quality_review") if isinstance(stage05_data.get("quality_review"), dict) else {}
    creator_runtime_status = stage05_data.get("creator_runtime_status") if isinstance(stage05_data.get("creator_runtime_status"), dict) else {}
    workbench_path = images_dir / "stage05_review_workbench.html"
    stage05_start_here = project_dir / "04_keyframes" / "stage05_start_here.md"
    active_jobs = _stage05_active_job_count(stage05_data)
    print("PIPELINE_PROGRESS_STAGE: STAGE_05_KEYFRAME_IMAGES_GENERATION")
    print(f"PIPELINE_PROGRESS_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_PROGRESS_STAGE05_MANIFEST: {str(stage05_manifest_path.resolve()).replace(chr(92), '/')}")
    print("Stage 05 关键帧仍在生成中，当前还不能收束成正式确认门。")
    print("当前摘要：")
    print(f"- 预期图片数：{summary.get('expected_image_count') or 0}")
    print(f"- 已落盘图片数：{summary.get('generated_image_count') or 0}")
    print(f"- 仍在执行的任务数：{active_jobs}")
    print(f"- 待人工复核数：{quality_review.get('pending_count') or 0}")
    print(f"- 是否可进入 Stage 06：{_yes_no(self_check.get('ready_for_video_clip_generation'))}")
    headline = str((creator_runtime_status.get("headline") or "")).strip()
    detail = str((creator_runtime_status.get("detail") or "")).strip()
    if headline:
        print(f"- 当前状态：{headline}")
    if detail:
        print(f"- 详情：{detail}")
    print("下一步：")
    if workbench_path.exists():
        print(str(workbench_path.resolve()).replace(chr(92), '/'))
    elif stage05_start_here.exists():
        print(str(stage05_start_here.resolve()).replace(chr(92), '/'))
    else:
        print("等待当前 Stage 05 生成任务继续落盘后，再在同一官方线程继续推进。")
    return 0


def _stage05_block_surface(project_dir: Path, stage05_manifest_path: Path, stage05_data: dict) -> int:
    images_dir = stage05_manifest_path.parent
    summary = stage05_data.get("summary") if isinstance(stage05_data.get("summary"), dict) else {}
    self_check = stage05_data.get("self_check") if isinstance(stage05_data.get("self_check"), dict) else {}
    quality_review = stage05_data.get("quality_review") if isinstance(stage05_data.get("quality_review"), dict) else {}
    creator_runtime_status = stage05_data.get("creator_runtime_status") if isinstance(stage05_data.get("creator_runtime_status"), dict) else {}
    reference_status = stage05_data.get("reference_image_status") if isinstance(stage05_data.get("reference_image_status"), dict) else {}
    readiness = stage05_data.get("stage05_execution_readiness") if isinstance(stage05_data.get("stage05_execution_readiness"), dict) else {}
    workbench_path = images_dir / "stage05_review_workbench.html"
    reference_entry = project_dir / "03_characters" / "reference_image_start_here.md"
    stage05_start_here = project_dir / "04_keyframes" / "stage05_start_here.md"
    all_exist = bool(self_check.get("all_required_images_exist"))
    manual_review_cleared = bool(self_check.get("manual_review_cleared")) or bool(quality_review.get("manual_review_cleared"))
    missing_paths = reference_status.get("missing_paths") if isinstance(reference_status.get("missing_paths"), list) else []
    ready_for_stage06 = bool(self_check.get("ready_for_video_clip_generation"))
    print("PIPELINE_BLOCKED_STAGE: STAGE_05_KEYFRAME_IMAGES")
    print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_BLOCKED_STAGE05_MANIFEST: {str(stage05_manifest_path.resolve()).replace(chr(92), '/')}")
    print("Stage 05 当前还没有进入可正式确认状态。")
    print("当前摘要：")
    print(f"- 预期图片数：{summary.get('expected_image_count') or 0}")
    print(f"- 已落盘图片数：{summary.get('generated_image_count') or 0}")
    print(f"- 是否全部图片已齐：{_yes_no(all_exist)}")
    print(f"- 人工复核是否已清：{_yes_no(manual_review_cleared)}")
    print(f"- 是否可进入 Stage 06：{_yes_no(ready_for_stage06)}")
    print("阻断原因：")
    if missing_paths:
        print("- Stage 05 仍缺角色参考图，当前不能打开正式确认门。")
        for path in missing_paths:
            print(f"- 缺失参考图：{path}")
    elif not all_exist:
        print("- Stage 05 关键帧仍未全部生成完成，当前不能打开正式确认门。")
    elif not manual_review_cleared:
        print("- Stage 05 仍有高风险关键帧待人工复核，当前不能打开正式确认门。")
    else:
        print(f"- {str((creator_runtime_status.get('headline') or '')).strip() or 'Stage 05 仍未满足正式确认条件。'}")
    detail = str((creator_runtime_status.get("detail") or "")).strip()
    if detail:
        print(f"- 详情：{detail}")
    blocker_reasons = readiness.get("blocker_reasons") if isinstance(readiness.get("blocker_reasons"), list) else []
    for reason in blocker_reasons:
        print(f"- readiness 阻断：{reason}")
    print("下一步：")
    if missing_paths and reference_entry.exists():
        print(str(reference_entry.resolve()).replace(chr(92), '/'))
    elif stage05_start_here.exists():
        print(str(stage05_start_here.resolve()).replace(chr(92), '/'))
    elif workbench_path.exists():
        print(str(workbench_path.resolve()).replace(chr(92), '/'))
    else:
        print("继续补齐缺失关键帧并重新同步 Stage 05 manifest。")
    return 1


def _stage05_review_gate(project_dir: Path, stage05_manifest_path: Path) -> int:
    images_dir = stage05_manifest_path.parent
    try:
        existing_stage05_data = _load_stage05_manifest(stage05_manifest_path)
    except SystemExit as exc:
        print(str(exc))
        return 1
    if _stage04_prompts_use_stage05_codex_contract(project_dir) and not _stage05_manifest_uses_codex_contract(existing_stage05_data):
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        keyframe_json = project_dir / "04_keyframes" / "keyframe_prompts.json"
        if not locked_brief.exists() or not keyframe_json.exists():
            print("PIPELINE_BLOCKED_STAGE05_CONTRACT_HANDOFF")
            print("Stage 04 已经携带 stage05_semantic_contract，但 Stage 05 legacy manifest 缺少正式主线重建所需的上游文件。")
            return 1
        print("PIPELINE_STAGE05_CONTRACT_HANDOFF_REBUILD: legacy manifest detected")
        print("PIPELINE_DISPATCH_STAGE: STAGE_05_KEYFRAME_IMAGES_GENERATION")
        print(
            "PIPELINE_DISPATCH_REASON: Stage04 已进入 Codex Stage05 contract 主线，但当前 Stage05 manifest 仍是 legacy package，"
            "需要先重建正式主线产物后才能进入 review。"
        )
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage05_from_confirmed_keyframe_prompts.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(keyframe_json).replace(chr(92), '/')} {str(stage05_manifest_path).replace(chr(92), '/')}"
        )
        exit_code = run_stage05_from_confirmed_keyframe_prompts.main([
            str(locked_brief),
            str(keyframe_json),
            str(stage05_manifest_path),
        ])
        if exit_code != 0:
            return exit_code
        try:
            rebuilt_stage05_data = _load_stage05_manifest(stage05_manifest_path)
        except SystemExit as exc:
            print(str(exc))
            return 1
        if not _stage05_manifest_uses_codex_contract(rebuilt_stage05_data):
            print("PIPELINE_BLOCKED_STAGE05_CONTRACT_HANDOFF")
            print("Stage 04 的 Codex contract 已存在，但 Stage 05 manifest 重建后仍未切入 codex_contract 主线。")
            return 1
    sync_exit_code = sync_keyframe_image_manifest.main([str(stage05_manifest_path)])
    if sync_exit_code != 0:
        print(f"PIPELINE_BLOCKED_STAGE05_MANIFEST: {str(stage05_manifest_path.resolve()).replace(chr(92), '/')}")
        print("Stage 05 manifest sync failed before review gate; current state may be stale.")
        return 1
    try:
        stage05_data = _load_stage05_manifest(stage05_manifest_path)
    except SystemExit as exc:
        print(str(exc))
        return 1
    summary = stage05_data.get("summary") if isinstance(stage05_data.get("summary"), dict) else {}
    self_check = stage05_data.get("self_check") if isinstance(stage05_data.get("self_check"), dict) else {}
    quality_review = stage05_data.get("quality_review") if isinstance(stage05_data.get("quality_review"), dict) else {}
    reference_bootstrap = stage05_data.get("reference_bootstrap") if isinstance(stage05_data.get("reference_bootstrap"), dict) else {}
    creator_runtime_status = stage05_data.get("creator_runtime_status") if isinstance(stage05_data.get("creator_runtime_status"), dict) else {}
    workbench_path = images_dir / "stage05_review_workbench.html"
    if _stage05_active_job_count(stage05_data) > 0:
        return _stage05_progress_surface(project_dir, stage05_manifest_path, stage05_data)
    if not bool(self_check.get("ready_for_video_clip_generation")):
        return _stage05_block_surface(project_dir, stage05_manifest_path, stage05_data)
    print("PIPELINE_REVIEW_STAGE: STAGE_05_KEYFRAME_IMAGES_REVIEW")
    print(f"PIPELINE_REVIEW_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_REVIEW_CONFIRM_COMMAND: python skills/video-production-pipeline/scripts/confirm_stage05_and_continue.py {str(project_dir).replace(chr(92), '/')}")
    print("Stage 05 关键帧图片包已生成：")
    for name in [
        "image_generation_plan.md",
        "image_generation_jobs.json",
        "keyframe_image_manifest.json",
        "comfyui_image_requests.json",
        "manual_review.md",
        "prompt_patch_cards.md",
        "stage05_review_workbench.html",
    ]:
        print(f"- {str((images_dir / name).resolve()).replace(chr(92), '/')}")
    print(f"- {str((images_dir / 'keyframes').resolve()).replace(chr(92), '/')}")
    if workbench_path.exists():
        print("")
        print("建议先看：")
        print(str(workbench_path.resolve()).replace(chr(92), '/'))
    print("")
    print("当前摘要：")
    print(f"- Stage05 主线模式：{str(stage05_data.get('stage05_mode') or '').strip() or '未提供'}")
    print(f"- Stage05-A 主参考图是否已就绪：{_yes_no(reference_bootstrap.get('ready'))}")
    print(f"- 预期图片数：{summary.get('expected_image_count') or 0}")
    print(f"- 已落盘图片数：{summary.get('generated_image_count') or 0}")
    print(f"- 待人工复核数：{quality_review.get('pending_count') or 0}")
    print(f"- 是否全部图片已齐：{_yes_no(self_check.get('all_required_images_exist'))}")
    print(f"- 是否可进入 Stage 06：{_yes_no(self_check.get('ready_for_video_clip_generation'))}")
    print(f"- 当前阻断：{str((creator_runtime_status.get('headline') or '')).strip() or ('无' if self_check.get('ready_for_video_clip_generation') else '尚未完成 Stage 05 正式确认')}")
    detail = str((creator_runtime_status.get('detail') or '')).strip()
    if detail:
        print(f"- 阻断详情：{detail}")
    notes = self_check.get("notes") if isinstance(self_check.get("notes"), list) else []
    if notes:
        print(f"- 当前提示：{str(notes[0]).strip()}")
    print("")
    print("请确认：")
    print("A. 关键帧图片可以，后续进入 Stage 06 视频片段生成")
    print("B. 打开 Stage 05 审图工作台")
    print("C. 批准当前高风险复核队列")
    print("D. 对高风险图片执行自动重跑")
    print("E. 手动补图后重新同步 Stage 05")
    print("F. 重新生成 Stage 05 图片包")
    return 0


def _stage06_pre_entry_block_surface(project_dir: Path, stage05_manifest_path: Path) -> int:
    print("PIPELINE_BLOCKED_STAGE: STAGE_06_VIDEO_CLIPS")
    print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_BLOCKED_STAGE05_MANIFEST: {str(stage05_manifest_path.resolve()).replace(chr(92), '/')}")
    print("Stage 05 已确认完成。")
    print("当前官方入口已经正确停在 Stage 06 前置阻断面。")
    print("阻断原因：")
    print("- Stage 06 官方主线改造不在当前批次范围内，当前只允许停在这里作为 Batch 5 的最远正确位置。")
    return 1


def _stage06_block_surface(project_dir: Path, stage06_manifest_path: Path, stage06_data: dict) -> int:
    summary = stage06_data.get("summary") if isinstance(stage06_data.get("summary"), dict) else {}
    self_check = stage06_data.get("self_check") if isinstance(stage06_data.get("self_check"), dict) else {}
    planning = stage06_data.get("planning_overrides") if isinstance(stage06_data.get("planning_overrides"), dict) else {}
    print("PIPELINE_BLOCKED_STAGE: STAGE_06_VIDEO_CLIPS")
    print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_BLOCKED_STAGE06_MANIFEST: {str(stage06_manifest_path.resolve()).replace(chr(92), '/')}")
    print("Stage 06 当前还没有进入可正式确认状态。")
    print("当前摘要：")
    print(f"- 预期 clip 数：{summary.get('expected_clip_count') or 0}")
    print(f"- 已落盘 clip 数：{summary.get('generated_clip_count') or 0}")
    print(f"- 阻断 clip 数：{summary.get('blocked_clip_count') or 0}")
    print(f"- 是否全部 clip 已齐：{_yes_no(self_check.get('all_required_clips_exist'))}")
    print(f"- Stage 05 是否已正式清审：{_yes_no(self_check.get('source_stage05_ready_for_video_clip_generation'))}")
    print(f"- 是否可进入 Stage 07：{_yes_no(self_check.get('ready_for_audio_stage'))}")
    formal_progression_status = str(planning.get("formal_progression_status") or "").strip()
    if formal_progression_status:
        print(f"- 当前推进状态：{formal_progression_status}")
    print("阻断原因：")
    if not bool(self_check.get("all_required_clips_exist")):
        print("- Stage 06 片段还不齐，当前不能打开正式确认门。")
    if not bool(self_check.get("source_stage05_ready_for_video_clip_generation")):
        print("- Stage 05 仍未正式清审，当前 Stage 06 结果只能按草稿态展示。")
    if not bool(self_check.get("ready_for_audio_stage")) and bool(self_check.get("all_required_clips_exist")):
        print("- Stage 06 仍包含占位或证据不足的 clip，当前不能正式推进到 Stage 07。")
    print("下一步：")
    print("补齐缺失或占位 clip，并重新同步 Stage 06 manifest。")
    return 1


def _stage06_review_gate(project_dir: Path, stage06_manifest_path: Path) -> int:
    clips_dir = stage06_manifest_path.parent
    sync_exit_code = sync_video_clip_manifest.main([str(stage06_manifest_path)])
    if sync_exit_code != 0:
        print("PIPELINE_BLOCKED_STAGE: STAGE_06_VIDEO_CLIPS")
        print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
        print(f"PIPELINE_BLOCKED_STAGE06_MANIFEST: {str(stage06_manifest_path.resolve()).replace(chr(92), '/')}")
        print("Stage 06 manifest 重新同步失败，当前不能进入 review gate。")
        return 1
    try:
        stage06_data = _load_stage05_manifest(stage06_manifest_path)
    except SystemExit as exc:
        print(str(exc))
        return 1
    self_check = stage06_data.get("self_check") if isinstance(stage06_data.get("self_check"), dict) else {}
    if not bool(self_check.get("ready_for_audio_stage")):
        return _stage06_block_surface(project_dir, stage06_manifest_path, stage06_data)
    ok, errors, _warnings = validate_video_clip_manifest.validate(stage06_data, stage06_manifest_path, mode="final")
    if not ok:
        print("PIPELINE_BLOCKED_STAGE: STAGE_06_VIDEO_CLIPS")
        print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
        print(f"PIPELINE_BLOCKED_STAGE06_MANIFEST: {str(stage06_manifest_path.resolve()).replace(chr(92), '/')}")
        print("Stage 06 视频片段正式校验未通过，当前不能进入 review gate。")
        print("阻断原因：")
        for error in errors:
            print(f"- {error}")
        return 1
    summary = stage06_data.get("summary") if isinstance(stage06_data.get("summary"), dict) else {}
    planning = stage06_data.get("planning_overrides") if isinstance(stage06_data.get("planning_overrides"), dict) else {}
    print("PIPELINE_REVIEW_STAGE: STAGE_06_VIDEO_CLIPS_REVIEW")
    print(f"PIPELINE_REVIEW_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_REVIEW_CONFIRM_COMMAND: python skills/video-production-pipeline/scripts/confirm_stage06_and_continue.py {str(project_dir).replace(chr(92), '/')}")
    print("Stage 06 视频片段包已生成：")
    for name in [
        "video_clip_generation_plan.md",
        "video_clip_jobs.json",
        "video_clip_manifest.json",
        "comfyui_ltx_i2v_requests.json",
        "manual_video_requests.json",
        "clip_review.md",
    ]:
        print(f"- {str((clips_dir / name).resolve()).replace(chr(92), '/')}")
    print(f"- {str((clips_dir / 'clips').resolve()).replace(chr(92), '/')}")
    print("")
    print("当前摘要：")
    print(f"- 预期 clip 数：{summary.get('expected_clip_count') or 0}")
    print(f"- 已落盘 clip 数：{summary.get('generated_clip_count') or 0}")
    print(f"- 当前阻断 clip 数：{summary.get('blocked_clip_count') or 0}")
    print(f"- 是否全部 clip 已齐：{_yes_no(self_check.get('all_required_clips_exist'))}")
    print(f"- 是否具备 Stage 07 推进条件：{_yes_no(self_check.get('ready_for_audio_stage'))}")
    print(f"- Stage 05 是否已正式清审：{_yes_no(self_check.get('source_stage05_ready_for_video_clip_generation'))}")
    print(f"- 当前 formal promotion 状态：{str(stage06_data.get('formal_promotion_status') or '').strip() or '未提供'}")
    notes = self_check.get("notes") if isinstance(self_check.get("notes"), list) else []
    if notes:
        print(f"- 当前提示：{str(notes[0]).strip()}")
    if planning:
        print(f"- 规划摘要：{str(planning.get('formal_progression_status') or '').strip() or '未提供'}")
    print("")
    print("请确认：")
    print("A. 视频片段可以，后续进入 Stage 07 音频生成")
    print("B. 查看 Stage 06 片段复核说明")
    print("C. 补齐或替换缺失 clip 后重新同步 Stage 06")
    print("D. 重新生成 Stage 06 视频片段")
    return 0


def _stage07_review_gate(project_dir: Path, stage07_manifest_path: Path) -> int:
    audio_dir = stage07_manifest_path.parent
    try:
        stage07_data = _load_stage05_manifest(stage07_manifest_path)
    except SystemExit as exc:
        print(str(exc))
        return 1
    ok, errors, _warnings = validate_audio_manifest.validate(stage07_data, stage07_manifest_path, mode="final")
    if not ok:
        print("PIPELINE_BLOCKED_STAGE: STAGE_07_AUDIO")
        print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
        print(f"PIPELINE_BLOCKED_STAGE07_MANIFEST: {str(stage07_manifest_path.resolve()).replace(chr(92), '/')}")
        print("Stage 07 音频正式校验未通过，当前不能进入 review gate。")
        print("阻断原因：")
        for error in errors:
            print(f"- {error}")
        return 1
    summary = stage07_data.get("summary") if isinstance(stage07_data.get("summary"), dict) else {}
    self_check = stage07_data.get("self_check") if isinstance(stage07_data.get("self_check"), dict) else {}
    print("PIPELINE_REVIEW_STAGE: STAGE_07_AUDIO_REVIEW")
    print(f"PIPELINE_REVIEW_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_REVIEW_CONFIRM_COMMAND: python skills/video-production-pipeline/scripts/confirm_stage07_and_continue.py {str(project_dir).replace(chr(92), '/')}")
    print("Stage 07 音频包已生成：")
    for name in [
        "audio_plan.md",
        "audio_jobs.json",
        "audio_manifest.json",
        "indextts2_requests.json",
        "music_requests.json",
        "audio_review.md",
    ]:
        print(f"- {str((audio_dir / name).resolve()).replace(chr(92), '/')}")
    print(f"- {str((audio_dir / 'voice').resolve()).replace(chr(92), '/')}")
    print(f"- {str((audio_dir / 'music').resolve()).replace(chr(92), '/')}")
    print("")
    print("当前摘要：")
    print(f"- 预期语音数：{summary.get('expected_voice_count') or 0}")
    print(f"- 已生成语音数：{summary.get('generated_voice_count') or 0}")
    print(f"- 预期音乐数：{summary.get('expected_music_count') or 0}")
    print(f"- 已生成音乐数：{summary.get('generated_music_count') or 0}")
    print(f"- 是否全部音频已齐：{_yes_no(self_check.get('all_required_audio_files_exist'))}")
    print(f"- 是否可进入 Stage 08：{_yes_no(self_check.get('ready_for_assembly_stage'))}")
    notes = self_check.get("notes") if isinstance(self_check.get("notes"), list) else []
    if notes:
        print(f"- 当前提示：{str(notes[0]).strip()}")
    print("")
    print("请确认：")
    print("A. 音频包可以，后续进入 Stage 08 粗剪装配")
    print("B. 查看 Stage 07 音频复核说明")
    print("C. 补齐或替换缺失音频后重新同步 Stage 07")
    print("D. 重新生成 Stage 07 音频包")
    return 0


def _stage08_pre_entry_block_surface(project_dir: Path, stage07_manifest_path: Path) -> int:
    print("PIPELINE_BLOCKED_STAGE: STAGE_08_ASSEMBLY")
    print(f"PIPELINE_BLOCKED_PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"PIPELINE_BLOCKED_STAGE07_MANIFEST: {str(stage07_manifest_path.resolve()).replace(chr(92), '/')}")
    print("Stage 07 已确认完成。")
    print("当前官方入口已经正确停在 Stage 08 前置阻断面。")
    print("阻断原因：")
    print("- Stage 08 官方主线改造不在当前批次范围内，当前只允许停在这里作为 Batch 6 的最远正确位置。")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    workspace_state_path = Path(args.stage00_state).resolve()
    if not args.manifest and not args.project_dir:
        workspace_state = _load_stage00_state_if_active(workspace_state_path)
        if workspace_state is not None:
            project_dir_text = str(workspace_state.get("project_dir") or "").strip()
            if project_dir_text:
                manifest_candidate = Path(project_dir_text) / "project_manifest.json"
                if manifest_candidate.exists():
                    args.project_dir = str(Path(project_dir_text))
                else:
                    project_dir_text = ""
            if not project_dir_text:
                status = str(workspace_state.get("status") or "").strip()
                if status == "draft_ready":
                    return run_stage00_controller.main([
                        "--state-json",
                        str(workspace_state_path),
                    ])
                return run_stage00_controller.main([
                    "--state-json",
                    str(workspace_state_path),
                ])
        if _resolve_manifest(args) is None:
            return run_stage00_controller.main([
                "--state-json",
                str(workspace_state_path),
            ])

    manifest_path = _resolve_manifest(args)
    if manifest_path is None or not manifest_path.exists():
        print("NO_PROJECT_FOUND")
        return 1

    synced = sync_project_manifest_truth(manifest_path)
    if synced is None or not synced.exists():
        print(f"ERROR: unable to sync manifest: {manifest_path}")
        return 1
    data = load_json_file(synced)
    project_dir = synced.parent

    current_stage = str(data.get("current_stage") or "").strip()
    allowed_next_stage = str(data.get("allowed_next_stage") or "").strip()
    brief_locked = bool(data.get("brief_locked"))
    script_confirmed = bool(data.get("script_confirmed"))
    storyboard_confirmed = bool(data.get("storyboard_confirmed"))
    character_bible_confirmed = bool(data.get("character_bible_confirmed"))
    keyframe_prompts_confirmed = bool(data.get("keyframe_prompts_confirmed"))
    keyframe_images_confirmed = bool(data.get("keyframe_images_confirmed"))
    intake_state_path = project_dir / "00_intake" / "intake_state.json"
    script_json = project_dir / "01_script" / "script.json"
    storyboard_json = project_dir / "02_storyboard" / "storyboard.json"
    character_json = project_dir / "03_characters" / "character_bible.json"
    keyframe_json = project_dir / "04_keyframes" / "keyframe_prompts.json"
    stage05_manifest_json = project_dir / "05_images" / "keyframe_image_manifest.json"
    stage06_manifest_json = project_dir / "06_video_clips" / "video_clip_manifest.json"
    stage07_manifest_json = project_dir / "07_audio" / "audio_manifest.json"

    if not brief_locked and current_stage == "STAGE_00_INTAKE" and intake_state_path.exists():
        intake_state = _load_stage00_state_if_active(intake_state_path)
        if intake_state is not None:
            if str(intake_state.get("status") or "").strip() == "draft_ready":
                return run_stage00_controller.main([
                    "--state-json",
                    str(intake_state_path),
                    "--project-dir",
                    str(project_dir),
                ])
            return run_stage00_controller.main([
                "--state-json",
                str(intake_state_path),
                "--project-dir",
                str(project_dir),
            ])

    if brief_locked and not script_confirmed and script_json.exists():
        return _stage01_review_gate(project_dir, script_json)

    if brief_locked and script_confirmed and not storyboard_confirmed and storyboard_json.exists():
        return _stage02_review_gate(project_dir, storyboard_json)

    if brief_locked and storyboard_confirmed and not character_bible_confirmed and character_json.exists():
        return _stage03_review_gate(project_dir, character_json)

    if brief_locked and character_bible_confirmed and not keyframe_prompts_confirmed and keyframe_json.exists():
        return _stage04_review_gate(project_dir, keyframe_json)

    if brief_locked and keyframe_prompts_confirmed and not keyframe_images_confirmed and stage05_manifest_json.exists():
        existing_stage05_data = _load_stage05_manifest(stage05_manifest_json)
        if _stage05_manifest_uses_codex_contract(existing_stage05_data):
            return _stage05_review_gate(project_dir, stage05_manifest_json)
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists() or not keyframe_json.exists():
            print("ERROR: Stage 05 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_05_KEYFRAME_IMAGES_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage05_from_confirmed_keyframe_prompts.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(keyframe_json).replace(chr(92), '/')} {str(stage05_manifest_json).replace(chr(92), '/')}"
        )
        exit_code = run_stage05_from_confirmed_keyframe_prompts.main([str(locked_brief), str(keyframe_json), str(stage05_manifest_json)])
        if exit_code != 0:
            return exit_code
        if not stage05_manifest_json.exists():
            print(f"ERROR: Stage 05 completed without manifest artifact: {stage05_manifest_json}")
            return 1
        return _stage05_review_gate(project_dir, stage05_manifest_json)

    if brief_locked and keyframe_images_confirmed and not bool(data.get("video_clips_confirmed")) and stage06_manifest_json.exists():
        return _stage06_review_gate(project_dir, stage06_manifest_json)

    if brief_locked and bool(data.get("video_clips_confirmed")) and not bool(data.get("audio_confirmed")) and stage07_manifest_json.exists():
        return _stage07_review_gate(project_dir, stage07_manifest_json)

    if brief_locked and bool(data.get("audio_confirmed")) and stage07_manifest_json.exists():
        return _stage08_pre_entry_block_surface(project_dir, stage07_manifest_json)

    if brief_locked and not script_confirmed and current_stage in {"STAGE_00_BRIEF_LOCKED", "STAGE_01_SCRIPT_GENERATION"} and allowed_next_stage == "STAGE_01_SCRIPT_GENERATION":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists():
            print(f"ERROR: locked brief not found: {locked_brief}")
            return 1
        print(f"PIPELINE_DISPATCH_STAGE: STAGE_01_SCRIPT_GENERATION")
        print(f"PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py {str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')}")
        exit_code = run_stage01_from_locked_brief.main([str(locked_brief), str(script_json)])
        if exit_code != 0:
            return exit_code
        if not script_json.exists():
            print(f"ERROR: Stage 01 completed without script artifact: {script_json}")
            return 1
        return _stage01_review_gate(project_dir, script_json)

    if brief_locked and script_confirmed and not storyboard_confirmed and current_stage in {"STAGE_01_SCRIPT_CONFIRMED", "STAGE_02_STORYBOARD_GENERATION"} and allowed_next_stage == "STAGE_02_STORYBOARD":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists() or not script_json.exists():
            print("ERROR: Stage 02 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_02_STORYBOARD_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage02_from_confirmed_script.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')}"
        )
        exit_code = run_stage02_from_confirmed_script.main([str(locked_brief), str(script_json), str(storyboard_json)])
        if exit_code != 0:
            return exit_code
        if not storyboard_json.exists():
            print(f"ERROR: Stage 02 completed without storyboard artifact: {storyboard_json}")
            return 1
        return _stage02_review_gate(project_dir, storyboard_json)

    if brief_locked and storyboard_confirmed and not character_bible_confirmed and current_stage in {"STAGE_02_STORYBOARD_CONFIRMED", "STAGE_03_CHARACTER_BIBLE_GENERATION"} and allowed_next_stage == "STAGE_03_CHARACTER_BIBLE":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists() or not script_json.exists() or not storyboard_json.exists():
            print("ERROR: Stage 03 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_03_CHARACTER_BIBLE_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage03_from_confirmed_storyboard.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')} {str(character_json).replace(chr(92), '/')}"
        )
        exit_code = run_stage03_from_confirmed_storyboard.main([str(locked_brief), str(script_json), str(storyboard_json), str(character_json)])
        if exit_code != 0:
            return exit_code
        if not character_json.exists():
            print(f"ERROR: Stage 03 completed without character artifact: {character_json}")
            return 1
        return _stage03_review_gate(project_dir, character_json)

    if brief_locked and character_bible_confirmed and not keyframe_prompts_confirmed and current_stage in {"STAGE_03_CHARACTER_BIBLE_CONFIRMED", "STAGE_04_KEYFRAME_PROMPTS_GENERATION"} and allowed_next_stage == "STAGE_04_KEYFRAME_PROMPTS":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists() or not script_json.exists() or not storyboard_json.exists() or not character_json.exists():
            print("ERROR: Stage 04 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_04_KEYFRAME_PROMPTS_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage04_from_confirmed_character_bible.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')} {str(character_json).replace(chr(92), '/')} {str(keyframe_json).replace(chr(92), '/')}"
        )
        exit_code = run_stage04_from_confirmed_character_bible.main([str(locked_brief), str(script_json), str(storyboard_json), str(character_json), str(keyframe_json)])
        if exit_code != 0:
            return exit_code
        if not keyframe_json.exists():
            print(f"ERROR: Stage 04 completed without keyframe artifact: {keyframe_json}")
            return 1
        return _stage04_review_gate(project_dir, keyframe_json)

    if brief_locked and keyframe_prompts_confirmed and not keyframe_images_confirmed and current_stage in {"STAGE_04_KEYFRAME_PROMPTS_CONFIRMED", "STAGE_05_KEYFRAME_IMAGES_GENERATION"} and allowed_next_stage == "STAGE_05_KEYFRAME_IMAGES":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists() or not keyframe_json.exists():
            print("ERROR: Stage 05 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_05_KEYFRAME_IMAGES_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage05_from_confirmed_keyframe_prompts.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(keyframe_json).replace(chr(92), '/')} {str(stage05_manifest_json).replace(chr(92), '/')}"
        )
        exit_code = run_stage05_from_confirmed_keyframe_prompts.main([str(locked_brief), str(keyframe_json), str(stage05_manifest_json)])
        if exit_code != 0:
            return exit_code
        if not stage05_manifest_json.exists():
            print(f"ERROR: Stage 05 completed without manifest artifact: {stage05_manifest_json}")
            return 1
        return _stage05_review_gate(project_dir, stage05_manifest_json)

    if brief_locked and keyframe_images_confirmed and not bool(data.get("video_clips_confirmed")) and current_stage in {"STAGE_05_KEYFRAME_IMAGES_CONFIRMED", "STAGE_06_VIDEO_CLIPS_GENERATION", "STAGE_06_VIDEO_CLIPS"} and allowed_next_stage == "STAGE_06_VIDEO_CLIPS":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists() or not storyboard_json.exists() or not keyframe_json.exists() or not stage05_manifest_json.exists():
            print("ERROR: Stage 06 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_06_VIDEO_CLIPS_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage06_from_confirmed_keyframe_images.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')} {str(keyframe_json).replace(chr(92), '/')} {str(stage05_manifest_json).replace(chr(92), '/')} {str(stage06_manifest_json).replace(chr(92), '/')}"
        )
        exit_code = run_stage06_from_confirmed_keyframe_images.main([
            str(locked_brief),
            str(storyboard_json),
            str(keyframe_json),
            str(stage05_manifest_json),
            str(stage06_manifest_json),
        ])
        if exit_code != 0 and not stage06_manifest_json.exists():
            return exit_code
        if not stage06_manifest_json.exists():
            print(f"ERROR: Stage 06 completed without manifest artifact: {stage06_manifest_json}")
            return 1
        return _stage06_review_gate(project_dir, stage06_manifest_json)

    if brief_locked and bool(data.get("video_clips_confirmed")) and not bool(data.get("audio_confirmed")) and current_stage in {"STAGE_06_VIDEO_CLIPS_CONFIRMED", "STAGE_07_AUDIO_GENERATION", "STAGE_07_AUDIO"} and allowed_next_stage == "STAGE_07_AUDIO":
        locked_brief = project_dir / "00_intake" / "project_brief.locked.json"
        if not locked_brief.exists() or not script_json.exists() or not storyboard_json.exists() or not character_json.exists() or not stage06_manifest_json.exists():
            print("ERROR: Stage 07 upstream files are missing")
            return 1
        print("PIPELINE_DISPATCH_STAGE: STAGE_07_AUDIO_GENERATION")
        print(
            "PIPELINE_DISPATCH_COMMAND: python skills/video-production-pipeline/scripts/run_stage07_from_confirmed_video_clips.py "
            f"{str(locked_brief).replace(chr(92), '/')} {str(script_json).replace(chr(92), '/')} {str(storyboard_json).replace(chr(92), '/')} {str(character_json).replace(chr(92), '/')} {str(stage06_manifest_json).replace(chr(92), '/')} {str(stage07_manifest_json).replace(chr(92), '/')}"
        )
        exit_code = run_stage07_from_confirmed_video_clips.main([
            str(locked_brief),
            str(script_json),
            str(storyboard_json),
            str(character_json),
            str(stage06_manifest_json),
            str(stage07_manifest_json),
        ])
        if exit_code != 0 and not stage07_manifest_json.exists():
            return exit_code
        if not stage07_manifest_json.exists():
            print(f"ERROR: Stage 07 completed without manifest artifact: {stage07_manifest_json}")
            return 1
        return _stage07_review_gate(project_dir, stage07_manifest_json)

    print(f"PIPELINE_CONTINUE_NOT_IMPLEMENTED: {current_stage or 'UNKNOWN_STAGE'}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
