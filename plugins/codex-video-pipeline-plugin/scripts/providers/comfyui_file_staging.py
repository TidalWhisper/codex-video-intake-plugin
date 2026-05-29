#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path

from comfyui_client import ComfyUIError


def stage_input_file(source_path: Path, input_dir: str | Path | None, *, stem_prefix: str) -> str:
    if input_dir is None or not str(input_dir).strip():
        raise ComfyUIError("comfyui.input_dir is not configured", kind="input_dir_missing")

    src = Path(source_path)
    if not src.exists() or not src.is_file():
        raise ComfyUIError(f"input file does not exist: {src}", kind="input_missing")
    if src.stat().st_size <= 0:
        raise ComfyUIError(f"input file is empty: {src}", kind="input_missing")

    dst_root = Path(input_dir)
    dst_root.mkdir(parents=True, exist_ok=True)
    suffix = src.suffix or ".bin"
    safe_stem = src.stem.replace(" ", "_")
    target_name = f"{stem_prefix}_{safe_stem}{suffix}"
    target_path = dst_root / target_name
    shutil.copyfile(src, target_path)
    return target_name
