#!/usr/bin/env python3
"""Assemble Stage 08 rough cut with FFmpeg.

Default mode attempts FFmpeg concat/mux. Test mode writes a non-empty placeholder rough_cut.mp4.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def resolve_path(base_json: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p
    return (base_json.parent / p).resolve()


def placeholder_mp4_bytes(label: str) -> bytes:
    payload = ("PLACEHOLDER ROUGH CUT - NOT PRODUCTION OUTPUT - " + label).encode("utf-8")
    ftyp = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    free = len(payload) + 8
    return ftyp + free.to_bytes(4, "big") + b"free" + payload


def sync(data: dict, path: Path, out: Path, provider: str, command: list[str] | None, error: str | None = None) -> None:
    exists = out.exists() and out.is_file()
    size = out.stat().st_size if exists else 0
    data.setdefault("ffmpeg_commands", [])
    if command:
        data["ffmpeg_commands"].append({"command": command, "ran_at": datetime.now(timezone.utc).isoformat(), "provider": provider})
    if error:
        data.setdefault("errors", []).append({"message": error, "created_at": datetime.now(timezone.utc).isoformat()})
    data.setdefault("evidence", {})
    data["evidence"].update({"file_path": str(out).replace("\\", "/"), "file_exists": exists, "file_size_bytes": size, "created_at": datetime.now(timezone.utc).isoformat() if exists else None})
    data.setdefault("self_check", {})
    data["self_check"].update({
        "has_timeline_from_confirmed_clips": bool(data.get("timeline")),
        "has_audio_mix_plan": bool(data.get("audio_mix_plan_path")),
        "has_edit_decision_list": bool(data.get("edit_decision_list_path")),
        "has_final_output_file": exists and size > 0,
        "ready_for_qa_stage": exists and size > 0,
    })
    if exists and size > 0:
        data["status"] = "generated"
        data["allowed_next_stage"] = "STAGE_09_QA"
        data["assembly_provider"] = provider
    else:
        data["status"] = "in_progress"
        data["allowed_next_stage"] = None
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--placeholder-test", action="store_true", help="Create non-empty placeholder rough_cut.mp4 for local pipeline tests only")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    out = resolve_path(path, data.get("final_output_path") or "rough_cut/rough_cut.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.placeholder_test:
        out.write_bytes(placeholder_mp4_bytes(data.get("project_id", "project")))
        sync(data, path, out, "placeholder_test_assembly_generator", None, None)
        print(f"PLACEHOLDER ROUGH CUT GENERATED: {out}")
        return 0

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        error = "ffmpeg executable not found in PATH"
        sync(data, path, out, "ffmpeg", None, error)
        print(f"ERROR: {error}")
        return 1

    concat_list = resolve_path(path, data.get("concat_list_path") or "ffmpeg_concat_list.txt")
    if not concat_list.exists():
        error = f"concat list not found: {concat_list}"
        sync(data, path, out, "ffmpeg", None, error)
        print(f"ERROR: {error}")
        return 1

    # Conservative first-pass: concat clips and copy streams. This works when generated clips share encoding.
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(out)]
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        # Fallback re-encode. This can still fail if source files are placeholders or invalid MP4.
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)]
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        error = (result.stderr or result.stdout or "ffmpeg failed").strip()[-2000:]
        sync(data, path, out, "ffmpeg", cmd, error)
        print("FFMPEG ASSEMBLY FAILED")
        print(error)
        return result.returncode or 1

    sync(data, path, out, "ffmpeg", cmd, None)
    print(f"FFMPEG ROUGH CUT GENERATED: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
