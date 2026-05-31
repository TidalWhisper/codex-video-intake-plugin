#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(THIS_DIR.parent))

from comfyui_client import ComfyUIClient, ComfyUIError
from comfyui_file_staging import stage_input_file
from pipeline_core.media_evidence import clip_output_ready
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from provider_config import ConfigError, get_comfyui_settings, load_provider_config, validate_provider_config
from stage06_video_utils import (
    append_error,
    build_motion_prompt,
    build_prompt_relay_global_prompt,
    build_prompt_relay_local_prompts,
    end_guide_frame_for_clip,
    load_json,
    prompt_relay_segment_lengths,
    resolve_path,
    update_manifest_state,
    utc_now,
    write_json,
)
from workflow_mapping import apply_node_inputs, load_mapped_workflow, load_workflow_mapping

TRANSIENT_TIMEOUT_PREFIX = "Timed out waiting for ComfyUI prompt"
VIDEO_EXTENSIONS = (".mp4", ".mov", ".webm", ".mkv", ".avi")


def stable_seed(job: dict[str, Any]) -> int:
    raw_seed = job.get("seed")
    if isinstance(raw_seed, int):
        return raw_seed
    return abs(hash(job.get("clip_id") or "clip")) % 2147483647


def requested_duration_for_job(job: dict[str, Any]) -> float:
    try:
        return max(1.0, float(job.get("duration_sec") or 0))
    except Exception:
        return 1.0


def effective_duration_for_job(job: dict[str, Any]) -> float:
    requested = requested_duration_for_job(job)
    try:
        recommended = float(job.get("recommended_max_duration_sec"))
    except Exception:
        recommended = 0.0
    if recommended > 0:
        return max(1.0, min(requested, recommended))
    return requested


def frame_count_for_job(job: dict[str, Any]) -> int:
    duration = effective_duration_for_job(job)
    fps = fps_for_job(job)
    target = max(9, int(round(duration * fps)) + 1)
    remainder = (target - 1) % 8
    if remainder:
        target -= remainder
    return max(9, target)


def start_guide_strength_for_job(job: dict[str, Any]) -> float:
    if str(job.get("route_hint") or "").strip() == "interaction_handoff":
        return 0.98
    return 0.9


def end_guide_strength_for_job(job: dict[str, Any]) -> float:
    if str(job.get("route_hint") or "").strip() == "interaction_handoff":
        return 0.9
    return 0.96


def mid_guide_frame_for_clip(frame_count: int) -> int:
    return max(1, int(round((max(2, frame_count) - 1) * 0.5)))


def mid_guide_strength_for_job(job: dict[str, Any]) -> float:
    _ = job
    # Community first-last-frame flows on this machine keep the middle guide fully anchored.
    return 1.0


def request_record(job: dict[str, Any], workflow_name: str, workflow_path: Path) -> dict[str, Any]:
    width, height = dimensions_for_job(job)
    frame_count = frame_count_for_job(job)
    fps = fps_for_job(job)
    keyframes = job.get("source_keyframes") if isinstance(job.get("source_keyframes"), dict) else {}
    has_mid = bool(str(keyframes.get("mid") or "").strip())
    job_status = str(job.get("status") or "").strip()
    blocking_reasons = job.get("blocking_reasons") if isinstance(job.get("blocking_reasons"), list) else []
    return {
        "request_id": f"REQ_COMFYUI_LTX_I2V_{job['clip_id']}",
        "clip_id": job["clip_id"],
        "shot_id": job["shot_id"],
        "provider": "comfyui_ltx_i2v",
        "workflow_name": workflow_name,
        "workflow_path": str(workflow_path).replace("\\", "/"),
        "start_keyframe_path": keyframes.get("start") or "",
        "mid_keyframe_path": keyframes.get("mid") or "",
        "end_keyframe_path": keyframes.get("end") or "",
        "motion_prompt": job.get("motion_prompt") or "",
        "resolved_motion_prompt": build_motion_prompt(job),
        "prompt_relay_global_prompt": build_prompt_relay_global_prompt(job),
        "prompt_relay_local_prompts": build_prompt_relay_local_prompts(job),
        "prompt_relay_segment_lengths": prompt_relay_segment_lengths(frame_count, job.get("route_hint")),
        "route_hint": job.get("route_hint"),
        "generation_risk_profile": job.get("generation_risk_profile"),
        "camera_lock_required": bool(job.get("camera_lock_required")),
        "expected_subject_count": job.get("expected_subject_count"),
        "prompt_constraints": job.get("prompt_constraints") or [],
        "blocking_reasons": blocking_reasons if job_status == "blocked" else [],
        "seed": stable_seed(job),
        "frame_count": frame_count,
        "requested_duration_sec": requested_duration_for_job(job),
        "duration_sec": effective_duration_for_job(job),
        "duration_was_clamped": effective_duration_for_job(job) < requested_duration_for_job(job),
        "guide_image_count_planned": 3 if has_mid else 2,
        "fps": fps,
        "end_guide_frame": end_guide_frame_for_clip(frame_count, fps),
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


def _savevideo_candidates(workflow: dict[str, Any], output_dir: Path | None) -> list[Path]:
    if output_dir is None:
        return []
    candidates: list[Path] = []
    for node in workflow.values():
        if not isinstance(node, dict) or str(node.get("class_type") or "") != "SaveVideo":
            continue
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        filename_prefix = str(inputs.get("filename_prefix") or "").strip()
        if not filename_prefix:
            continue
        fmt = str(inputs.get("format") or "auto").strip().lower()
        prefix_path = Path(filename_prefix)
        folder = (output_dir / prefix_path.parent).resolve()
        stem = prefix_path.name
        suffixes = VIDEO_EXTENSIONS if fmt == "auto" else (f".{fmt.lstrip('.')}",)
        for suffix in suffixes:
            candidates.extend(folder.glob(f"{stem}*{suffix}"))
    return [path.resolve() for path in candidates if path.exists() and path.is_file()]


def _fallback_saved_video_output(
    workflow: dict[str, Any],
    output_dir: Path | None,
    *,
    started_at: float,
) -> dict[str, Any] | None:
    candidates = sorted(
        _savevideo_candidates(workflow, output_dir),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            modified = path.stat().st_mtime
        except OSError:
            continue
        if modified + 1 < started_at:
            continue
        subfolder = path.parent.relative_to(output_dir).as_posix() if output_dir and path.parent != output_dir else ""
        return {
            "node_id": "savevideo_fallback",
            "slot": "files",
            "media_type": "video",
            "filename": path.name,
            "subfolder": subfolder,
            "type": "output",
            "resolved_path": str(path).replace("\\", "/"),
        }
    return None


def queue_state_for_prompt(queue_payload: dict[str, Any], prompt_id: str) -> str | None:
    for key, state in [("queue_running", "running"), ("queue_pending", "queued")]:
        entries = queue_payload.get(key)
        if not isinstance(entries, list):
            continue
        for item in entries:
            if isinstance(item, list) and len(item) >= 2 and str(item[1]) == prompt_id:
                return state
    return None


def sync_prompt_state(client: ComfyUIClient, prompt_id: str) -> str:
    history_entry = client.get_history(prompt_id)
    if isinstance(history_entry, dict) and history_entry:
        status = history_entry.get("status") if isinstance(history_entry.get("status"), dict) else {}
        if status.get("status_str") == "error":
            return "failed"
        if history_entry.get("outputs") or status.get("completed") is True:
            return "succeeded"
    return queue_state_for_prompt(client.get_queue(), prompt_id) or "failed"


def resolution_for_job(job: dict[str, Any]) -> str:
    width, height = dimensions_for_job(job)
    return f"{width}x{height}"


def duration_seconds_for_job(job: dict[str, Any]) -> float:
    return effective_duration_for_job(job)


def fps_for_job(job: dict[str, Any]) -> int:
    return max(1, int(round(float(job.get("fps") or 24))))


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
    pending_sync = False
    for job in selected_jobs:
        request_item = requests_by_id[job["clip_id"]]
        if str(job.get("status") or "").strip() == "blocked":
            failed = True
            reason = " | ".join(str(item).strip() for item in (job.get("blocking_reasons") or []) if str(item or "").strip())
            if not reason:
                reason = "Stage 06 job is blocked before execution"
            request_item.update({
                "status": "blocked",
                "completed_at": utc_now(),
                "error_message": reason,
            })
            append_error(job, "comfyui_ltx_i2v", reason)
            job["status"] = "blocked"
            job["notes"] = (f"{job.get('notes') or ''} | " if job.get("notes") else "") + "runner refused blocked job"
            request_manifest["generated_at"] = utc_now()
            write_json(requests_path, request_manifest)
            if args.fail_fast:
                break
            continue
        request_item["requested_at"] = utc_now()
        request_item["status"] = "submitting"
        request_manifest["generated_at"] = utc_now()
        write_json(requests_path, request_manifest)
        try:
            keyframes = job.get("source_keyframes") if isinstance(job.get("source_keyframes"), dict) else {}
            start_path = resolve_path(manifest_path, keyframes.get("start"))
            end_path = resolve_path(manifest_path, keyframes.get("end"))
            mid_path_raw = str(keyframes.get("mid") or "").strip()
            mid_path = resolve_path(manifest_path, mid_path_raw) if mid_path_raw else None
            if not start_path.exists() or start_path.stat().st_size <= 0:
                raise ComfyUIError(f"start keyframe missing or empty: {start_path}", kind="input_missing")
            if not end_path.exists() or end_path.stat().st_size <= 0:
                raise ComfyUIError(f"end keyframe missing or empty: {end_path}", kind="input_missing")
            seed = stable_seed(job)
            nodes = mapping_entry["nodes"]
            staged_start = stage_input_file(start_path, settings["input_dir"], stem_prefix=f"{job['clip_id']}_start")
            staged_end = stage_input_file(end_path, settings["input_dir"], stem_prefix=f"{job['clip_id']}_end")
            staged_mid = ""
            staged_guide_paths = [staged_start]
            if mid_path is not None and mid_path.exists() and mid_path.stat().st_size > 0:
                staged_mid = stage_input_file(mid_path, settings["input_dir"], stem_prefix=f"{job['clip_id']}_mid")
                staged_guide_paths.append(staged_mid)
            staged_guide_paths.append(staged_end)
            staged_guide_images = "\n".join(staged_guide_paths)
            guide_image_count = len(staged_guide_paths)
            width, height = dimensions_for_job(job)
            frame_count = frame_count_for_job(job)
            fps = fps_for_job(job)
            replacements: dict[str, Any] = {}
            if "start_image" in nodes:
                replacements["start_image"] = staged_start
            if "guide_image_paths" in nodes:
                replacements["guide_image_paths"] = staged_guide_images
            if "global_prompt" in nodes:
                replacements["global_prompt"] = build_prompt_relay_global_prompt(job)
            if "local_prompts" in nodes:
                replacements["local_prompts"] = build_prompt_relay_local_prompts(job)
            if "segment_lengths" in nodes:
                replacements["segment_lengths"] = prompt_relay_segment_lengths(frame_count, job.get("route_hint"))
            if "prompt_relay_epsilon" in nodes:
                replacements["prompt_relay_epsilon"] = 0.01
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
                replacements["frame_count"] = frame_count
            if "start_guide_frame" in nodes:
                replacements["start_guide_frame"] = 0
            if "end_guide_frame" in nodes:
                replacements["end_guide_frame"] = end_guide_frame_for_clip(frame_count, fps)
            if guide_image_count >= 3 and "mid_guide_frame" in nodes:
                replacements["mid_guide_frame"] = mid_guide_frame_for_clip(frame_count)
            if "start_guide_strength" in nodes:
                replacements["start_guide_strength"] = start_guide_strength_for_job(job)
            if "end_guide_strength" in nodes:
                replacements["end_guide_strength"] = end_guide_strength_for_job(job)
            if guide_image_count >= 3 and "mid_guide_strength" in nodes:
                replacements["mid_guide_strength"] = mid_guide_strength_for_job(job)
            if "num_guide_images" in nodes:
                replacements["num_guide_images"] = guide_image_count
            if "duration_sec" in nodes:
                replacements["duration_sec"] = duration_seconds_for_job(job)
            if "fps" in nodes:
                replacements["fps"] = fps
            if "frame_rate" in nodes:
                replacements["frame_rate"] = fps
            if "width" in nodes:
                replacements["width"] = width
            if "height" in nodes:
                replacements["height"] = height
            if "resolution" in nodes:
                replacements["resolution"] = resolution_for_job(job)
            if "output_prefix" in nodes:
                replacements["output_prefix"] = f"video/codex_stage06/{job['clip_id'].lower()}"
            if "vram_reserved_gb" in nodes:
                replacements["vram_reserved_gb"] = 1.2
            if "vram_auto_max_reserved_gb" in nodes:
                replacements["vram_auto_max_reserved_gb"] = 0.0
            if "clean_gpu_before" in nodes:
                replacements["clean_gpu_before"] = True
            workflow = apply_node_inputs(workflow_template, nodes, replacements)
            submit_started_at = time.time()
            submitted = client.submit_prompt(
                workflow,
                client_id=f"codex-stage06-{job['clip_id'].lower()}-{uuid.uuid4().hex[:12]}",
            )
            request_item["prompt_id"] = submitted["prompt_id"]
            request_item["status"] = "running"
            request_manifest["generated_at"] = utc_now()
            write_json(requests_path, request_manifest)
            history_entry = client.wait_for_prompt(
                str(submitted["prompt_id"]),
                poll_interval=args.poll_interval,
                max_wait_seconds=args.max_wait_seconds,
            )
            outputs = client.collect_outputs(history_entry)
            if not outputs:
                fallback_output = _fallback_saved_video_output(
                    workflow,
                    client.output_dir,
                    started_at=submit_started_at,
                )
                if fallback_output is not None:
                    outputs = [fallback_output]
            selected_output = choose_output(outputs)
            output_path = resolve_path(manifest_path, job.get("output_path") or job.get("evidence", {}).get("file_path"))
            copy_selected_output(selected_output, output_path)
            if not clip_output_ready(output_path, "comfyui_ltx_i2v"):
                size = output_path.stat().st_size if output_path.exists() and output_path.is_file() else 0
                raise ComfyUIError(
                    f"ComfyUI output file is too small or non-production: {output_path} ({size} bytes)",
                    kind="output_missing",
                )
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
                "staged_mid_image": staged_mid,
                "staged_end_image": staged_end,
                "guide_image_count_used": guide_image_count,
                "error_message": None,
            })
        except ComfyUIError as exc:
            if exc.kind == "timeout" and request_item.get("prompt_id"):
                prompt_id = str(request_item["prompt_id"])
                remote_state = sync_prompt_state(client, prompt_id)
                if remote_state in {"queued", "running"}:
                    pending_sync = True
                    request_item.update({
                        "status": remote_state,
                        "completed_at": None,
                        "error_message": None,
                    })
                    job["provider"] = "comfyui_ltx_i2v"
                    job["status"] = remote_state
                    job.setdefault("evidence", {})
                    job["notes"] = f"workflow={args.workflow_name}; prompt_id={prompt_id}; sync_state={remote_state}"
                else:
                    failed = True
                    append_error(job, "comfyui_ltx_i2v", str(exc))
                    request_item.update({
                        "status": "failed",
                        "completed_at": utc_now(),
                        "error_message": str(exc),
                    })
            else:
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
    if pending_sync:
        print(f"COMFYUI LTX I2V STILL RUNNING OR QUEUED; SYNC REQUIRED: {manifest_path}")
        return 1
    print(f"COMFYUI LTX I2V COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
