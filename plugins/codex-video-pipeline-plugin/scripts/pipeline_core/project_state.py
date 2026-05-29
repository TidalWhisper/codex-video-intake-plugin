from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def load_json_file(path: Path, *, allow_bom: bool = True) -> dict[str, Any]:
    encoding = "utf-8-sig" if allow_bom else "utf-8"
    return json.loads(path.read_text(encoding=encoding))


def write_json_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_project_manifest(start: Path) -> Path | None:
    anchor = start if start.is_dir() else start.parent
    for directory in [anchor, *anchor.parents]:
        candidate = directory / "project_manifest.json"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def update_project_manifest_for_stage(
    source_path: Path,
    *,
    current_stage: str,
    allowed_next_stage: str | None,
    flags: dict[str, bool] | None = None,
    status: str | None = None,
) -> Path | None:
    manifest_path = find_project_manifest(source_path)
    if manifest_path is None:
        return None

    try:
        data = load_json_file(manifest_path)
    except Exception:
        return None

    project_dir = manifest_path.parent
    data.setdefault("project_id", project_dir.name)
    data.setdefault("project_dir", as_posix(project_dir))
    data["current_stage"] = current_stage
    data["allowed_next_stage"] = allowed_next_stage
    data["updated_at"] = utc_now()
    if status is not None:
        data["status"] = status
    for key, value in (flags or {}).items():
        data[key] = bool(value)

    write_json_file(manifest_path, data)
    return manifest_path
