#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(THIS_DIR.parent))

from acestep_prompt_builder import build_acestep_prompt
from comfyui_client import ComfyUIClient, ComfyUIError
from comfyui_music_sync_utils import finalize_music_success, mark_job_failed, sync_request_and_job
from heartmula_prompt_builder import build_heartmula_prompt
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from provider_config import ConfigError, get_comfyui_settings, load_provider_config, validate_provider_config
from stage07_audio_utils import load_json, update_manifest_state, utc_now, write_json
from workflow_mapping import apply_node_inputs, load_mapped_workflow, load_workflow_mapping


def stable_seed(job: dict[str, Any]) -> int:
    return abs(hash(job.get("audio_id") or "music")) % 2147483647


def music_duration_seconds(job: dict[str, Any]) -> float:
    try:
        duration = float(job.get("duration_sec") or 0)
    except Exception:
        duration = 0.0
    return duration if duration > 0 else 30.0


def request_record(job: dict[str, Any], workflow_name: str, workflow_path: Path) -> dict[str, Any]:
    return {
        "request_id": f"REQ_COMFYUI_MUSIC_{job['audio_id']}",
        "audio_id": job["audio_id"],
        "audio_type": job["audio_type"],
        "provider": "comfyui_music",
        "workflow_name": workflow_name,
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "music_prompt": job.get("music_prompt"),
        "music_profile": job.get("music_profile"),
        "duration_sec": float(job.get("duration_sec") or 0),
        "seed": stable_seed(job),
        "output_path": job["output_path"],
        "status": "planned",
        "prompt_id": None,
        "selected_output": None,
        "error_message": None,
        "requested_at": None,
        "completed_at": None,
    }


def is_heartmula_workflow(workflow_path: Path, mapping_entry: dict[str, Any]) -> bool:
    filename = workflow_path.name.lower()
    if "heartmula" in filename:
        return True
    nodes = mapping_entry.get("nodes") if isinstance(mapping_entry.get("nodes"), dict) else {}
    return "max_audio_length_seconds" in nodes


def is_acestep_workflow(workflow_path: Path) -> bool:
    return "acestep" in workflow_path.name.lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 07_audio/audio_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--mapping", default=None, help="Optional path to config/workflow_node_mapping.yaml")
    parser.add_argument("--workflow-name", default="music_generation", help="Workflow mapping entry to use")
    parser.add_argument("--audio-id", default=None, help="Optional single audio_id to generate")
    parser.add_argument("--dry-run", action="store_true", help="Only refresh music_requests.json without calling ComfyUI")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--max-wait-seconds", type=float, default=None, help="Maximum time to wait for each prompt")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Allow this executor to run even when the project brief requested an earlier terminal output")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    if data.get("stage") != "STAGE_07_AUDIO":
        print("ERROR: manifest.stage must be STAGE_07_AUDIO", file=sys.stderr)
        return 1
    if not args.allow_beyond_requested_scope:
        scope_error = requested_output_scope_guard_message("STAGE_07", compiled_requirements_from_context(data))
        if scope_error:
            print(f"ERROR: {scope_error}", file=sys.stderr)
            return 1

    try:
        config, _ = load_provider_config(config_path=args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    config_errors = validate_provider_config(config)
    if config_errors:
        for error in config_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    settings = get_comfyui_settings(config)
    if not settings["enabled"]:
        print("ERROR: comfyui.enabled is false", file=sys.stderr)
        return 1

    try:
        mapping_data, mapping_path = load_workflow_mapping(mapping_path=args.mapping)
        workflow_template, mapping_entry, workflow_path = load_mapped_workflow(mapping_data, args.workflow_name)
    except ComfyUIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        print("ERROR: manifest.jobs must be a non-empty list", file=sys.stderr)
        return 1
    selected_jobs = [
        job for job in jobs
        if isinstance(job, dict)
        and job.get("audio_type") == "music"
        and (args.audio_id is None or job.get("audio_id") == args.audio_id)
    ]
    if args.audio_id and not selected_jobs:
        print(f"ERROR: audio_id not found in manifest music jobs: {args.audio_id}", file=sys.stderr)
        return 1

    requests_path = manifest_path.parent / "music_requests.json"
    request_manifest = {
        "provider": "comfyui_music",
        "workflow_name": args.workflow_name,
        "workflow_mapping_path": str(mapping_path).replace("\\", "/"),
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "generated_at": utc_now(),
        "requests": [request_record(job, args.workflow_name, workflow_path) for job in selected_jobs],
    }
    requests_by_id = {record["audio_id"]: record for record in request_manifest["requests"]}
    write_json(requests_path, request_manifest)
    if args.dry_run:
        print(f"MUSIC REQUEST MANIFEST UPDATED: {requests_path}")
        return 0

    client = ComfyUIClient(
        base_url=settings["base_url"],
        timeout_seconds=settings["timeout_seconds"],
        retry_count=settings["retry_count"],
        output_dir=settings["output_dir"] or None,
    )
    failed = False
    pending_sync = False
    for job in selected_jobs:
        request_item = requests_by_id[job["audio_id"]]
        request_item["requested_at"] = utc_now()
        try:
            nodes = mapping_entry["nodes"]
            duration_seconds = music_duration_seconds(job)
            replacements: dict[str, Any]
            if is_acestep_workflow(workflow_path):
                acestep_prompt = build_acestep_prompt(
                    manifest_path,
                    job,
                    profile=str(job.get("music_profile") or ""),
                )
                replacements = {}
                if "lyrics" in nodes:
                    replacements["lyrics"] = acestep_prompt["lyrics"]
                if "tags" in nodes:
                    replacements["tags"] = acestep_prompt["tags"]
                if "seed" in nodes:
                    replacements["seed"] = stable_seed(job)
                if "duration_sec" in nodes:
                    replacements["duration_sec"] = duration_seconds
                if "latent_seconds" in nodes:
                    replacements["latent_seconds"] = duration_seconds
                if "bpm" in nodes:
                    replacements["bpm"] = acestep_prompt["bpm"]
                if "language" in nodes:
                    replacements["language"] = acestep_prompt["language"]
                if "keyscale" in nodes:
                    replacements["keyscale"] = acestep_prompt["keyscale"]
                if "timesignature" in nodes:
                    replacements["timesignature"] = acestep_prompt["timesignature"]
                request_item["acestep_prompt"] = acestep_prompt
            elif is_heartmula_workflow(workflow_path, mapping_entry):
                heartmula_prompt = build_heartmula_prompt(manifest_path, job)
                replacements = {}
                if "lyrics" in nodes:
                    replacements["lyrics"] = heartmula_prompt["lyrics"]
                if "tags" in nodes:
                    replacements["tags"] = heartmula_prompt["global_tags"]
                if "seed" in nodes:
                    replacements["seed"] = stable_seed(job)
                if "max_audio_length_seconds" in nodes:
                    replacements["max_audio_length_seconds"] = int(round(duration_seconds))
                request_item["heartmula_prompt"] = heartmula_prompt
            else:
                replacements = {}
                if "prompt" in nodes:
                    replacements["prompt"] = str(job.get("music_prompt") or "")
                if "duration_sec" in nodes:
                    replacements["duration_sec"] = duration_seconds
                if "seed" in nodes:
                    replacements["seed"] = stable_seed(job)
            if "duration_sec" in nodes and "duration_sec" not in replacements:
                replacements["duration_sec"] = duration_seconds
            if "duration" in nodes and "duration" not in replacements:
                replacements["duration"] = duration_seconds
            workflow = apply_node_inputs(
                workflow_template,
                nodes,
                replacements,
            )
            submitted = client.submit_prompt(workflow)
            request_item["prompt_id"] = submitted["prompt_id"]
            history_entry = client.wait_for_prompt(
                str(submitted["prompt_id"]),
                poll_interval=args.poll_interval,
                max_wait_seconds=args.max_wait_seconds,
            )
            finalize_music_success(
                client=client,
                manifest_path=manifest_path,
                job=job,
                request_item=request_item,
                workflow_name=args.workflow_name,
                prompt_id=str(submitted["prompt_id"]),
                history_entry=history_entry,
            )
        except ComfyUIError as exc:
            if exc.kind == "timeout" and request_item.get("prompt_id"):
                state = sync_request_and_job(
                    client=client,
                    manifest_path=manifest_path,
                    workflow_name=args.workflow_name,
                    request_item=request_item,
                    job=job,
                )
                if state in {"queued", "running"}:
                    pending_sync = True
                elif state in {"cancelled", "failed"}:
                    failed = True
            else:
                failed = True
                request_item.update({
                    "status": "failed",
                    "completed_at": utc_now(),
                    "error_message": str(exc),
                })
                mark_job_failed(job, args.workflow_name, str(request_item.get("prompt_id") or ""), str(exc))
            if args.fail_fast:
                break

    update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    request_manifest["generated_at"] = utc_now()
    write_json(requests_path, request_manifest)

    if failed:
        print(f"COMFYUI MUSIC COMPLETED WITH FAILURES: {manifest_path}")
        return 1
    if pending_sync:
        print(f"COMFYUI MUSIC STILL RUNNING OR QUEUED; SYNC REQUIRED: {manifest_path}")
        return 1
    print(f"COMFYUI MUSIC COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
