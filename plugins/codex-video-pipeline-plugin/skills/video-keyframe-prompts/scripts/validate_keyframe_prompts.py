#!/usr/bin/env python3
"""Validate Stage 04 keyframe/motion prompts JSON without third-party dependencies.

Usage:
  python validate_keyframe_prompts.py --mode draft video_projects/<project_id>/04_keyframes/keyframe_prompts.json
  python validate_keyframe_prompts.py --mode final video_projects/<project_id>/04_keyframes/keyframe_prompts.json
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_script",
    "source_storyboard", "source_character_bible", "shot_prompts", "transition_prompts",
    "global_negative_prompt", "self_check", "allowed_next_stage"
]
REQUIRED_SHOT = [
    "shot_id", "duration_sec", "characters", "scene_summary", "start_keyframe_prompt",
    "end_keyframe_prompt", "motion_prompt", "camera_prompt", "lighting_prompt", "style_prompt",
    "consistency_prompt", "negative_prompt", "image_generation_notes", "video_generation_notes", "dependencies"
]
REQUIRED_TRANSITION = [
    "transition_id", "from_shot_id", "to_shot_id", "transition_type", "transition_motion_prompt", "continuity_requirements"
]
SHOT_ID_RE = re.compile(r"^S\d{3}$")
TRANSITION_ID_RE = re.compile(r"^T\d{3}$")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def validate(data: dict[str, Any], mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_04_KEYFRAME_PROMPTS":
        errors.append("stage must be STAGE_04_KEYFRAME_PROMPTS")
    if data.get("status") not in {"draft", "confirmed"}:
        errors.append("status must be draft or confirmed")
    for key in ["project_id", "source_brief", "source_script", "source_storyboard", "source_character_bible"]:
        if is_blank(data.get(key)):
            errors.append(f"{key} must not be blank")
    if not isinstance(data.get("shot_prompts"), list):
        errors.append("shot_prompts must be a list")
    if not isinstance(data.get("transition_prompts"), list):
        errors.append("transition_prompts must be a list")
    if data.get("reference_image_status") is not None and not isinstance(data.get("reference_image_status"), dict):
        errors.append("reference_image_status must be an object when present")
    if data.get("stage05_execution_readiness") is not None and not isinstance(data.get("stage05_execution_readiness"), dict):
        errors.append("stage05_execution_readiness must be an object when present")
    if not isinstance(data.get("self_check"), dict):
        errors.append("self_check must be an object")

    if mode == "draft":
        if isinstance(data.get("shot_prompts"), list):
            empty_required = []
            for idx, item in enumerate(data.get("shot_prompts") or []):
                if isinstance(item, dict) and is_blank(item.get("start_keyframe_prompt")):
                    empty_required.append(idx)
            if empty_required:
                warnings.append("draft keyframe prompts contain empty prompt fields; expected until Codex fills Stage 04 content")
        return not errors, errors, warnings

    shots = data.get("shot_prompts")
    shot_ids: set[str] = set()
    if isinstance(shots, list):
        if not shots:
            errors.append("shot_prompts must not be empty in final mode")
        for idx, shot in enumerate(shots):
            if not isinstance(shot, dict):
                errors.append(f"shot_prompts[{idx}] must be an object")
                continue
            for key in REQUIRED_SHOT:
                if key not in shot:
                    errors.append(f"shot_prompts[{idx}] missing field: {key}")
            sid = shot.get("shot_id")
            if not isinstance(sid, str) or not SHOT_ID_RE.match(sid):
                errors.append(f"shot_prompts[{idx}].shot_id must look like S001")
            elif sid in shot_ids:
                errors.append(f"duplicate shot_id: {sid}")
            else:
                shot_ids.add(sid)
            dur = shot.get("duration_sec")
            if not isinstance(dur, (int, float)) or dur <= 0:
                errors.append(f"shot_prompts[{idx}].duration_sec must be a positive number")
            if not isinstance(shot.get("characters"), list):
                errors.append(f"shot_prompts[{idx}].characters must be a list")
            for key in ["scene_summary", "start_keyframe_prompt", "end_keyframe_prompt", "motion_prompt", "camera_prompt", "lighting_prompt", "style_prompt", "consistency_prompt", "negative_prompt", "image_generation_notes", "video_generation_notes"]:
                if is_blank(shot.get(key)):
                    errors.append(f"shot_prompts[{idx}].{key} must not be blank in final mode")
            deps = shot.get("dependencies")
            if not isinstance(deps, dict):
                errors.append(f"shot_prompts[{idx}].dependencies must be an object")
            else:
                if not isinstance(deps.get("reference_images"), list):
                    errors.append(f"shot_prompts[{idx}].dependencies.reference_images must be a list")

    transitions = data.get("transition_prompts")
    if isinstance(transitions, list):
        seen_transitions: set[str] = set()
        for idx, item in enumerate(transitions):
            if not isinstance(item, dict):
                errors.append(f"transition_prompts[{idx}] must be an object")
                continue
            for key in REQUIRED_TRANSITION:
                if key not in item:
                    errors.append(f"transition_prompts[{idx}] missing field: {key}")
            tid = item.get("transition_id")
            if not isinstance(tid, str) or not TRANSITION_ID_RE.match(tid):
                errors.append(f"transition_prompts[{idx}].transition_id must look like T001")
            elif tid in seen_transitions:
                errors.append(f"duplicate transition_id: {tid}")
            else:
                seen_transitions.add(tid)
            for key in ["from_shot_id", "to_shot_id"]:
                val = item.get(key)
                if not isinstance(val, str) or not SHOT_ID_RE.match(val):
                    errors.append(f"transition_prompts[{idx}].{key} must look like S001")
                elif shot_ids and val not in shot_ids:
                    errors.append(f"transition_prompts[{idx}].{key} references unknown shot_id: {val}")
            for key in ["transition_type", "transition_motion_prompt"]:
                if is_blank(item.get(key)):
                    errors.append(f"transition_prompts[{idx}].{key} must not be blank in final mode")
            reqs = item.get("continuity_requirements")
            if not isinstance(reqs, list) or not reqs or any(is_blank(x) for x in reqs):
                errors.append(f"transition_prompts[{idx}].continuity_requirements must be a non-empty list of strings")

    if is_blank(data.get("global_negative_prompt")):
        errors.append("global_negative_prompt must not be blank in final mode")
    self_check = data.get("self_check")
    if isinstance(self_check, dict):
        for key in ["matches_locked_brief", "matches_script", "matches_storyboard", "uses_character_consistency", "covers_all_storyboard_shots", "ready_for_image_generation"]:
            if self_check.get(key) is not True:
                errors.append(f"self_check.{key} must be true in final mode")
        for key in ["character_reference_images_ready", "safe_for_auto_image_generation"]:
            value = self_check.get(key)
            if value is not None and not isinstance(value, bool):
                errors.append(f"self_check.{key} must be a boolean when present")
    reference_image_status = data.get("reference_image_status")
    if isinstance(reference_image_status, dict):
        for key in ["required", "all_present"]:
            if key in reference_image_status and not isinstance(reference_image_status.get(key), bool):
                errors.append(f"reference_image_status.{key} must be a boolean when present")
        for key in ["target_paths", "existing_paths", "missing_paths", "items"]:
            if key in reference_image_status and not isinstance(reference_image_status.get(key), list):
                errors.append(f"reference_image_status.{key} must be a list when present")
    stage05_execution_readiness = data.get("stage05_execution_readiness")
    if isinstance(stage05_execution_readiness, dict):
        if "safe_to_auto_generate" in stage05_execution_readiness and not isinstance(stage05_execution_readiness.get("safe_to_auto_generate"), bool):
            errors.append("stage05_execution_readiness.safe_to_auto_generate must be a boolean when present")
        for key in ["blocker_reasons", "missing_reference_images"]:
            if key in stage05_execution_readiness and not isinstance(stage05_execution_readiness.get(key), list):
                errors.append(f"stage05_execution_readiness.{key} must be a list when present")
    return not errors, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("keyframe_prompts_json")
    parser.add_argument("--mode", choices=["draft", "final"], default="final")
    args = parser.parse_args(argv)
    data = load_json(Path(args.keyframe_prompts_json))
    ok, errors, warnings = validate(data, args.mode)
    if warnings:
        print("KEYFRAME PROMPTS VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"KEYFRAME PROMPTS VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"KEYFRAME PROMPTS VALIDATION PASSED ({args.mode} mode): {args.keyframe_prompts_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
