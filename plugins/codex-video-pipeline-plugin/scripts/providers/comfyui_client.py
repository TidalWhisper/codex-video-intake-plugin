#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class ComfyUIError(RuntimeError):
    def __init__(self, message: str, *, kind: str = "client_error", status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.details = details


class ComfyUIClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: int = 600,
        retry_count: int = 1,
        output_dir: str | Path | None = None,
    ) -> None:
        self.base_url = str(base_url).rstrip("/")
        self.timeout_seconds = int(timeout_seconds)
        self.retry_count = int(retry_count)
        self.output_dir = Path(output_dir).resolve() if output_dir else None

    def _request_json(self, method: str, path: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                details = json.loads(raw)
            except json.JSONDecodeError:
                details = {"raw": raw}
            detail_message = self._summarize_error_details(details)
            message = f"ComfyUI request failed with HTTP {exc.code}"
            if detail_message:
                message = f"{message}: {detail_message}"
            raise ComfyUIError(
                message,
                kind="http_error",
                status_code=exc.code,
                details=details,
            ) from exc
        except urllib.error.URLError as exc:
            raise ComfyUIError(
                f"ComfyUI request failed: {exc.reason or exc}",
                kind="connection_error",
                details={"reason": str(exc.reason or exc)},
            ) from exc
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            raise ComfyUIError(
                "ComfyUI response was not valid JSON",
                kind="invalid_response",
                status_code=status_code,
                details={"raw": raw},
            ) from exc
        if not isinstance(data, dict):
            raise ComfyUIError(
                "ComfyUI response root must be a JSON object",
                kind="invalid_response",
                status_code=status_code,
                details=data,
            )
        return data

    @staticmethod
    def _summarize_node_errors(node_errors: Any, *, limit: int = 3) -> str:
        if not isinstance(node_errors, dict):
            return ""
        parts: list[str] = []
        for node_id, payload in node_errors.items():
            if not isinstance(payload, dict):
                continue
            class_type = str(payload.get("class_type") or "").strip()
            errors = payload.get("errors")
            if not isinstance(errors, list):
                continue
            for item in errors:
                if not isinstance(item, dict):
                    continue
                message = str(item.get("message") or "").strip()
                details = str(item.get("details") or "").strip()
                if message and details:
                    summary = f"node {node_id}"
                    if class_type:
                        summary = f"{summary} ({class_type})"
                    summary = f"{summary}: {message} - {details}"
                elif details or message:
                    summary = f"node {node_id}"
                    if class_type:
                        summary = f"{summary} ({class_type})"
                    summary = f"{summary}: {details or message}"
                else:
                    continue
                parts.append(summary)
                if len(parts) >= limit:
                    return "; ".join(parts)
        return "; ".join(parts)

    @staticmethod
    def _summarize_error_details(details: Any) -> str:
        if isinstance(details, dict):
            error = details.get("error")
            node_error_summary = ComfyUIClient._summarize_node_errors(details.get("node_errors"))
            if isinstance(error, dict):
                error_type = str(error.get("type") or "").strip()
                message = str(error.get("message") or "").strip()
                if error_type and message:
                    summary = f"{error_type}: {message}"
                    if node_error_summary:
                        return f"{summary}; {node_error_summary}"
                    return summary
                if message:
                    if node_error_summary:
                        return f"{message}; {node_error_summary}"
                    return message
                if error_type:
                    if node_error_summary:
                        return f"{error_type}; {node_error_summary}"
                    return error_type
            if node_error_summary:
                return node_error_summary
            message = str(details.get("message") or "").strip()
            if message:
                return message
            raw = str(details.get("raw") or "").strip()
            if raw:
                return raw
        elif details:
            return str(details).strip()
        return ""

    def get_system_stats(self) -> dict[str, Any]:
        return self._request_json("GET", "/system_stats")

    def get_queue(self) -> dict[str, Any]:
        return self._request_json("GET", "/queue")

    def submit_prompt(
        self,
        workflow: dict[str, Any],
        *,
        client_id: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"prompt": workflow}
        if client_id:
            payload["client_id"] = client_id
        if isinstance(extra_data, dict) and extra_data:
            payload["extra_data"] = extra_data
        data = self._request_json("POST", "/prompt", payload=payload)
        prompt_id = data.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise ComfyUIError(
                "ComfyUI submit response did not include prompt_id",
                kind="invalid_response",
                details=data,
            )
        node_errors = data.get("node_errors")
        if isinstance(node_errors, dict) and any(node_errors.values()):
            raise ComfyUIError(
                "ComfyUI returned node_errors during prompt submission",
                kind="submission_error",
                details=data,
            )
        return data

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        data = self._request_json("GET", f"/history/{prompt_id}")
        if prompt_id in data and isinstance(data[prompt_id], dict):
            return data[prompt_id]
        return data

    @staticmethod
    def _extract_execution_error(entry: dict[str, Any]) -> tuple[str, Any]:
        status = entry.get("status") if isinstance(entry.get("status"), dict) else {}
        messages = status.get("messages") if isinstance(status.get("messages"), list) else []
        for item in reversed(messages):
            if not (isinstance(item, list) and len(item) == 2 and item[0] == "execution_error" and isinstance(item[1], dict)):
                continue
            details = item[1]
            node_id = details.get("node_id")
            node_type = details.get("node_type")
            exception_message = str(details.get("exception_message") or "").strip()
            if node_id and node_type and exception_message:
                return f"ComfyUI prompt execution failed at node {node_id} ({node_type}): {exception_message}", details
            if exception_message:
                return f"ComfyUI prompt execution failed: {exception_message}", details
        return "ComfyUI prompt execution failed", entry

    def wait_for_prompt(
        self,
        prompt_id: str,
        *,
        poll_interval: float = 1.0,
        max_wait_seconds: float | None = None,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max_wait_seconds if max_wait_seconds else None
        while True:
            history = self.get_history(prompt_id)
            entry = history.get(prompt_id) if isinstance(history.get(prompt_id), dict) else history
            if isinstance(entry, dict) and entry:
                status = entry.get("status") if isinstance(entry.get("status"), dict) else {}
                if status.get("status_str") == "error":
                    message, details = self._extract_execution_error(entry)
                    raise ComfyUIError(
                        message,
                        kind="execution_error",
                        details=details,
                    )
                if entry.get("outputs") or status.get("completed") is True:
                    return entry
            if deadline is not None and time.monotonic() >= deadline:
                raise ComfyUIError(
                    f"Timed out waiting for ComfyUI prompt {prompt_id}",
                    kind="timeout",
                    details={"prompt_id": prompt_id, "max_wait_seconds": max_wait_seconds},
                )
            time.sleep(max(0.05, float(poll_interval)))

    def collect_outputs(self, history_entry: dict[str, Any]) -> list[dict[str, Any]]:
        outputs = history_entry.get("outputs")
        if not isinstance(outputs, dict):
            return []
        collected: list[dict[str, Any]] = []
        for node_id, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue
            for key, media_type in {
                "images": "image",
                "audio": "audio",
                "videos": "video",
                "gifs": "video",
                "files": "file",
            }.items():
                records = node_output.get(key)
                if not isinstance(records, list):
                    continue
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    filename = item.get("filename")
                    if not isinstance(filename, str) or not filename.strip():
                        continue
                    subfolder = str(item.get("subfolder") or "").strip()
                    media_kind = media_type
                    suffix = Path(filename).suffix.lower()
                    if suffix in {".mp4", ".webm", ".mov", ".mkv", ".avi"}:
                        media_kind = "video"
                    elif suffix in {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".opus"}:
                        media_kind = "audio"
                    resolved_path = None
                    if self.output_dir:
                        resolved_path = str((self.output_dir / subfolder / filename).resolve()).replace("\\", "/")
                    collected.append({
                        "node_id": str(node_id),
                        "slot": key,
                        "media_type": media_kind,
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": item.get("type"),
                        "resolved_path": resolved_path,
                    })
        return collected


def load_workflow_json(path: str | Path) -> dict[str, Any]:
    workflow_path = Path(path)
    if not workflow_path.exists():
        raise ComfyUIError(f"workflow file not found: {workflow_path}", kind="workflow_missing")
    try:
        data = json.loads(workflow_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ComfyUIError(f"workflow file is not valid JSON: {workflow_path}", kind="workflow_invalid") from exc
    if not isinstance(data, dict):
        raise ComfyUIError(f"workflow file root must be a JSON object: {workflow_path}", kind="workflow_invalid")
    return data
