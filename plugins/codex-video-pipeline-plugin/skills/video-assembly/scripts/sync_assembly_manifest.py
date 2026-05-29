#!/usr/bin/env python3
"""Sync Stage 08 final rough-cut output evidence into assembly_manifest.json."""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402


def resolve_path(base_json: Path, raw: str) -> Path:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    out = resolve_path(path, data.get("final_output_path") or data.get("evidence", {}).get("file_path") or "")
    mix_plan = resolve_path(path, data.get("audio_mix_plan_path") or "audio_mix_plan.json")
    edit_list = resolve_path(path, data.get("edit_decision_list_path") or "edit_decision_list.json")
    exists = out.exists() and out.is_file()
    size = out.stat().st_size if exists else 0
    data.setdefault("evidence", {})
    data["evidence"].update({
        "file_path": str(out).replace("\\", "/"),
        "file_exists": bool(exists),
        "file_size_bytes": size,
        "created_at": datetime.now(timezone.utc).isoformat() if exists else None
    })
    data.setdefault("self_check", {})
    data["self_check"].update({
        "has_timeline_from_confirmed_clips": bool(data.get("timeline")),
        "has_audio_mix_plan": mix_plan.exists(),
        "has_edit_decision_list": edit_list.exists(),
        "has_final_output_file": exists and size > 0,
        "ready_for_qa_stage": exists and size > 0,
    })
    if exists and size > 0:
        data["status"] = "generated"
        data["allowed_next_stage"] = next_stage_after("STAGE_08_ASSEMBLY", routing, "STAGE_09_QA")
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_08_ASSEMBLY_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"assembly_confirmed": True},
            status="active",
        )
    else:
        data["status"] = "in_progress"
        data["allowed_next_stage"] = None
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ASSEMBLY MANIFEST SYNCED: {path}")
    print(f"OUTPUT EXISTS: {exists}, SIZE: {size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
