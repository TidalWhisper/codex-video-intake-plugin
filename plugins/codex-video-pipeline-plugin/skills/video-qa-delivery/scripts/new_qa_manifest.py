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
    return (base_json.parent / p).resolve()


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
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

    qa_plan = qa_dir / "qa_plan.md"
    qa_checklist = qa_dir / "qa_checklist.json"
    issue_report = qa_dir / "issue_report.md"
    delivery_report = qa_dir / "delivery_report.md"
    delivery_manifest = qa_dir / "delivery_manifest.json"
    asset_index = qa_dir / "asset_index.json"
    qa_review = qa_dir / "qa_review.md"

    checks = [
        {"check_id": "final_video_evidence", "category": "file_evidence", "description": "最终粗剪视频文件存在且非空", "status": "pending", "severity": "blocker"},
        {"check_id": "duration_consistency", "category": "timeline", "description": "粗剪时长与分镜/片段时长基本一致", "status": "pending", "severity": "major"},
        {"check_id": "storyboard_coverage", "category": "story", "description": "所有关键分镜均在粗剪时间线中出现", "status": "pending", "severity": "major"},
        {"check_id": "audio_presence", "category": "audio", "description": "需要配音/音乐时音频轨已纳入交付说明", "status": "pending", "severity": "major"},
        {"check_id": "subtitle_package", "category": "subtitle", "description": "字幕文件或字幕说明已归档", "status": "pending", "severity": "minor"},
        {"check_id": "delivery_package", "category": "delivery", "description": "最终交付包文件齐全", "status": "pending", "severity": "blocker"},
    ]

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
