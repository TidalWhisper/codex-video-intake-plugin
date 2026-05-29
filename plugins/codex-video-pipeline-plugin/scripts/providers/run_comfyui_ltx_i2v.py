#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from comfyui_file_staging import stage_input_file
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from provider_config import ConfigError, get_comfyui_settings, load_provider_config, validate_provider_config
from stage06_video_utils import append_error, build_motion_prompt, load_json, resolve_path, update_manifest_state, utc_now, write_json
from workflow_mapping import apply_node_inputs, load_mapped_workflow, load_workflow_mapping


def stable_seed(job: dict[str, Any]) -> int:
    raw_seed = job.get("seed")
    if isinstance(raw_seed, int):
        return raw_seed
    return abs(hash(job.get("clip_id") or "clip")) % 2147483647


def frame_count_for_job(job: dict[str, Any]) -> int:
    try:
        duration = float(job.get("duration_sec") or 0)
    except Exception:
        duration = 0.0
    fps = fps_for_job(job)
    target = max(9, int(round(duration * fps)) + 1)
    remainder = (target - 1) % 8
    if remainder:
        target -= remainder
    return max(9, target)


def request_record(job: dict[str, Any], workflow_name: str, workflow_path: Path) -> dict[str, Any]:
    width, height = dimensions_for_job(job)
    return {
        "request_id": f"REQ_COMFYUI_LTX_I2V_{job['clip_id']}",
        "clip_id": job["clip_id"],
        "shot_id": job["shot_id"],
        "provider": "comfyui_ltx_i2v",
        "workflow_name": workflow_name,
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "start_keyframe_path": job["source_keyframes"]["start"],
        "end_keyframe_path": job["source_keyframes"]["end"],
        "motion_prompt": job.get("motion_prompt") or "",
        "resolved_motion_prompt": build_motion_prompt(job),
        "seed": stable_seed(job),
        "frame_count": frame_count_for_job(job),
        "duration_sec": duration_seconds_for_job(job),
        "fps": fps_for_job(job),
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


def choose_output(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    videos = [item for item in outputs if item.get("media_type") == "video"]
    if videos:
        return videos[0]
    files = [item for item in outputs if item.get("media_type") == "file"]
    if files:
        return files[0]
    raise ComfyUIError("ComfyUI workflow did not produce any video outputs", kind="output_missing", details=outputs)


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


def resolution_for_job(job: dict[str, Any]) -> str:
    width, height = dimensions_for_job(job)
    return f"{width}x{height}"


def duration_seconds_for_job(job: dict[str, Any]) -> int:
    target = max(1, int(round(float(job.get("duration_sec") or 0))))
    supported = [6, 8, 10, 12, 14, 16, 18, 20]
    return min(supported, key=lambda item: abs(item - target))


def fps_for_job(job: dict[str, Any]) -> int:
    target = max(1, int(round(float(job.get("fps") or 25))))
    supported = [25, 50]
    return min(supported, key=lambda item: abs(item - target))


def dimensions_for_job(job: dict[str, Any]) -> tuple[int, int]:
    aspect = str(job.get("aspect_ratio") or "").strip()
    if aspect == "9:16":
        return 576, 1024
    if aspect == "16:9":
        return 1024, 576
    return 768, 768


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 06_video_clips/video_clip_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--mapping", default=None, help="Optional path to config/workflow_node_mapping.yaml")
    parser.add_argument("--workflow-name", default="i2v_ltx", help="Workflow mapping entry to use")
    parser.add_argument("--clip-id", default=None, help="Optional single clip_id to generate")
    parser.add_argument("--dry-run", action="store_true", help="Only refresh comfyui_ltx_i2v_requests.json without calling ComfyUI")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--max-wait-seconds", type=float, default=None, help="Maximum time to wait for each prompt")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Allow this executor to run even when the project brief requested an earlier terminal output")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    if data.get("stage") != "STAGE_06_VIDEO_CLIPS":
        print("ERROR: manifest.stage must be STAGE_06_VIDEO_CLIPS", file=sys.stderr)
        return 1
    if not args.allow_beyond_requested_scope:
        scope_error = requested_output_scope_guard_message("STAGE_06", compiled_requirements_from_context(data))
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
    selected_jobs = [job for job in jobs if isinstance(job, dict) and (args.clip_id is None or job.get("clip_id") == args.clip_id)]
    if args.clip_id and not selected_jobs:
        print(f"ERROR: clip_id not found in manifest: {args.clip_id}", file=sys.stderr)
        return 1

    requests_path = manifest_path.parent / "comfyui_ltx_i2v_requests.json"
    request_manifest = {
        "provider": "comfyui_ltx_i2v",
        "workflow_name": args.workflow_name,
        "workflow_mapping_path": str(mapping_path).replace("\\", "/"),
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "generated_at": utc_now(),
        "requests": [request_record(job, args.workflow_name, workflow_path) for job in selected_jobs],
    }
    requests_by_id = {record["clip_id"]: record for record in request_manifest["requests"]}
    write_json(requests_path, request_manifest)
    if args.dry_run:
        print(f"COMFYUI LTX REQUEST MANIFEST UPDATED: {requests_path}")
        return 0

    client = ComfyUIClient(
        base_url=settings["base_url"],
        timeout_seconds=settings["timeout_seconds"],
        retry_count=settings["retry_count"],
        output_dir=settings["output_dir"] or None,
    )
    failed = False
    for job in selected_jobs:
        request_item = requests_by_id[job["clip_id"]]
        request_item["requested_at"] = utc_now()
        try:
            keyframes = job.get("source_keyframes") if isinstance(job.get("source_keyframes"), dict) else {}
            start_path = resolve_path(manifest_path, keyframes.get("start"))
            end_path = resolve_path(manifest_path, keyframes.get("end"))
            if not start_path.exists() or start_path.stat().st_size <= 0:
                raise ComfyUIError(f"start keyframe missing or empty: {start_path}", kind="input_missing")
            if not end_path.exists() or end_path.stat().st_size <= 0:
                raise ComfyUIError(f"end keyframe missing or empty: {end_path}", kind="input_missing")
            seed = stable_seed(job)
            nodes = mapping_entry["nodes"]
            staged_start = stage_input_file(start_path, settings["input_dir"], stem_prefix=f"{job['clip_id']}_start")
            staged_end = stage_input_file(end_path, settings["input_dir"], stem_prefix=f"{job['clip_id']}_end")
            width, height = dimensions_for_job(job)
            replacements: dict[str, Any] = {
                "start_image": staged_start,
            }
            if "motion_prompt" in nodes:
                replacements["motion_prompt"] = build_motion_prompt(job)
            if "positive_prompt" in nodes:
                replacements["positive_prompt"] = build_motion_prompt(job)
            if "negative_prompt" in nodes:
                replacements["negative_prompt"] = str(job.get("negative_prompt") or "")
            if "end_image" in nodes:
                replacements["end_image"] = staged_end
            if "seed" in nodes:
                replacements["seed"] = seed
            if "frame_count" in nodes:
                replacements["frame_count"] = frame_count_for_job(job)
            if "duration_sec" in nodes:
                replacements["duration_sec"] = duration_seconds_for_job(job)
            if "fps" in nodes:
                replacements["fps"] = fps_for_job(job)
            if "frame_rate" in nodes:
                replacements["frame_rate"] = fps_for_job(job)
            if "width" in nodes:
                replacements["width"] = width
            if "height" in nodes:
                replacements["height"] = height
            if "resolution" in nodes:
                replacements["resolution"] = resolution_for_job(job)
            workflow = apply_node_inputs(workflow_template, nodes, replacements)
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
            job["provider"] = "comfyui_ltx_i2v"
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
            job["notes"] = f"workflow={args.workflow_name}; prompt_id={submitted['prompt_id']}"
            request_item.update({
                "status": "succeeded",
                "completed_at": utc_now(),
                "prompt_id": submitted["prompt_id"],
                "selected_output": selected_output,
                "staged_start_image": staged_start,
                "staged_end_image": staged_end,
            })
        except ComfyUIError as exc:
            failed = True
            append_error(job, "comfyui_ltx_i2v", str(exc))
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
        print(f"COMFYUI LTX I2V COMPLETED WITH FAILURES: {manifest_path}")
        return 1
    print(f"COMFYUI LTX I2V COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
