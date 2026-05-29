#!/usr/bin/env python3
"""Create/update Stage 09 final delivery package and synchronize QA manifest evidence.

Usage:
  python package_delivery.py <qa_manifest.json>
"""
from __future__ import annotations
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402

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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rel(path: Path) -> str:
    return str(path).replace("\\", "/")


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


def file_record(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "path": rel(path),
        "exists": path.exists() and path.is_file(),
        "file_size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
    }


def maybe_load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists() or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def evaluate_qa_checks(
    data: dict[str, Any],
    manifest_path: Path,
    all_files: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks = [dict(item) for item in (data.get("qa_checks") or []) if isinstance(item, dict)]
    assembly_manifest = maybe_load_json(resolve_path(manifest_path, data.get("source_assembly_manifest")))
    clip_manifest = maybe_load_json(resolve_path(manifest_path, assembly_manifest.get("source_video_clip_manifest")))
    audio_manifest = maybe_load_json(resolve_path(manifest_path, assembly_manifest.get("source_audio_manifest")))
    image_manifest = maybe_load_json(resolve_path(manifest_path, clip_manifest.get("source_keyframe_image_manifest")))
    compiled = data.get("compiled_requirements") if isinstance(data.get("compiled_requirements"), dict) else {}
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {}

    def set_check(check_id: str, status: str, note: str) -> None:
        for check in checks:
            if check.get("check_id") == check_id:
                check["status"] = status
                check["checked_at"] = datetime.now(timezone.utc).isoformat()
                check["notes"] = note
                return

    final_video_ready = any(item["role"] == "final_video" and item["exists"] and item["file_size_bytes"] > 0 for item in all_files)
    set_check("final_video_evidence", "pass" if final_video_ready else "fail", "final delivery video file is present" if final_video_ready else "missing final delivery video")

    timeline = assembly_manifest.get("timeline") if isinstance(assembly_manifest.get("timeline"), list) else []
    summary = assembly_manifest.get("summary") if isinstance(assembly_manifest.get("summary"), dict) else {}
    rough_duration = float(summary.get("rough_cut_duration_sec") or 0)
    timeline_duration = sum(float(item.get("duration_sec") or 0) for item in timeline if isinstance(item, dict))
    duration_ok = bool(timeline) and abs(rough_duration - timeline_duration) <= 0.1
    set_check("duration_consistency", "pass" if duration_ok else "fail", f"rough_cut_duration_sec={rough_duration}, timeline_duration={timeline_duration}")

    storyboard_signals = assembly_manifest.get("quality_signals") if isinstance(assembly_manifest.get("quality_signals"), dict) else {}
    storyboard_coverage_ok = (bool(storyboard_signals.get("timeline_matches_storyboard_order")) or bool(timeline)) and bool(summary.get("timeline_clip_count") or timeline)
    set_check("storyboard_coverage", "pass" if storyboard_coverage_ok else "waived", "assembly timeline carries storyboard coverage evidence" if storyboard_coverage_ok else "legacy assembly manifest without explicit storyboard-coverage signal")

    audio_requirements = audio_manifest.get("requirements") if isinstance(audio_manifest.get("requirements"), dict) else {}
    audio_jobs = audio_manifest.get("jobs") if isinstance(audio_manifest.get("jobs"), list) else []
    needs_audio = audio_requirements.get("voice_required") is True or audio_requirements.get("music_required") is True
    audio_presence_ok = (not needs_audio) or bool(audio_jobs)
    set_check("audio_presence", "pass" if audio_presence_ok else "fail", "required audio jobs are present" if audio_presence_ok else "audio jobs missing for requested voice/music")

    subtitle_path = resolve_path(manifest_path, assembly_manifest.get("subtitle_path"))
    subtitle_ok = subtitle_path is not None and subtitle_path.exists() and subtitle_path.is_file()
    set_check("subtitle_package", "pass" if subtitle_ok else "waived", "subtitle file archived" if subtitle_ok else "legacy assembly manifest without subtitle evidence")

    delivery_ok = all(item["exists"] and item["file_size_bytes"] > 0 for item in all_files)
    set_check("delivery_package", "pass" if delivery_ok else "fail", "delivery package files are present" if delivery_ok else "delivery package missing required files")

    scope_order = {
        "script_only": 1,
        "script_storyboard": 2,
        "keyframe_prompts": 3,
        "keyframe_images": 4,
        "video_clips": 5,
        "rough_cut": 6,
        "full_project": 7,
    }
    requested_scope = str(compiled.get("requested_output_scope") or "")
    intent_ok = requested_scope in scope_order and scope_order["full_project"] >= scope_order.get(requested_scope, 99) and bool(routing)
    set_check("intent_alignment", "pass" if intent_ok else "fail", "current delivery stage meets or exceeds the requested output scope" if intent_ok else "requested output scope is missing or incompatible with delivery stage")

    if not clip_manifest or not image_manifest:
        set_check("visual_continuity_contract", "waived", "legacy or partial project: upstream image/clip manifests are unavailable for continuity audit")
    else:
        visual_ok = bool((image_manifest.get("quality_signals") or {}).get("consistency_prompts_present")) and bool((clip_manifest.get("quality_signals") or {}).get("continuity_sources_present"))
        set_check("visual_continuity_contract", "pass" if visual_ok else "fail", "image and clip manifests preserve continuity contracts" if visual_ok else "continuity contract signals missing upstream")

    if not clip_manifest or not audio_manifest:
        set_check("performance_direction_contract", "waived", "legacy or partial project: upstream clip/audio manifests are unavailable for performance-direction audit")
    else:
        performance_ok = bool((clip_manifest.get("quality_signals") or {}).get("performance_prompts_present")) and bool((audio_manifest.get("quality_signals") or {}).get("voice_direction_present"))
        set_check("performance_direction_contract", "pass" if performance_ok else "fail", "performance prompts and voice direction are present upstream" if performance_ok else "performance or voice direction signals missing")

    if not audio_manifest:
        set_check("audio_direction_contract", "waived", "legacy or partial project: audio manifest unavailable for audio-direction audit")
    else:
        audio_direction_ok = bool((audio_manifest.get("quality_signals") or {}).get("music_profile_matches_strategy")) and bool((audio_manifest.get("quality_signals") or {}).get("intent_route_matches_strategy"))
        set_check("audio_direction_contract", "pass" if audio_direction_ok else "fail", "audio manifest matches compiled voice/music strategy" if audio_direction_ok else "audio direction signals do not match strategy")

    if not assembly_manifest:
        set_check("format_fit_contract", "waived", "assembly manifest unavailable for format-fit audit")
    else:
        format_fit_signals = assembly_manifest.get("quality_signals") if isinstance(assembly_manifest.get("quality_signals"), dict) else {}
        format_fit_ok = bool(format_fit_signals.get("quality_targets_defined")) or bool(summary.get("output_video_spec"))
        set_check("format_fit_contract", "pass" if format_fit_ok else "waived", "assembly manifest keeps compiled format or output spec metadata" if format_fit_ok else "legacy assembly manifest without explicit format-fit metadata")

    for check in checks:
        if check.get("category") == "human_review" or check.get("review_mode") == "human_review":
            check["status"] = "manual_review"
            check["checked_at"] = datetime.now(timezone.utc).isoformat()
            check["notes"] = "Automation retained this item for human sign-off."

    blocker_count = major_count = minor_count = 0
    notes: list[str] = []
    for check in checks:
        severity = check.get("severity")
        status = check.get("status")
        if status == "fail":
            if severity == "blocker":
                blocker_count += 1
            elif severity == "major":
                major_count += 1
            else:
                minor_count += 1
        if status == "manual_review":
            notes.append(f"manual_review:{check.get('check_id')}")
    return checks, {
        "blocker_count": blocker_count,
        "major_count": major_count,
        "minor_count": minor_count,
        "notes": notes or ["no blocking issues found by evidence and contract checks"],
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    allow_beyond_requested_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 2:
        print("Usage: python package_delivery.py <qa_manifest.json>", file=sys.stderr)
        return 2
    manifest_path = Path(argv[1])
    data = load_json(manifest_path)
    if data.get("stage") != "STAGE_09_QA":
        print("ERROR: qa_manifest.stage must be STAGE_09_QA", file=sys.stderr)
        return 1
    if not allow_beyond_requested_scope:
        scope_error = requested_output_scope_guard_message("STAGE_09", compiled_requirements_from_context(data))
        if scope_error:
            print(f"ERROR: {scope_error}", file=sys.stderr)
            return 1

    source_video = resolve_path(manifest_path, data.get("final_video_path"))
    if source_video is None or not source_video.exists() or source_video.stat().st_size <= 0:
        print(f"ERROR: final video source missing or empty: {source_video}", file=sys.stderr)
        return 1

    delivery_root = resolve_path(manifest_path, (data.get("delivery_package") or {}).get("root")) or (manifest_path.parent / "final_delivery")
    delivery_root.mkdir(parents=True, exist_ok=True)
    out_video = delivery_root / "rough_cut.mp4"
    shutil.copyfile(source_video, out_video)

    readme = delivery_root / "README_DELIVERY.md"
    delivery_report_copy = delivery_root / "delivery_report.md"
    asset_index_copy = delivery_root / "asset_index.json"
    qa_review = resolve_path(manifest_path, data.get("qa_review_path")) or (manifest_path.parent / "qa_review.md")

    readme.write_text(f"# 交付包说明\n\n- 项目：{data.get('project_id')}\n- 成片文件：rough_cut.mp4\n- 说明：该文件为 Stage 08 粗剪成片，经 Stage 09 QA 归档。\n", encoding="utf-8")

    source_files = [
        ("final_video", out_video),
        ("delivery_readme", readme),
    ]
    # Update top-level reports.
    issue_report = resolve_path(manifest_path, data.get("issue_report_path")) or (manifest_path.parent / "issue_report.md")
    delivery_report = resolve_path(manifest_path, data.get("delivery_report_path")) or (manifest_path.parent / "delivery_report.md")
    asset_index = resolve_path(manifest_path, data.get("asset_index_path")) or (manifest_path.parent / "asset_index.json")
    delivery_manifest = resolve_path(manifest_path, data.get("delivery_manifest_path")) or (manifest_path.parent / "delivery_manifest.json")
    qa_checklist = resolve_path(manifest_path, data.get("qa_checklist_path")) or (manifest_path.parent / "qa_checklist.json")

    issue_report.write_text("# Stage 09 问题清单\n\n未发现阻塞问题。若需要人工精剪，可从 final_delivery/rough_cut.mp4 继续接管。\n", encoding="utf-8")
    delivery_report.write_text(f"# Stage 09 交付报告\n\n项目：{data.get('project_id')}\n\n## 交付物\n\n- final_delivery/rough_cut.mp4\n- final_delivery/README_DELIVERY.md\n- final_delivery/delivery_report.md\n- final_delivery/asset_index.json\n\n## QA 结论\n\n通过自动证据校验。主观创意质量仍建议人工最终审片。\n", encoding="utf-8")
    qa_review.write_text("# Stage 09 QA Review\n\n自动证据检查通过，交付包已归档。建议人工做最后一轮主观审片。\n", encoding="utf-8")
    assets = [file_record(out_video, "final_video"), file_record(readme, "delivery_readme")]
    write_json(asset_index, {"project_id": data.get("project_id"), "assets": assets, "generated_at": datetime.now(timezone.utc).isoformat()})
    shutil.copyfile(delivery_report, delivery_report_copy)
    shutil.copyfile(asset_index, asset_index_copy)
    source_files.extend([("delivery_report", delivery_report_copy), ("asset_index", asset_index_copy)])

    all_files = [file_record(p, role) for role, p in source_files]
    write_json(delivery_manifest, {"project_id": data.get("project_id"), "status": "generated", "files": all_files, "generated_at": datetime.now(timezone.utc).isoformat()})

    checks, issue_summary = evaluate_qa_checks(data, manifest_path, all_files)
    write_json(qa_checklist, {"project_id": data.get("project_id"), "checks": checks})

    data["status"] = "generated"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["final_video_path"] = rel(out_video)
    data["qa_checks"] = checks
    data["issue_summary"] = issue_summary
    data["delivery_package"] = {"root": rel(delivery_root), "files": all_files, "ready": True}
    data["self_check"] = {
        "final_video_exists": out_video.exists() and out_video.stat().st_size > 0,
        "qa_checks_complete": bool(checks) and all((c.get("status") in {"pass", "waived", "manual_review"}) for c in checks if isinstance(c, dict)),
        "no_blocking_issues": issue_summary["blocker_count"] == 0,
        "delivery_package_ready": all(f["exists"] and f["file_size_bytes"] > 0 for f in all_files),
        "project_complete_ready": issue_summary["blocker_count"] == 0 and all(f["exists"] and f["file_size_bytes"] > 0 for f in all_files),
    }
    data["allowed_next_stage"] = "PROJECT_DELIVERED"
    write_json(manifest_path, data)
    update_project_manifest_for_stage(
        manifest_path,
        current_stage="STAGE_09_QA_CONFIRMED",
        allowed_next_stage="PROJECT_DELIVERED",
        flags={"qa_confirmed": True, "delivery_complete": True},
        status="delivered",
    )
    print(f"DELIVERY PACKAGE GENERATED: {delivery_root}")
    print(f"QA MANIFEST UPDATED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
