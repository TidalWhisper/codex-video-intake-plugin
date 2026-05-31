#!/usr/bin/env python3
"""Sync Stage 07 audio manifest evidence from files on disk."""
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
sys.path.insert(0, str(ROOT / "scripts" / "providers"))
from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402
from providers.provider_config import ConfigError, check_comfyui_server, load_provider_config  # noqa: E402
from providers.stage07_audio_utils import write_audio_recovery_artifacts  # noqa: E402


def resolve(base: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    special_roots: list[Path] = []
    plugin_root = next(
        (anchor.resolve() for anchor in [base.parent, *base.parents] if anchor.name == "codex-video-pipeline-plugin"),
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
    for anchor in [*special_roots, Path.cwd(), base.parent, *base.parents]:
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
    return (base.parent / p).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json")
    parser.add_argument("--provider", default=None, help="Optional provider to set for existing audio, e.g. indextts2 or manual")
    args = parser.parse_args()
    path = Path(args.manifest_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    provider_health: dict[str, str] = {}
    generated_voice = generated_music = generated_total = failed = 0
    voice_jobs = music_jobs = 0
    for job in data.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        audio_type = job.get("audio_type")
        if audio_type in {"voiceover", "dialogue"}:
            voice_jobs += 1
        if audio_type == "music":
            music_jobs += 1
        raw = job.get("output_path") or job.get("evidence", {}).get("file_path")
        if not raw:
            failed += 1
            continue
        audio = resolve(path, str(raw))
        ev = job.setdefault("evidence", {})
        ev["file_path"] = str(audio).replace("\\", "/")
        if audio.exists() and audio.is_file() and audio.stat().st_size > 0:
            ev["file_exists"] = True
            ev["file_size_bytes"] = audio.stat().st_size
            ev["created_at"] = datetime.fromtimestamp(audio.stat().st_mtime, timezone.utc).isoformat()
            job["status"] = "succeeded"
            if args.provider and not job.get("provider"):
                job["provider"] = args.provider
            generated_total += 1
            if audio_type in {"voiceover", "dialogue"}:
                generated_voice += 1
            if audio_type == "music":
                generated_music += 1
        else:
            ev["file_exists"] = False
            ev["file_size_bytes"] = 0
            if job.get("status") == "succeeded":
                job["status"] = "failed"
            failed += 1
    jobs = data.get("jobs") or []
    summary = data.setdefault("summary", {})
    summary["expected_voice_count"] = voice_jobs
    summary["generated_voice_count"] = generated_voice
    summary["expected_music_count"] = music_jobs
    summary["generated_music_count"] = generated_music
    summary["required_audio_count"] = len(jobs)
    summary["generated_audio_count"] = generated_total
    req = data.get("requirements") if isinstance(data.get("requirements"), dict) else {}
    self_check = data.setdefault("self_check", {})
    self_check["has_voice_tracks_for_required_lines"] = (not req.get("voice_required")) or voice_jobs > 0
    self_check["has_music_when_required"] = (not req.get("music_required")) or music_jobs > 0
    all_audio = generated_total == len(jobs) and (len(jobs) > 0 or (not req.get("voice_required") and not req.get("music_required")))
    self_check["all_required_audio_files_exist"] = all_audio
    self_check["ready_for_assembly_stage"] = all_audio
    data["status"] = "generated" if all_audio else ("in_progress" if generated_total > 0 else "draft")
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    if all_audio:
        data["allowed_next_stage"] = next_stage_after("STAGE_07_AUDIO", routing, "STAGE_08_ASSEMBLY")
        self_check.setdefault("notes", [])
        self_check["notes"] = [
            note for note in self_check["notes"]
            if not (isinstance(note, str) and note.startswith(("recovery:", "runtime_status:")))
        ]
        write_audio_recovery_artifacts(
            path,
            data,
            reason="Stage 07 audio files are present and ready for Stage 08 assembly.",
        )
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_07_AUDIO_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"audio_confirmed": True},
            status="active",
        )
    else:
        data["allowed_next_stage"] = None
        try:
            provider_config, _ = load_provider_config(root=ROOT)
            comfyui_result = check_comfyui_server(provider_config, timeout=8)
            provider_health = {
                "comfyui_status": str(comfyui_result.get("status") or "unknown"),
                "comfyui_error": str(comfyui_result.get("error") or ""),
            }
        except ConfigError as exc:
            provider_health = {
                "comfyui_status": "config_error",
                "comfyui_error": str(exc),
            }
        recovery_path, runtime_status_path = write_audio_recovery_artifacts(
            path,
            data,
            reason="Stage 07 audio files are still missing, so assembly cannot continue yet.",
            provider_health=provider_health,
        )
        recovery_note = str(recovery_path).replace("\\", "/")
        runtime_status_note = str(runtime_status_path).replace("\\", "/")
        self_check.setdefault("notes", [])
        self_check["notes"] = [
            note for note in self_check["notes"]
            if isinstance(note, str) and not note.startswith(("recovery:", "runtime_status:"))
        ]
        self_check["notes"].extend([
            f"recovery:{recovery_note}",
            f"runtime_status:{runtime_status_note}",
        ])
        update_project_manifest_for_stage(
            path,
            current_stage="STAGE_07_AUDIO",
            allowed_next_stage=None,
            flags={"audio_confirmed": False},
            status="active",
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"AUDIO MANIFEST SYNCED: {path}")
    print(f"GENERATED_AUDIO: {generated_total}")
    print(f"FAILED_OR_MISSING_AUDIO: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
