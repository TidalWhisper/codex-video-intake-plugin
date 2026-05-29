#!/usr/bin/env python3
"""Validate Stage 08 assembly manifest.

Final mode requires the rough-cut output file to exist and have non-zero size, and verifies that source clip/audio evidence is present in the manifest.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

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

REQUIRED_TOP = [
    "schema_version", "stage", "status", "project_id", "source_brief", "source_storyboard",
    "source_video_clip_manifest", "source_audio_manifest", "assembly_provider_strategy",
    "output_root", "rough_cut_dir", "temp_dir", "concat_list_path", "edit_decision_list_path",
    "audio_mix_plan_path", "subtitle_path", "final_output_path", "timeline", "audio_tracks",
    "subtitle_tracks", "ffmpeg_commands", "evidence", "summary", "self_check", "allowed_next_stage"
]
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def resolve_path(base_json: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    p = Path(raw)
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


def validate(data: dict[str, Any], path: Path | None = None, mode: str = "final") -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = path or Path("assembly_manifest.json")

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_08_ASSEMBLY":
        errors.append("stage must be STAGE_08_ASSEMBLY")
    if data.get("status") not in {"draft", "in_progress", "generated", "confirmed"}:
        errors.append("status must be draft, in_progress, generated, or confirmed")
    if is_blank(data.get("project_id")):
        errors.append("project_id must not be blank")
    if not isinstance(data.get("timeline"), list):
        errors.append("timeline must be a list")
        timeline: list[Any] = []
    else:
        timeline = data.get("timeline") or []
    if mode == "final" and not timeline:
        errors.append("timeline must not be empty in final mode")

    timeline_duration = 0.0
    for idx, item in enumerate(timeline):
        if not isinstance(item, dict):
            errors.append(f"timeline[{idx}] must be an object")
            continue
        for key in ["shot_id", "clip_path", "start_sec", "duration_sec", "source_clip_id"]:
            if key not in item:
                errors.append(f"timeline[{idx}] missing key: {key}")
        try:
            duration = float(item.get("duration_sec") or 0)
        except Exception:
            errors.append(f"timeline[{idx}].duration_sec must be numeric")
            duration = 0
        if mode == "final" and duration <= 0:
            errors.append(f"timeline[{idx}].duration_sec must be positive in final mode")
        timeline_duration += max(duration, 0)
        if mode == "final":
            clip_path = resolve_path(manifest_path, item.get("clip_path"))
            if clip_path is None:
                errors.append(f"timeline[{idx}].clip_path must not be blank")
            elif not clip_path.exists() or not clip_path.is_file() or clip_path.stat().st_size <= 0:
                errors.append(f"timeline[{idx}] clip file missing or empty: {clip_path}")

    audio_tracks = data.get("audio_tracks") if isinstance(data.get("audio_tracks"), list) else []
    if not isinstance(data.get("audio_tracks"), list):
        errors.append("audio_tracks must be a list")
    for idx, item in enumerate(audio_tracks):
        if not isinstance(item, dict):
            errors.append(f"audio_tracks[{idx}] must be an object")
            continue
        for key in ["audio_id", "audio_type", "audio_path", "start_sec", "duration_sec", "source_audio_id"]:
            if key not in item:
                errors.append(f"audio_tracks[{idx}] missing key: {key}")
        if mode == "final":
            audio_path = resolve_path(manifest_path, item.get("audio_path"))
            if audio_path is None:
                errors.append(f"audio_tracks[{idx}].audio_path must not be blank")
            elif not audio_path.exists() or not audio_path.is_file() or audio_path.stat().st_size <= 0:
                errors.append(f"audio_tracks[{idx}] audio file missing or empty: {audio_path}")

    if mode == "final":
        ffmpeg_commands = data.get("ffmpeg_commands")
        if not isinstance(ffmpeg_commands, list) or not ffmpeg_commands:
            errors.append("ffmpeg_commands must be a non-empty list in final mode")
        else:
            for idx, item in enumerate(ffmpeg_commands):
                if not isinstance(item, dict):
                    errors.append(f"ffmpeg_commands[{idx}] must be an object")
                    continue
                command = item.get("command")
                if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
                    errors.append(f"ffmpeg_commands[{idx}].command must be a non-empty list of strings")
                if not isinstance(item.get("return_code"), int):
                    errors.append(f"ffmpeg_commands[{idx}].return_code must be an integer")
                if is_blank(item.get("strategy")):
                    errors.append(f"ffmpeg_commands[{idx}].strategy must not be blank")
                if is_blank(item.get("provider")):
                    errors.append(f"ffmpeg_commands[{idx}].provider must not be blank")
                if is_blank(item.get("ran_at")):
                    errors.append(f"ffmpeg_commands[{idx}].ran_at must not be blank")
        for key in ["concat_list_path", "edit_decision_list_path", "audio_mix_plan_path", "subtitle_path"]:
            p = resolve_path(manifest_path, data.get(key))
            if p is None:
                errors.append(f"{key} must not be blank")
            elif not p.exists() or not p.is_file():
                errors.append(f"{key} file does not exist: {p}")
        final_path = resolve_path(manifest_path, data.get("final_output_path"))
        if final_path is None:
            errors.append("final_output_path must not be blank")
        else:
            if final_path.suffix.lower() not in VIDEO_EXTS:
                errors.append(f"final output extension must be one of {sorted(VIDEO_EXTS)}: {final_path}")
            if not final_path.exists():
                errors.append(f"final output file does not exist: {final_path}")
            elif not final_path.is_file():
                errors.append(f"final output path is not a file: {final_path}")
            elif final_path.stat().st_size <= 0:
                errors.append(f"final output file is empty: {final_path}")
        evidence = data.get("evidence")
        if not isinstance(evidence, dict):
            errors.append("evidence must be an object")
        else:
            if evidence.get("file_exists") is not True:
                errors.append("evidence.file_exists must be true in final mode")
            if not isinstance(evidence.get("file_size_bytes"), int) or evidence.get("file_size_bytes") <= 0:
                errors.append("evidence.file_size_bytes must be a positive integer in final mode")
        summary = data.get("summary")
        if isinstance(summary, dict):
            if summary.get("timeline_clip_count") != len(timeline):
                errors.append("summary.timeline_clip_count must equal len(timeline)")
            if summary.get("audio_track_count") != len(audio_tracks):
                errors.append("summary.audio_track_count must equal len(audio_tracks)")
            try:
                stated = float(summary.get("rough_cut_duration_sec") or 0)
            except Exception:
                errors.append("summary.rough_cut_duration_sec must be numeric")
                stated = 0
            if timeline and abs(stated - timeline_duration) > 0.1:
                errors.append("summary.rough_cut_duration_sec must equal sum of timeline duration_sec")
        self_check = data.get("self_check")
        if isinstance(self_check, dict):
            for key in ["has_timeline_from_confirmed_clips", "has_audio_mix_plan", "has_edit_decision_list", "has_final_output_file", "ready_for_qa_stage"]:
                if self_check.get(key) is not True:
                    errors.append(f"self_check.{key} must be true in final mode")
        quality_signals = data.get("quality_signals")
        if not isinstance(quality_signals, dict):
            errors.append("quality_signals must be an object in final mode")
        else:
            for key in ["intent_route_matches_strategy", "timeline_matches_storyboard_order", "audio_tracks_match_strategy", "quality_targets_defined"]:
                if quality_signals.get(key) is not True:
                    errors.append(f"quality_signals.{key} must be true in final mode")

    if mode == "draft":
        warnings.append("draft assembly manifest still requires FFmpeg output evidence before final validation")
    return not errors, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--mode", choices=["draft", "final"], default="final")
    args = parser.parse_args(argv)
    path = Path(args.manifest_json)
    data = load_json(path)
    ok, errors, warnings = validate(data, path, args.mode)
    if warnings:
        print("ASSEMBLY MANIFEST VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"ASSEMBLY MANIFEST VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"ASSEMBLY MANIFEST VALIDATION PASSED ({args.mode} mode): {args.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
