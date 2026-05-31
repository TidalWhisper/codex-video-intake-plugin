#!/usr/bin/env python3
"""Sync and show the creator-facing home entry for a video project."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline_core.project_state import load_json_file, sync_project_manifest_truth  # noqa: E402


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
    parser.add_argument("--root", default="video_projects", help="Root directory used when no project is explicitly provided")
    parser.add_argument("--project-dir", default=None, help="Specific project directory to inspect")
    parser.add_argument("--manifest", default=None, help="Explicit project_manifest.json path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = _resolve_manifest(args)
    if manifest_path is None or not manifest_path.exists():
        print("NO_PROJECT_FOUND")
        return 1

    synced = sync_project_manifest_truth(manifest_path)
    if synced is None:
        print(f"ERROR: unable to sync manifest: {manifest_path}")
        return 1
    data = load_json_file(synced)
    project_dir = synced.parent
    overview = data.get("creator_status_overview") if isinstance(data.get("creator_status_overview"), dict) else {}
    recommended_entry = overview.get("recommended_entry") if isinstance(overview.get("recommended_entry"), dict) else {}

    print(f"PROJECT_DIR: {str(project_dir).replace(chr(92), '/')}")
    print(f"CREATOR_HOME_HTML: {str((project_dir / 'creator_home.html').resolve()).replace(chr(92), '/')}")
    print(f"CREATOR_HOME_MD: {str((project_dir / 'creator_home.md').resolve()).replace(chr(92), '/')}")
    print(f"TRUSTED_STAGE: {overview.get('trusted_stage') or data.get('current_stage') or ''}")
    print(f"CURRENT_RESULT: {overview.get('current_result') or ''}")
    print(f"CURRENT_BLOCKER: {overview.get('current_blocker') or ''}")
    print(f"NEXT_ACTION: {overview.get('next_action') or ''}")
    print(f"RECOMMENDED_ENTRY_LABEL: {recommended_entry.get('label') or ''}")
    if recommended_entry.get("path"):
        print(f"RECOMMENDED_ENTRY_PATH: {recommended_entry.get('path')}")
    if recommended_entry.get("command"):
        print(f"RECOMMENDED_ENTRY_COMMAND: {recommended_entry.get('command')}")
    if recommended_entry.get("description"):
        print(f"RECOMMENDED_ENTRY_DESCRIPTION: {recommended_entry.get('description')}")
    print("CREATOR_HOME_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
