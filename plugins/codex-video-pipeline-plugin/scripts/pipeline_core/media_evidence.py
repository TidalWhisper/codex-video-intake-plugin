from __future__ import annotations

from pathlib import Path
from typing import Any


# Small placeholder files in this repo's examples are typically ~100 bytes.
# Keep the threshold just above that so obviously fake rough cuts are rejected,
# while template/test assets that simulate a minimal playable output can pass.
MIN_PRODUCTION_VIDEO_BYTES = 128
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}


def provider_is_nonproduction(provider: Any) -> bool:
    return str(provider or "").strip().lower().startswith("placeholder_test_")


def file_is_nontrivial_video(path: Path | None, *, min_bytes: int = MIN_PRODUCTION_VIDEO_BYTES) -> bool:
    if path is None or not path.exists() or not path.is_file():
        return False
    if path.suffix.lower() not in VIDEO_EXTS:
        return False
    return path.stat().st_size >= int(min_bytes)


def clip_output_ready(
    output_path: Path | None,
    provider: Any = None,
    *,
    min_bytes: int = MIN_PRODUCTION_VIDEO_BYTES,
) -> bool:
    if provider_is_nonproduction(provider):
        return False
    return file_is_nontrivial_video(output_path, min_bytes=min_bytes)


def assembly_output_ready(data: dict[str, Any], output_path: Path | None, *, min_bytes: int = MIN_PRODUCTION_VIDEO_BYTES) -> bool:
    if provider_is_nonproduction(data.get("assembly_provider")):
        return False
    if not file_is_nontrivial_video(output_path, min_bytes=min_bytes):
        return False
    commands = data.get("ffmpeg_commands") if isinstance(data.get("ffmpeg_commands"), list) else []
    for item in commands:
        if not isinstance(item, dict):
            continue
        if provider_is_nonproduction(item.get("provider")) or str(item.get("strategy") or "").strip().lower() == "placeholder_test":
            return False
    return True
