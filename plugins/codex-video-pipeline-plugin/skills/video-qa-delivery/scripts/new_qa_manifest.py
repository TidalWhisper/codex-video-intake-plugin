#!/usr/bin/env python3
"""Create Stage 09 QA/delivery manifest from a locked brief and Stage 08 assembly manifest.

Usage:
  python new_qa_manifest.py <locked_brief.json> <assembly_manifest.json> <qa_manifest.json>
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.quality_contracts import build_quality_contract, build_qa_checks  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage  # noqa: E402

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
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


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


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 4:
        print("Usage: python new_qa_manifest.py <locked_brief.json> <assembly_manifest.json> <qa_manifest.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    assembly_path = Path(argv[2])
    out_path = Path(argv[3])

    brief = load_json(brief_path)
    assembly = load_json(assembly_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_09", compiled):
        print("ERROR: requested output scope does not allow Stage 09. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if assembly.get("stage") != "STAGE_08_ASSEMBLY":
        print("ERROR: assembly_manifest.stage must be STAGE_08_ASSEMBLY", file=sys.stderr)
        return 1
    if not (assembly.get("self_check") or {}).get("ready_for_qa_stage"):
        print("ERROR: assembly_manifest must be ready_for_qa_stage=true before Stage 09", file=sys.stderr)
        return 1

    final_video = resolve_path(assembly_path, assembly.get("final_output_path") or (assembly.get("evidence") or {}).get("file_path"))
    if final_video is None:
        print("ERROR: assembly final video path is missing", file=sys.stderr)
        return 1

    project_id = brief.get("project_id") or assembly.get("project_id") or out_path.parents[1].name
    qa_dir = out_path.parent
    delivery_dir = qa_dir / "final_delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    routing = routing_from_brief(brief)
    quality_contract = build_quality_contract(brief, compiled)

    qa_plan = qa_dir / "qa_plan.md"
    qa_checklist = qa_dir / "qa_checklist.json"
    issue_report = qa_dir / "issue_report.md"
    delivery_report = qa_dir / "delivery_report.md"
    delivery_manifest = qa_dir / "delivery_manifest.json"
    asset_index = qa_dir / "asset_index.json"
    qa_review = qa_dir / "qa_review.md"

    checks = build_qa_checks(brief, compiled, quality_contract)

    qa_plan.write_text(f"# Stage 09 QA 计划\n\n- 项目：{project_id}\n- 输入粗剪：{rel(final_video)}\n- 目标：检查粗剪证据、归档交付包、生成问题清单和交付说明。\n", encoding="utf-8")
    write_json(qa_checklist, {"project_id": project_id, "checks": checks})
    issue_report.write_text("# Stage 09 问题清单\n\n当前为草稿状态，尚未完成最终 QA。\n", encoding="utf-8")
    delivery_report.write_text(f"# Stage 09 交付报告\n\n项目：{project_id}\n\n待生成最终交付包。\n", encoding="utf-8")
    write_json(delivery_manifest, {"project_id": project_id, "status": "draft", "files": []})
    write_json(asset_index, {"project_id": project_id, "assets": []})
    qa_review.write_text("# Stage 09 QA Review\n\n待 QA 和交付包确认。\n", encoding="utf-8")

    manifest = {
        "schema_version": "1.0.0",
        "stage": "STAGE_09_QA",
        "status": "draft",
        "project_id": project_id,
        "source_brief": rel(brief_path),
        "source_assembly_manifest": rel(assembly_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "routing": routing,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "qa_root": rel(qa_dir),
        "final_video_path": rel(final_video),
        "qa_plan_path": rel(qa_plan),
        "qa_checklist_path": rel(qa_checklist),
        "issue_report_path": rel(issue_report),
        "delivery_report_path": rel(delivery_report),
        "delivery_manifest_path": rel(delivery_manifest),
        "asset_index_path": rel(asset_index),
        "qa_review_path": rel(qa_review),
        "qa_checks": checks,
        "content_alignment_review": {
            "confirmed": False,
            "status": "pending",
            "note": "",
            "reviewed_at": None,
        },
        "issue_summary": {"blocker_count": 0, "major_count": 0, "minor_count": 0, "notes": ["draft QA manifest; run package_delivery.py before final validation"]},
        "delivery_package": {"root": rel(delivery_dir), "files": [], "ready": False},
        "self_check": {
            "final_video_exists": final_video.exists() and final_video.is_file() and final_video.stat().st_size > 0,
            "qa_checks_complete": False,
            "no_blocking_issues": False,
            "delivery_package_ready": False,
            "project_complete_ready": False,
        },
        "allowed_next_stage": None,
        "errors": []
    }
    write_json(out_path, manifest)
    print(f"QA MANIFEST CREATED: {out_path}")
    print(f"FINAL VIDEO SOURCE: {final_video}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
