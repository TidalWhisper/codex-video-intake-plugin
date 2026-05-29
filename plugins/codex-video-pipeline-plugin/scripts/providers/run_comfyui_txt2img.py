#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(THIS_DIR.parent))

from comfyui_client import ComfyUIClient, ComfyUIError
from openai_image_client import image_size_for_aspect_ratio
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from provider_config import ConfigError, get_comfyui_settings, load_provider_config, validate_provider_config
from stage05_image_utils import append_error, build_provider_prompt, load_json, resolve_path, update_manifest_state, utc_now, write_json
from workflow_mapping import apply_node_inputs, load_mapped_workflow, load_workflow_mapping


AUTO_ROUTED_WORKFLOW_NAMES = {"", "auto", "txt2img_keyframe"}


def request_record(job: dict[str, Any], workflow_name: str, workflow_path: Path) -> dict[str, Any]:
    width, height = dimensions_for_job(job)
    return {
        "request_id": f"REQ_COMFYUI_TXT2IMG_{job['image_id']}",
        "image_id": job["image_id"],
        "shot_id": job["shot_id"],
        "frame_role": job["frame_role"],
        "provider": "comfyui_txt2img",
        "style_family": job.get("style_family"),
        "workflow_name": workflow_name,
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "prompt": job["prompt"],
        "resolved_prompt": build_provider_prompt(job),
        "negative_prompt": job.get("negative_prompt") or "",
        "seed": stable_seed(job),
        "width": width,
        "height": height,
        "output_path": job["output_path"],
        "status": "planned",
        "prompt_id": None,
        "selected_output": None,
        "error_message": None,
        "requested_at": None,
        "completed_at": None,
    }


def stable_seed(job: dict[str, Any]) -> int:
    raw_seed = job.get("seed")
    if isinstance(raw_seed, int):
        return raw_seed
    return abs(hash(job.get("image_id") or "image")) % 2147483647


def dimensions_for_job(job: dict[str, Any]) -> tuple[int, int]:
    size = image_size_for_aspect_ratio(job.get("aspect_ratio"))
    width_raw, height_raw = size.split("x", 1)
    return int(width_raw), int(height_raw)


def copy_selected_output(selected_output: dict[str, Any], target_path: Path) -> None:
    resolved_path = selected_output.get("resolved_path")
    if not isinstance(resolved_path, str) or not resolved_path.strip():
        raise ComfyUIError("ComfyUI output did not resolve to a local file path", kind="output_missing", details=selected_output)
    source = Path(resolved_path)
    if not source.exists() or not source.is_file():
        raise ComfyUIError(f"ComfyUI output file does not exist: {source}", kind="output_missing", details=selected_output)
    if source.stat().st_size <= 0:
        raise ComfyUIError(f"ComfyUI output file is empty: {source}", kind="output_missing", details=selected_output)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target_path)


def choose_output(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    images = [item for item in outputs if item.get("media_type") == "image"]
    if not images:
        raise ComfyUIError("ComfyUI workflow did not produce any image outputs", kind="output_missing", details=outputs)
    return images[0]


def resolve_workflow_name_for_job(job: dict[str, Any], explicit_workflow_name: str) -> str:
    if explicit_workflow_name not in AUTO_ROUTED_WORKFLOW_NAMES:
        return explicit_workflow_name
    routed = str(job.get("comfyui_workflow_name") or "").strip()
    return routed or "txt2img_keyframe"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--mapping", default=None, help="Optional path to config/workflow_node_mapping.yaml")
    parser.add_argument("--workflow-name", default="txt2img_keyframe", help="Workflow mapping entry to use, or auto-route by style family when left as txt2img_keyframe")
    parser.add_argument("--image-id", default=None, help="Optional single image_id to generate")
    parser.add_argument("--dry-run", action="store_true", help="Only refresh comfyui_image_requests.json without calling ComfyUI")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--max-wait-seconds", type=float, default=None, help="Maximum time to wait for each prompt")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Allow this executor to run even when the project brief requested an earlier terminal output")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    if data.get("stage") != "STAGE_05_KEYFRAME_IMAGES":
        print("ERROR: manifest.stage must be STAGE_05_KEYFRAME_IMAGES", file=sys.stderr)
        return 1
    if not args.allow_beyond_requested_scope:
        scope_error = requested_output_scope_guard_message("STAGE_05", compiled_requirements_from_context(data))
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
    except ComfyUIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    workflow_cache: dict[str, tuple[dict[str, Any], dict[str, Any], Path]] = {}

    def mapped_workflow_for_name(workflow_name: str) -> tuple[dict[str, Any], dict[str, Any], Path]:
        cached = workflow_cache.get(workflow_name)
        if cached is not None:
            return cached
        loaded = load_mapped_workflow(mapping_data, workflow_name)
        workflow_cache[workflow_name] = loaded
        return loaded

    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        print("ERROR: manifest.jobs must be a non-empty list", file=sys.stderr)
        return 1
    selected_jobs = [job for job in jobs if isinstance(job, dict) and (args.image_id is None or job.get("image_id") == args.image_id)]
    if args.image_id and not selected_jobs:
        print(f"ERROR: image_id not found in manifest: {args.image_id}", file=sys.stderr)
        return 1

    request_records: list[dict[str, Any]] = []
    workflow_paths_used: list[str] = []
    for job in selected_jobs:
        workflow_name = resolve_workflow_name_for_job(job, str(args.workflow_name or ""))
        try:
            _, _, workflow_path = mapped_workflow_for_name(workflow_name)
        except ComfyUIError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        request_records.append(request_record(job, workflow_name, workflow_path))
        workflow_path_text = str(workflow_path).replace("\\", "/")
        if workflow_path_text not in workflow_paths_used:
            workflow_paths_used.append(workflow_path_text)

    requests_path = manifest_path.parent / "comfyui_image_requests.json"
    request_manifest = {
        "provider": "comfyui_txt2img",
        "workflow_name": "auto_style_family" if str(args.workflow_name or "") in AUTO_ROUTED_WORKFLOW_NAMES else args.workflow_name,
        "workflow_mapping_path": str(mapping_path).replace("\\", "/"),
        "workflow_path": workflow_paths_used[0] if len(workflow_paths_used) == 1 else None,
        "workflow_paths": workflow_paths_used,
        "generated_at": utc_now(),
        "requests": request_records,
    }
    requests_by_id = {record["image_id"]: record for record in request_manifest["requests"]}
    write_json(requests_path, request_manifest)
    if args.dry_run:
        print(f"COMFYUI REQUEST MANIFEST UPDATED: {requests_path}")
        return 0

    client = ComfyUIClient(
        base_url=settings["base_url"],
        timeout_seconds=settings["timeout_seconds"],
        retry_count=settings["retry_count"],
        output_dir=settings["output_dir"] or None,
    )
    failed = False
    for job in selected_jobs:
        request_item = requests_by_id[job["image_id"]]
        request_item["requested_at"] = utc_now()
        try:
            workflow_name = resolve_workflow_name_for_job(job, str(args.workflow_name or ""))
            workflow_template, mapping_entry, _ = mapped_workflow_for_name(workflow_name)
            width, height = dimensions_for_job(job)
            seed = stable_seed(job)
            workflow = apply_node_inputs(
                workflow_template,
                mapping_entry["nodes"],
                {
                    "positive_prompt": build_provider_prompt(job),
                    "negative_prompt": str(job.get("negative_prompt") or ""),
                    "seed": seed,
                    "width": width,
                    "height": height,
                },
            )
            submitted = client.submit_prompt(workflow)
            request_item["prompt_id"] = submitted["prompt_id"]
            history_entry = client.wait_for_prompt(
                str(submitted["prompt_id"]),
                poll_interval=args.poll_interval,
                max_wait_seconds=args.max_wait_seconds,
            )
            outputs = client.collect_outputs(history_entry)
            selected_output = choose_output(outputs)
            output_path = resolve_path(manifest_path, job.get("output_path") or job.get("evidence", {}).get("file_path"))
            copy_selected_output(selected_output, output_path)
            job["provider"] = "comfyui_txt2img"
            job["status"] = "succeeded"
            job["seed"] = seed
            job["errors"] = []
            job.setdefault("evidence", {})
            job["evidence"].update({
                "file_path": str(output_path).replace("\\", "/"),
                "file_exists": True,
                "file_size_bytes": output_path.stat().st_size,
                "created_at": utc_now(),
            })
            job["notes"] = f"workflow={workflow_name}; prompt_id={submitted['prompt_id']}"
            request_item.update({
                "status": "succeeded",
                "completed_at": utc_now(),
                "prompt_id": submitted["prompt_id"],
                "selected_output": selected_output,
            })
        except ComfyUIError as exc:
            failed = True
            append_error(job, "comfyui_txt2img", str(exc))
            request_item.update({
                "status": "failed",
                "completed_at": utc_now(),
                "error_message": str(exc),
            })
            if args.fail_fast:
                break

    update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    request_manifest["generated_at"] = utc_now()
    write_json(requests_path, request_manifest)

    if failed:
        print(f"COMFYUI TXT2IMG COMPLETED WITH FAILURES: {manifest_path}")
        return 1
    print(f"COMFYUI TXT2IMG COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
