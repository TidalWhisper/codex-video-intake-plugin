#!/usr/bin/env python3
"""Sync Stage 08 final rough-cut output evidence into assembly_manifest.json."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def resolve_path(base_json: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p
    return (base_json.parent / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    out = resolve_path(path, data.get("final_output_path") or data.get("evidence", {}).get("file_path") or "")
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
        "has_final_output_file": exists and size > 0,
        "ready_for_qa_stage": exists and size > 0,
    })
    if exists and size > 0:
        data["status"] = "generated"
        data["allowed_next_stage"] = "STAGE_09_QA"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ASSEMBLY MANIFEST SYNCED: {path}")
    print(f"OUTPUT EXISTS: {exists}, SIZE: {size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
