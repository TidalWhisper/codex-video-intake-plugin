#!/usr/bin/env python3
"""Official Stage 00 controller for the codex-first pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PIPELINE_SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
INTAKE_SCRIPT_DIR = PLUGIN_ROOT / "skills" / "video-project-intake" / "scripts"
sys.path.insert(0, str(INTAKE_SCRIPT_DIR))
sys.path.insert(0, str(PIPELINE_SCRIPT_DIR))

import run_stage00_brief_from_intake  # noqa: E402
import run_stage00_intake_turn  # noqa: E402
import run_stage00_lock_and_continue  # noqa: E402
import validate_stage00_intake_state as validate_stage00_intake_state_module  # noqa: E402
from stage00_intake_common import (  # noqa: E402
    QUESTION_INDEX_TO_KEY,
    QUESTION_KEYS,
    build_initial_state,
    canonical_question_block,
    load_or_create_state,
    utc_now,
)

QUESTION_TO_NORMALIZED_FIELDS = {
    "idea": ["idea"],
    "target_duration": ["target_duration_sec", "target_duration_label"],
    "genre": ["genre"],
    "style": ["style"],
    "visual_spec": ["aspect_ratio", "aspect_ratio_label", "resolution", "resolution_label"],
    "characters": ["characters_mode", "characters_required"],
    "voice": ["voice_mode", "voice_required"],
    "music": ["music_mode", "music_profile", "music_required"],
    "final_output": ["final_output"],
}

BRIEF_ARTIFACT_PATTERNS = [
    "project_brief.draft.json",
    "project_brief.locked.json",
    "stage00_brief_confirmation_summary.json",
    "stage00_brief_confirmation_summary.md",
    "stage00_brief_prompt_packet.json",
    "stage00_brief_llm_output.json",
    "stage00_brief_codex_last_message.txt",
    "stage00_brief_codex_generation_request.txt",
    "stage00_brief_validation_errors.json",
    "stage00_brief_repair_packet.json",
    "stage00_brief_codex_repair_request_attempt_*.txt",
    "stage00_brief_codex_repair_last_message_attempt_*.txt",
]


def default_state_path() -> Path:
    return Path(".video_project/intake/intake_state.json").resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-json", default=str(default_state_path()), help="Path to intake_state.json")
    parser.add_argument("--user-reply", default="", help="Raw user reply for the current Stage 00 turn")
    parser.add_argument("--project-root", default="video_projects", help="Root directory for project creation when the intake is still workspace-local")
    parser.add_argument("--project-dir", default=None, help="Explicit project directory to use for Stage 00-B output")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary name or path")
    parser.add_argument("--max-repair-attempts", type=int, default=2, help="How many automatic repair attempts to allow after the first generation fails validation")
    return parser.parse_args(argv)


def _write_state(state_path: Path, state: dict[str, Any]) -> None:
    ok, errors, warnings = validate_stage00_intake_state_module.validate(state, state_path)
    if not ok:
        raise SystemExit("ERROR: Stage 00 controller produced invalid intake state:\n- " + "\n- ".join(errors))
    for warning in warnings:
        print(f"WARNING: {warning}")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _latest_project(root: Path) -> Path | None:
    if not root.exists() or not root.is_dir():
        return None
    candidates = [item for item in root.iterdir() if item.is_dir() and (item / "project_manifest.json").exists()]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return candidates[0]


def _resolve_project_dir(state_path: Path, state: dict[str, Any], explicit_project_dir: Path | None) -> Path | None:
    if explicit_project_dir is not None:
        return explicit_project_dir.resolve()
    project_dir_text = str(state.get("project_dir") or "").strip()
    if project_dir_text:
        return Path(project_dir_text).resolve()
    if state_path.parent.name == "00_intake" and (state_path.parent.parent / "project_manifest.json").exists():
        return state_path.parent.parent.resolve()
    return None


def _remove_stage00_brief_artifacts(project_dir: Path) -> None:
    intake_dir = project_dir / "00_intake"
    if not intake_dir.exists():
        return
    for pattern in BRIEF_ARTIFACT_PATTERNS:
        for path in intake_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def _reset_manifest_for_stage00(project_dir: Path) -> None:
    manifest_path = project_dir / "project_manifest.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return
    manifest["current_stage"] = "STAGE_00_INTAKE"
    manifest["allowed_next_stage"] = None
    manifest["brief_locked"] = False
    manifest["script_confirmed"] = False
    manifest["storyboard_confirmed"] = False
    manifest["character_bible_confirmed"] = False
    manifest["keyframe_prompts_confirmed"] = False
    manifest["keyframe_images_confirmed"] = False
    manifest["video_clips_confirmed"] = False
    manifest["audio_confirmed"] = False
    manifest["assembly_confirmed"] = False
    manifest["qa_confirmed"] = False
    manifest["delivery_complete"] = False
    manifest["requested_output_scope"] = ""
    manifest["requested_output_label"] = ""
    manifest["requested_terminal_stage"] = ""
    manifest["compiled_requirements"] = {}
    manifest["quality_contract"] = {}
    manifest["updated_at"] = utc_now()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _render_fallback_summary(project_dir: Path) -> str:
    draft_path = project_dir / "00_intake" / "project_brief.draft.json"
    if not draft_path.exists():
        return "Stage 00 Brief 草稿尚未生成。"
    try:
        draft = json.loads(draft_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return "Stage 00 Brief 草稿已存在，但内容损坏，请重新生成。"
    normalized = draft.get("normalized") if isinstance(draft.get("normalized"), dict) else {}
    lines = [
        "9 项信息已收集完成。",
        "",
        f"项目文件夹：{str(project_dir).replace(chr(92), '/')}",
        "",
        "请确认项目 Brief：",
        f"1. 故事想法：{normalized.get('idea') or ''}",
        f"2. 目标视频时长：{normalized.get('target_duration_label') or ''}",
        f"3. 视频题材：{normalized.get('genre') or ''}",
        f"4. 视频风格：{normalized.get('style') or ''}",
        f"5. 画面规格：{normalized.get('aspect_ratio_label') or ''} + {normalized.get('resolution_label') or ''}".strip(),
        f"6. 固定主角/人物：{normalized.get('characters_mode') or ''}",
        f"7. 配音：{normalized.get('voice_mode') or ''}",
        f"8. 背景音乐：{normalized.get('music_mode') or ''} {normalized.get('music_profile') or ''}".strip(),
        f"9. 最终输出：{normalized.get('final_output') or ''}",
    ]
    return "\n".join(lines).rstrip()


def _print_confirmation_prompt(project_dir: Path) -> int:
    summary_path = project_dir / "00_intake" / "stage00_brief_confirmation_summary.md"
    if summary_path.exists():
        summary_text = summary_path.read_text(encoding="utf-8").strip()
    else:
        summary_text = _render_fallback_summary(project_dir)
    print(summary_text)
    print()
    print(canonical_question_block("final_confirmation"))
    return 0


def _print_modify_item_prompt() -> int:
    print("请选择要修改的 Stage 00 条目编号：1-9。")
    print("1. 故事想法")
    print("2. 目标视频时长")
    print("3. 视频题材")
    print("4. 视频风格")
    print("5. 画面规格")
    print("6. 固定主角/人物")
    print("7. 配音")
    print("8. 背景音乐")
    print("9. 最终输出")
    return 0


def _set_confirmation_mode(state_path: Path, state: dict[str, Any], mode: str) -> None:
    state["confirmation_mode"] = mode
    state["updated_at"] = utc_now()
    _write_state(state_path, state)


def _rewind_state_for_modify(state_path: Path, state: dict[str, Any], question_index: int) -> dict[str, Any]:
    question_key = QUESTION_INDEX_TO_KEY[question_index]
    rewound = load_or_create_state(state_path)
    rewound["status"] = "collecting"
    rewound["current_question"] = question_index
    rewound["current_question_key"] = question_key
    rewound["next_question_key"] = question_key
    rewound["next_prompt_text"] = canonical_question_block(question_key)
    rewound["required_fields_complete"] = False
    rewound["ready_for_brief_generation"] = False
    rewound["needs_followup"] = False
    rewound["followup_reason"] = ""
    rewound["completion_summary"] = ""
    rewound["last_user_reply"] = ""
    rewound["confirmation_mode"] = ""
    keep_keys = QUESTION_KEYS[: question_index - 1]
    clear_keys = QUESTION_KEYS[question_index - 1 :]
    rewound["answers"] = {key: value for key, value in dict(rewound.get("answers") or {}).items() if key in keep_keys}
    rewound["user_answers"] = {key: value for key, value in dict(rewound.get("user_answers") or {}).items() if key in keep_keys}
    normalized = dict(rewound.get("normalized") or {})
    for clear_key in clear_keys:
        for field_name in QUESTION_TO_NORMALIZED_FIELDS.get(clear_key, []):
            normalized.pop(field_name, None)
    rewound["normalized"] = normalized
    rewound["missing_required_fields"] = clear_keys
    rewound["updated_at"] = utc_now()
    _write_state(state_path, rewound)
    return rewound


def _reset_state_from_start(state_path: Path, state: dict[str, Any]) -> dict[str, Any]:
    reset = build_initial_state(state_path)
    reset["project_id"] = str(state.get("project_id") or reset.get("project_id") or "")
    reset["project_dir"] = str(state.get("project_dir") or reset.get("project_dir") or "")
    reset["confirmation_mode"] = ""
    reset["updated_at"] = utc_now()
    _write_state(state_path, reset)
    return reset


def _ensure_draft_materialized(
    *,
    state_path: Path,
    state: dict[str, Any],
    explicit_project_dir: Path | None,
    project_root: Path,
    codex_bin: str,
    max_repair_attempts: int,
) -> Path:
    project_dir = _resolve_project_dir(state_path, state, explicit_project_dir)
    draft_exists = bool(project_dir and (project_dir / "00_intake" / "project_brief.draft.json").exists())
    if draft_exists:
        return project_dir  # type: ignore[return-value]
    exit_code = run_stage00_brief_from_intake.main([
        "--state-json",
        str(state_path),
        "--project-root",
        str(project_root),
        "--codex-bin",
        codex_bin,
        "--max-repair-attempts",
        str(max_repair_attempts),
        *(
            ["--project-dir", str(explicit_project_dir)]
            if explicit_project_dir is not None else []
        ),
    ])
    if exit_code != 0:
        raise SystemExit(exit_code)
    refreshed_state = load_or_create_state(state_path)
    project_dir = _resolve_project_dir(state_path, refreshed_state, explicit_project_dir)
    if project_dir is None:
        latest = _latest_project(project_root)
        if latest is None:
            raise SystemExit("ERROR: Stage 00-B completed but no project directory could be resolved")
        project_dir = latest.resolve()
    return project_dir


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state_path = Path(args.state_json).resolve()
    explicit_project_dir = Path(args.project_dir).resolve() if args.project_dir else None
    project_root = Path(args.project_root).resolve()
    user_reply = str(args.user_reply or "").strip()
    state = load_or_create_state(state_path)
    status = str(state.get("status") or "").strip()

    if str(state.get("confirmation_mode") or "") == "await_modify_item":
        if not user_reply:
            return _print_modify_item_prompt()
        if not user_reply.isdigit() or int(user_reply) not in QUESTION_INDEX_TO_KEY:
            print("请输入 1-9 之间的编号。")
            return _print_modify_item_prompt()
        project_dir = _resolve_project_dir(state_path, state, explicit_project_dir)
        if project_dir is not None:
            _remove_stage00_brief_artifacts(project_dir)
            _reset_manifest_for_stage00(project_dir)
        _rewind_state_for_modify(state_path, state, int(user_reply))
        return run_stage00_intake_turn.main([
            "--state-json",
            str(state_path),
        ])

    if status == "locked":
        print("PIPELINE_STAGE00_STATE: locked")
        return 0

    if status == "collecting":
        if not user_reply:
            return run_stage00_intake_turn.main([
                "--state-json",
                str(state_path),
            ])
        return run_stage00_intake_turn.main([
            "--state-json",
            str(state_path),
            "--user-reply",
            user_reply,
            "--codex-bin",
            str(args.codex_bin),
        ])

    if status != "draft_ready":
        raise SystemExit(f"ERROR: unsupported Stage 00 status: {status or 'UNKNOWN'}")

    project_dir = _ensure_draft_materialized(
        state_path=state_path,
        state=state,
        explicit_project_dir=explicit_project_dir,
        project_root=project_root,
        codex_bin=str(args.codex_bin),
        max_repair_attempts=int(args.max_repair_attempts),
    )
    state = load_or_create_state(state_path)

    if not user_reply:
        return _print_confirmation_prompt(project_dir)

    confirmation_reply = user_reply.strip().upper()
    if confirmation_reply == "A":
        return run_stage00_lock_and_continue.main([str(project_dir)])
    if confirmation_reply == "B":
        _set_confirmation_mode(state_path, state, "await_modify_item")
        return _print_modify_item_prompt()
    if confirmation_reply == "C":
        _remove_stage00_brief_artifacts(project_dir)
        _reset_manifest_for_stage00(project_dir)
        _reset_state_from_start(state_path, state)
        return run_stage00_intake_turn.main([
            "--state-json",
            str(state_path),
        ])

    print("Stage 00 确认阶段只接受 A / B / C。")
    return _print_confirmation_prompt(project_dir)


if __name__ == "__main__":
    raise SystemExit(main())
