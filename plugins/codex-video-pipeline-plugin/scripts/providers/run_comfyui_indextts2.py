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

from audio_output_utils import detect_audio_container, materialize_audio_output
from comfyui_client import ComfyUIClient, ComfyUIError
from comfyui_file_staging import stage_input_file
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from provider_config import ConfigError, check_comfyui_server, get_comfyui_settings, load_provider_config, validate_provider_config
from stage07_audio_utils import append_error, load_json, resolve_path, update_manifest_state, utc_now, write_audio_recovery_artifacts, write_json
from workflow_mapping import apply_node_inputs, load_mapped_workflow, load_workflow_mapping


def stable_seed(job: dict[str, Any]) -> int:
    return abs(hash(job.get("audio_id") or "audio")) % 2147483647


def choose_output(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    audio = [item for item in outputs if item.get("media_type") == "audio"]
    if audio:
        return audio[0]
    files = [item for item in outputs if item.get("media_type") == "file"]
    if files:
        return files[0]
    raise ComfyUIError("ComfyUI workflow did not produce any audio outputs", kind="output_missing", details=outputs)


def request_record(job: dict[str, Any], workflow_name: str, workflow_path: Path) -> dict[str, Any]:
    return {
        "request_id": f"REQ_COMFYUI_INDEXTTS2_{job['audio_id']}",
        "audio_id": job["audio_id"],
        "audio_type": job["audio_type"],
        "shot_id": job.get("shot_id"),
        "provider": "indextts2",
        "workflow_name": workflow_name,
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "text": job.get("text"),
        "emotion": job.get("emotion"),
        "speaker_reference": "",
        "seed": stable_seed(job),
        "output_path": job["output_path"],
        "status": "planned",
        "prompt_id": None,
        "selected_output": None,
        "error_message": None,
        "requested_at": None,
        "completed_at": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 07_audio/audio_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--mapping", default=None, help="Optional path to config/workflow_node_mapping.yaml")
    parser.add_argument("--workflow-name", default="indextts2", help="Workflow mapping entry to use")
    parser.add_argument("--audio-id", default=None, help="Optional single audio_id to generate")
    parser.add_argument("--speaker-reference", default="", help="Optional speaker reference audio path")
    parser.add_argument("--dry-run", action="store_true", help="Only refresh indextts2_requests.json without calling ComfyUI")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--max-wait-seconds", type=float, default=None, help="Maximum time to wait for each prompt")
    parser.add_argument("--preflight-timeout", type=int, default=8, help="Short connectivity probe timeout before prompt submission")
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
        and job.get("audio_type") in {"voiceover", "dialogue"}
        and (args.audio_id is None or job.get("audio_id") == args.audio_id)
    ]
    if args.audio_id and not selected_jobs:
        print(f"ERROR: audio_id not found in manifest voice jobs: {args.audio_id}", file=sys.stderr)
        return 1

    requests_path = manifest_path.parent / "indextts2_requests.json"
    request_manifest = {
        "provider": "indextts2",
        "workflow_name": args.workflow_name,
        "workflow_mapping_path": str(mapping_path).replace("\\", "/"),
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "generated_at": utc_now(),
        "requests": [request_record(job, args.workflow_name, workflow_path) for job in selected_jobs],
    }
    requests_by_id = {record["audio_id"]: record for record in request_manifest["requests"]}
    write_json(requests_path, request_manifest)
    if args.dry_run:
        print(f"INDEXTTS2 REQUEST MANIFEST UPDATED: {requests_path}")
        return 0

    comfyui_result = check_comfyui_server(config, timeout=args.preflight_timeout)
    if not comfyui_result.get("ready"):
        message = f"ComfyUI preflight failed before Stage 07 voice submission: {comfyui_result.get('status')}"
        if comfyui_result.get("error"):
            message = f"{message} ({comfyui_result.get('error')})"
        for job in selected_jobs:
            append_error(job, "indextts2", message)
        for request_item in request_manifest["requests"]:
            request_item.update({
                "status": "failed",
                "requested_at": utc_now(),
                "completed_at": utc_now(),
                "error_message": message,
            })
        update_manifest_state(data, manifest_path)
        write_json(manifest_path, data)
        request_manifest["generated_at"] = utc_now()
        write_json(requests_path, request_manifest)
        write_audio_recovery_artifacts(
            manifest_path,
            data,
            reason=message,
            provider_health={
                "comfyui_status": str(comfyui_result.get("status") or "unknown"),
                "comfyui_error": str(comfyui_result.get("error") or ""),
            },
        )
        print(f"ERROR: {message}", file=sys.stderr)
        return 1

    client = ComfyUIClient(
        base_url=settings["base_url"],
        timeout_seconds=settings["timeout_seconds"],
        retry_count=settings["retry_count"],
        output_dir=settings["output_dir"] or None,
    )
    failed = False
    speaker_reference = str(args.speaker_reference or "").strip()
    for job in selected_jobs:
        request_item = requests_by_id[job["audio_id"]]
        request_item["requested_at"] = utc_now()
        request_item["status"] = "submitting"
        request_manifest["generated_at"] = utc_now()
        write_json(requests_path, request_manifest)
        try:
            nodes = mapping_entry["nodes"]
            replacements: dict[str, Any] = {
                "text": str(job.get("text") or ""),
            }
            staged_speaker_reference = ""
            if speaker_reference and "speaker_reference" in nodes:
                source_path = resolve_path(manifest_path, speaker_reference)
                staged_speaker_reference = stage_input_file(
                    source_path,
                    settings["input_dir"],
                    stem_prefix=f"{job['audio_id']}_speaker",
                )
                replacements["speaker_reference"] = staged_speaker_reference
            if "emotion" in nodes and str(job.get("emotion") or "").strip():
                replacements["emotion"] = str(job.get("emotion") or "")
            workflow = apply_node_inputs(workflow_template, nodes, replacements)
            submitted = client.submit_prompt(workflow)
            request_item["prompt_id"] = submitted["prompt_id"]
            history_entry = client.wait_for_prompt(
                str(submitted["prompt_id"]),
                poll_interval=args.poll_interval,
                max_wait_seconds=args.max_wait_seconds,
            )
            output_path = resolve_path(manifest_path, job.get("output_path") or job.get("evidence", {}).get("file_path"))
            outputs = client.collect_outputs(history_entry)
            selected_output = None
            try:
                selected_output = choose_output(outputs)
                materialized = materialize_audio_output(selected_output, output_path)
            except ComfyUIError as exc:
                if exc.kind != "output_missing" or not output_path.exists() or not output_path.is_file() or output_path.stat().st_size <= 0:
                    raise
                materialized = {
                    "mode": "reused_existing",
                    "source_path": str(output_path).replace("\\", "/"),
                    "source_container": detect_audio_container(output_path),
                    "target_path": str(output_path).replace("\\", "/"),
                    "target_container": detect_audio_container(output_path),
                }
            job["provider"] = "indextts2"
            job["status"] = "succeeded"
            job["errors"] = []
            job.setdefault("evidence", {})
            job["evidence"].update({
                "file_path": str(output_path).replace("\\", "/"),
                "file_exists": True,
                "file_size_bytes": output_path.stat().st_size,
                "created_at": utc_now(),
                "detected_container": materialized.get("target_container"),
                "source_file_path": materialized.get("source_path"),
                "source_container": materialized.get("source_container"),
            })
            job["notes"] = (
                f"workflow={args.workflow_name}; prompt_id={submitted['prompt_id']}; "
                f"audio_materialization={materialized.get('mode')}; target_container={materialized.get('target_container') or 'unknown'}"
            )
            request_item.update({
                "status": "succeeded",
                "completed_at": utc_now(),
                "prompt_id": submitted["prompt_id"],
                "selected_output": selected_output,
                "speaker_reference": staged_speaker_reference or speaker_reference,
                "materialized_output": materialized,
            })
        except ComfyUIError as exc:
            failed = True
            append_error(job, "indextts2", str(exc))
            request_item.update({
                "status": "failed",
                "completed_at": utc_now(),
                "error_message": str(exc),
                "speaker_reference": speaker_reference,
            })
            if args.fail_fast:
                break

    update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    request_manifest["generated_at"] = utc_now()
    write_json(requests_path, request_manifest)

    if failed:
        print(f"INDEXTTS2 COMPLETED WITH FAILURES: {manifest_path}")
        return 1
    print(f"INDEXTTS2 COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
