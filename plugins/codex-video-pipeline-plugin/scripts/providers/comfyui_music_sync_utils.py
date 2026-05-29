#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from audio_output_utils import detect_audio_container, materialize_audio_output
from comfyui_client import ComfyUIClient, ComfyUIError
from stage07_audio_utils import remove_error_messages, resolve_path, upsert_error, utc_now

PROVIDER_NAME = "comfyui_music"
TRANSIENT_TIMEOUT_PREFIX = "Timed out waiting for ComfyUI prompt"
USER_CANCELLED_MESSAGE = "Cancelled by user before ComfyUI completed the music task"


def choose_output(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    audio = [item for item in outputs if item.get("media_type") == "audio"]
    if audio:
        return audio[0]
    files = [item for item in outputs if item.get("media_type") == "file"]
    if files:
        return files[0]
    raise ComfyUIError("ComfyUI music workflow did not produce any audio outputs", kind="output_missing", details=outputs)


def _queue_entries(queue_payload: dict[str, Any], key: str) -> list[Any]:
    value = queue_payload.get(key)
    return value if isinstance(value, list) else []


def queue_state_for_prompt(queue_payload: dict[str, Any], prompt_id: str) -> tuple[str | None, Any]:
    for item in _queue_entries(queue_payload, "queue_running"):
        if isinstance(item, list) and len(item) >= 2 and str(item[1]) == prompt_id:
            return "running", item
    for item in _queue_entries(queue_payload, "queue_pending"):
        if isinstance(item, list) and len(item) >= 2 and str(item[1]) == prompt_id:
            return "queued", item
    return None, None


def _history_cancelled(status: dict[str, Any]) -> bool:
    status_str = str(status.get("status_str") or "").strip().lower()
    if status_str in {"cancelled", "canceled", "interrupted"}:
        return True
    messages = status.get("messages")
    if not isinstance(messages, list):
        return False
    for item in messages:
        if not (isinstance(item, list) and item):
            continue
        tag = str(item[0] or "").strip().lower()
        if "cancel" in tag or "interrupt" in tag:
            return True
    return False


def inspect_remote_prompt_state(client: ComfyUIClient, prompt_id: str) -> dict[str, Any]:
    history_entry = client.get_history(prompt_id)
    if isinstance(history_entry, dict) and history_entry:
        status = history_entry.get("status") if isinstance(history_entry.get("status"), dict) else {}
        if _history_cancelled(status):
            return {"state": "cancelled", "history_entry": history_entry, "queue_entry": None}
        if status.get("status_str") == "error":
            message, details = client._extract_execution_error(history_entry)
            return {
                "state": "failed",
                "history_entry": history_entry,
                "queue_entry": None,
                "message": message,
                "details": details,
            }
        if history_entry.get("outputs") or status.get("completed") is True:
            return {"state": "succeeded", "history_entry": history_entry, "queue_entry": None}
    queue_payload = client.get_queue()
    queue_state, queue_entry = queue_state_for_prompt(queue_payload, prompt_id)
    if queue_state:
        return {
            "state": queue_state,
            "history_entry": history_entry if isinstance(history_entry, dict) else {},
            "queue_entry": queue_entry,
        }
    return {
        "state": "cancelled",
        "history_entry": history_entry if isinstance(history_entry, dict) else {},
        "queue_entry": None,
        "message": USER_CANCELLED_MESSAGE,
    }


def _set_request_status(request_item: dict[str, Any], state: str, *, completed: bool = False, message: str | None = None) -> None:
    request_item["status"] = state
    if completed:
        request_item["completed_at"] = utc_now()
    else:
        request_item["completed_at"] = None
    request_item["error_message"] = message


def mark_job_in_progress(job: dict[str, Any], workflow_name: str, prompt_id: str, state: str) -> None:
    remove_error_messages(job, PROVIDER_NAME, (TRANSIENT_TIMEOUT_PREFIX, USER_CANCELLED_MESSAGE))
    job["provider"] = PROVIDER_NAME
    job["status"] = state
    job.setdefault("evidence", {})
    job["notes"] = f"workflow={workflow_name}; prompt_id={prompt_id}; sync_state={state}"


def mark_job_cancelled(job: dict[str, Any], workflow_name: str, prompt_id: str, message: str) -> None:
    remove_error_messages(job, PROVIDER_NAME, (TRANSIENT_TIMEOUT_PREFIX, USER_CANCELLED_MESSAGE))
    job["provider"] = PROVIDER_NAME
    job["status"] = "cancelled"
    upsert_error(job, PROVIDER_NAME, message, status="cancelled")
    job.setdefault("evidence", {})
    job["notes"] = f"workflow={workflow_name}; prompt_id={prompt_id}; sync_state=cancelled; reason=user_cancelled"


def mark_job_failed(job: dict[str, Any], workflow_name: str, prompt_id: str, message: str) -> None:
    remove_error_messages(job, PROVIDER_NAME, (TRANSIENT_TIMEOUT_PREFIX,))
    upsert_error(job, PROVIDER_NAME, message, status="failed")
    job.setdefault("evidence", {})
    job["notes"] = f"workflow={workflow_name}; prompt_id={prompt_id}; sync_state=failed"


def finalize_music_success(
    *,
    client: ComfyUIClient,
    manifest_path: Path,
    job: dict[str, Any],
    request_item: dict[str, Any],
    workflow_name: str,
    prompt_id: str,
    history_entry: dict[str, Any],
) -> None:
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
    remove_error_messages(job, PROVIDER_NAME, (TRANSIENT_TIMEOUT_PREFIX, USER_CANCELLED_MESSAGE))
    job["provider"] = PROVIDER_NAME
    job["status"] = "succeeded"
    job["errors"] = [
        item for item in (job.get("errors") or [])
        if not (isinstance(item, dict) and item.get("provider") == PROVIDER_NAME)
    ]
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
        f"workflow={workflow_name}; prompt_id={prompt_id}; "
        f"audio_materialization={materialized.get('mode')}; target_container={materialized.get('target_container') or 'unknown'}"
    )
    if request_item.get("music_profile"):
        job["notes"] += f"; music_profile={request_item['music_profile']}"
    if request_item.get("acestep_prompt"):
        job["notes"] += "; prompt_builder=acestep"
    elif request_item.get("heartmula_prompt"):
        job["notes"] += "; prompt_builder=lyrics_tags"
    request_item.update({
        "status": "succeeded",
        "completed_at": utc_now(),
        "prompt_id": prompt_id,
        "selected_output": selected_output,
        "materialized_output": materialized,
        "error_message": None,
    })


def sync_request_and_job(
    *,
    client: ComfyUIClient,
    manifest_path: Path,
    workflow_name: str,
    request_item: dict[str, Any],
    job: dict[str, Any],
) -> str:
    prompt_id = str(request_item.get("prompt_id") or "").strip()
    if not prompt_id:
        request_item["status"] = "planned"
        return "planned"
    remote = inspect_remote_prompt_state(client, prompt_id)
    state = remote["state"]
    if state == "succeeded":
        finalize_music_success(
            client=client,
            manifest_path=manifest_path,
            job=job,
            request_item=request_item,
            workflow_name=workflow_name,
            prompt_id=prompt_id,
            history_entry=remote["history_entry"],
        )
        return state
    if state == "failed":
        message = str(remote.get("message") or "ComfyUI prompt execution failed")
        _set_request_status(request_item, "failed", completed=True, message=message)
        mark_job_failed(job, workflow_name, prompt_id, message)
        return state
    if state == "cancelled":
        message = str(remote.get("message") or USER_CANCELLED_MESSAGE)
        _set_request_status(request_item, "cancelled", completed=True, message=message)
        mark_job_cancelled(job, workflow_name, prompt_id, message)
        return state
    _set_request_status(request_item, state, completed=False, message=None)
    mark_job_in_progress(job, workflow_name, prompt_id, state)
    return state
