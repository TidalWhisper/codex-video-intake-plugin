#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from comfyui_client import ComfyUIError


TARGET_AUDIO_CODECS: dict[str, list[str]] = {
    ".wav": ["-c:a", "pcm_s16le"],
    ".flac": ["-c:a", "flac"],
    ".mp3": ["-c:a", "libmp3lame"],
    ".ogg": ["-c:a", "libvorbis"],
    ".m4a": ["-c:a", "aac"],
    ".aac": ["-c:a", "aac"],
}


def find_ffmpeg() -> str | None:
    configured = os.environ.get("FFMPEG_PATH", "").strip()
    if configured:
        candidate = Path(configured)
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg  # type: ignore

        candidate = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    except Exception:
        return None
    return None


def detect_audio_container(path: Path) -> str | None:
    try:
        header = path.read_bytes()[:16]
    except OSError:
        return None
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        return "wav"
    if header[:4] == b"fLaC":
        return "flac"
    if header[:4] == b"OggS":
        return "ogg"
    if header[:3] == b"ID3":
        return "mp3"
    if len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
        return "mp3_or_aac"
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "mp4_family"
    return None


def expected_container_for_suffix(path: Path) -> str | None:
    mapping = {
        ".wav": "wav",
        ".flac": "flac",
        ".mp3": "mp3",
        ".ogg": "ogg",
        ".m4a": "mp4_family",
        ".aac": "mp3_or_aac",
    }
    return mapping.get(path.suffix.lower())


def transcode_audio(source: Path, target: Path) -> None:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise ComfyUIError(
            f"Cannot normalize audio output to {target.suffix or 'target format'} because ffmpeg is not available",
            kind="audio_transcode_unavailable",
            details={"source": str(source), "target": str(target)},
        )
    codec_args = TARGET_AUDIO_CODECS.get(target.suffix.lower())
    if not codec_args:
        raise ComfyUIError(
            f"Unsupported target audio extension for normalization: {target.suffix}",
            kind="audio_transcode_unsupported",
            details={"source": str(source), "target": str(target)},
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vn",
            *codec_args,
            str(target),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if result.returncode != 0 or not target.exists() or target.stat().st_size <= 0:
        raise ComfyUIError(
            f"Failed to normalize audio output to {target.suffix}: {(result.stderr or result.stdout or 'ffmpeg failed').strip()}",
            kind="audio_transcode_failed",
            details={
                "source": str(source),
                "target": str(target),
                "return_code": result.returncode,
                "stdout": (result.stdout or "")[-2000:],
                "stderr": (result.stderr or "")[-2000:],
            },
        )


def materialize_audio_output(selected_output: dict[str, Any], target_path: Path) -> dict[str, Any]:
    resolved_path = selected_output.get("resolved_path")
    if not isinstance(resolved_path, str) or not resolved_path.strip():
        raise ComfyUIError("ComfyUI output did not resolve to a local file path", kind="output_missing", details=selected_output)
    source = Path(resolved_path)
    if not source.exists() or not source.is_file():
        raise ComfyUIError(f"ComfyUI output file does not exist: {source}", kind="output_missing", details=selected_output)
    if source.stat().st_size <= 0:
        raise ComfyUIError(f"ComfyUI output file is empty: {source}", kind="output_missing", details=selected_output)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    source_container = detect_audio_container(source)
    expected_target_container = expected_container_for_suffix(target_path)
    should_transcode = False
    if source.suffix.lower() != target_path.suffix.lower():
        should_transcode = True
    elif expected_target_container and source_container and source_container != expected_target_container:
        should_transcode = True

    if should_transcode:
        transcode_audio(source, target_path)
        return {
            "mode": "transcoded",
            "source_path": str(source).replace("\\", "/"),
            "source_container": source_container,
            "target_path": str(target_path).replace("\\", "/"),
            "target_container": detect_audio_container(target_path),
        }

    shutil.copyfile(source, target_path)
    return {
        "mode": "copied",
        "source_path": str(source).replace("\\", "/"),
        "source_container": source_container,
        "target_path": str(target_path).replace("\\", "/"),
        "target_container": detect_audio_container(target_path),
    }
