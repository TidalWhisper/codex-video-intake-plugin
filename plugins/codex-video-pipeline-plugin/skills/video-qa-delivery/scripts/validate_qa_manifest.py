#!/usr/bin/env python3
"""Validate Stage 09 QA/delivery manifest.

Final mode requires final delivery package evidence to exist and all blocking QA checks to pass or be waived.
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
    "schema_version", "stage", "status", "project_id", "source_brief", "source_assembly_manifest",
    "qa_root", "final_video_path", "qa_plan_path", "qa_checklist_path", "issue_report_path",
    "delivery_report_path", "delivery_manifest_path", "asset_index_path", "qa_review_path",
    "qa_checks", "issue_summary", "delivery_package", "self_check", "allowed_next_stage"
]
REQUIRED_CHECK_IDS = {
    "final_video_evidence", "duration_consistency", "storyboard_coverage", "audio_presence", "subtitle_package", "delivery_package",
    "intent_alignment", "visual_continuity_contract", "performance_direction_contract", "audio_direction_contract", "format_fit_contract",
}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


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
    manifest_path = path or Path("qa_manifest.json")

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if data.get("stage") != "STAGE_09_QA":
        errors.append("stage must be STAGE_09_QA")
    if data.get("status") not in {"draft", "in_progress", "generated", "confirmed"}:
        errors.append("status must be draft, in_progress, generated, or confirmed")
    if is_blank(data.get("project_id")):
        errors.append("project_id must not be blank")

    checks = data.get("qa_checks")
    if not isinstance(checks, list):
        errors.append("qa_checks must be a list")
        checks = []
    seen_ids = set()
    for idx, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"qa_checks[{idx}] must be an object")
            continue
        cid = check.get("check_id")
        if is_blank(cid):
            errors.append(f"qa_checks[{idx}].check_id must not be blank")
        else:
            seen_ids.add(cid)
        if check.get("status") not in {"pending", "pass", "fail", "waived", "manual_review"}:
            errors.append(f"qa_checks[{idx}].status must be pending, pass, fail, waived, or manual_review")
        if mode == "final":
            allowed_statuses = {"pass", "waived"}
            if check.get("category") == "human_review" or check.get("review_mode") == "human_review":
                allowed_statuses.add("manual_review")
            if check.get("status") not in allowed_statuses:
                errors.append(f"qa_checks[{idx}] must be one of {sorted(allowed_statuses)} in final mode: {cid}")
    if mode == "final" and not REQUIRED_CHECK_IDS.issubset(seen_ids):
        errors.append(f"qa_checks must include required check ids: {sorted(REQUIRED_CHECK_IDS - seen_ids)}")

    if mode == "final":
        final_video = resolve_path(manifest_path, data.get("final_video_path"))
        if final_video is None:
            errors.append("final_video_path must not be blank")
        else:
            if final_video.suffix.lower() not in VIDEO_EXTS:
                errors.append(f"final video extension must be one of {sorted(VIDEO_EXTS)}: {final_video}")
            if not final_video.exists() or not final_video.is_file() or final_video.stat().st_size <= 0:
                errors.append(f"final video file missing or empty: {final_video}")

        for key in ["qa_plan_path", "qa_checklist_path", "issue_report_path", "delivery_report_path", "delivery_manifest_path", "asset_index_path", "qa_review_path"]:
            p = resolve_path(manifest_path, data.get(key))
            if p is None:
                errors.append(f"{key} must not be blank")
            elif not p.exists() or not p.is_file() or p.stat().st_size <= 0:
                errors.append(f"{key} file missing or empty: {p}")

        issue_summary = data.get("issue_summary")
        if not isinstance(issue_summary, dict):
            errors.append("issue_summary must be an object")
        else:
            if int(issue_summary.get("blocker_count") or 0) > 0:
                errors.append("issue_summary.blocker_count must be 0 in final mode")

        package = data.get("delivery_package")
        if not isinstance(package, dict):
            errors.append("delivery_package must be an object")
        else:
            if package.get("ready") is not True:
                errors.append("delivery_package.ready must be true in final mode")
            root = resolve_path(manifest_path, package.get("root"))
            if root is None or not root.exists() or not root.is_dir():
                errors.append(f"delivery_package.root missing: {root}")
            files = package.get("files")
            if not isinstance(files, list) or not files:
                errors.append("delivery_package.files must not be empty in final mode")
            else:
                roles = set()
                for idx, f in enumerate(files):
                    if not isinstance(f, dict):
                        errors.append(f"delivery_package.files[{idx}] must be an object")
                        continue
                    roles.add(f.get("role"))
                    fp = resolve_path(manifest_path, f.get("path"))
                    if fp is None or not fp.exists() or not fp.is_file() or fp.stat().st_size <= 0:
                        errors.append(f"delivery_package.files[{idx}] missing or empty: {fp}")
                if "final_video" not in roles:
                    errors.append("delivery_package.files must include a final_video role")

        self_check = data.get("self_check")
        if not isinstance(self_check, dict):
            errors.append("self_check must be an object")
        else:
            for key in ["final_video_exists", "qa_checks_complete", "no_blocking_issues", "delivery_package_ready", "project_complete_ready"]:
                if self_check.get(key) is not True:
                    errors.append(f"self_check.{key} must be true in final mode")

    if mode == "draft":
        warnings.append("draft QA manifest still requires package_delivery.py and final evidence validation")
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
        print("QA MANIFEST VALIDATION WARNINGS:")
        for w in warnings:
            print(f"- {w}")
    if not ok:
        print(f"QA MANIFEST VALIDATION FAILED ({args.mode} mode):")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"QA MANIFEST VALIDATION PASSED ({args.mode} mode): {args.manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
