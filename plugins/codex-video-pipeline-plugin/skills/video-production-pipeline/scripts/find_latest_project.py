#!/usr/bin/env python3
"""Find the latest video project folder under a root directory."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="video_projects")
    args = p.parse_args()
    root = Path(args.root)
    if not root.exists():
        print("NO_PROJECTS_FOUND")
        return 1
    candidates = []
    for d in root.iterdir():
        if d.is_dir() and (d / "project_manifest.json").exists():
            try:
                m = json.loads((d / "project_manifest.json").read_text(encoding="utf-8"))
                stamp = m.get("updated_at") or m.get("created_at") or ""
            except Exception:
                stamp = ""
            candidates.append((stamp, d.stat().st_mtime, d))
    if not candidates:
        print("NO_PROJECTS_FOUND")
        return 1
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    print(str(candidates[0][2]).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
