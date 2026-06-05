from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


TRANSIENT_CODEX_ERROR_HINTS = (
    "stream disconnected before completion",
    "upstream request failed",
    "reconnecting...",
)


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"ERROR: file not found: {path}") from exc


def clean_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def resolve_codex_bin(codex_bin: str) -> str:
    requested = str(codex_bin or "").strip() or "codex"
    if sys.platform != "win32":
        return requested

    def normalized(path_value: str) -> str:
        return os.path.normcase(os.path.abspath(path_value))

    requested_path = Path(requested)
    if requested_path.suffix.lower() == ".ps1":
        raise SystemExit(
            "ERROR: --codex-bin resolved to a PowerShell shim (.ps1), which Python cannot launch "
            "reliably on Windows. Please use codex.cmd, codex.exe, or leave --codex-bin unset."
        )

    requested_lookup = shutil.which(requested)
    if requested_lookup and Path(requested_lookup).suffix.lower() != ".ps1":
        return requested_lookup

    if requested_path.is_file() and requested_path.suffix.lower() != ".ps1":
        return str(requested_path)

    fallback_names = ["codex.cmd", "codex.exe", "codex"]
    seen: set[str] = set()
    for name in fallback_names:
        resolved = shutil.which(name)
        if not resolved:
            continue
        normalized_resolved = normalized(resolved)
        if normalized_resolved in seen:
            continue
        seen.add(normalized_resolved)
        if Path(resolved).suffix.lower() == ".ps1":
            continue
        return resolved

    return requested


def build_generation_request(
    *,
    stage_label: str,
    generation_prompt_path: Path,
    schema_path: Path,
    prompt_packet_path: Path,
) -> str:
    generation_prompt = load_text(generation_prompt_path).strip()
    schema_text = load_text(schema_path).strip()
    prompt_packet_text = load_text(prompt_packet_path).strip()
    return "\n\n".join([
        generation_prompt,
        f"You must return exactly one JSON object that matches the provided {stage_label} output schema.",
        f"{stage_label} LLM output schema:",
        schema_text,
        f"{stage_label} prompt packet JSON:",
        prompt_packet_text,
    ])


def build_repair_request(
    *,
    stage_label: str,
    repair_prompt_path: Path,
    schema_path: Path,
    prompt_packet_path: Path,
    repair_packet_path: Path,
    current_llm_output_path: Path,
) -> str:
    repair_prompt = load_text(repair_prompt_path).strip()
    schema_text = load_text(schema_path).strip()
    prompt_packet_text = load_text(prompt_packet_path).strip()
    repair_packet_text = load_text(repair_packet_path).strip()
    current_llm_output_text = load_text(current_llm_output_path).strip()
    return "\n\n".join([
        repair_prompt,
        f"Return a full replacement JSON object that matches the {stage_label} LLM output schema exactly.",
        "Keep every unchanged good field stable unless a failed check requires updating it.",
        f"{stage_label} LLM output schema:",
        schema_text,
        f"Original {stage_label} prompt packet JSON:",
        prompt_packet_text,
        f"Current {stage_label} LLM output JSON:",
        current_llm_output_text,
        f"{stage_label} repair packet JSON:",
        repair_packet_text,
    ])


def _allow_null(schema: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(schema)
    type_value = updated.get("type")
    if isinstance(type_value, str):
        if type_value != "null":
            updated["type"] = [type_value, "null"]
        return updated
    if isinstance(type_value, list):
        if "null" not in type_value:
            updated["type"] = [*type_value, "null"]
        return updated
    any_of = updated.get("anyOf")
    if isinstance(any_of, list):
        if not any(isinstance(item, dict) and item.get("type") == "null" for item in any_of):
            updated["anyOf"] = [*any_of, {"type": "null"}]
        return updated
    return {
        "anyOf": [
            updated,
            {"type": "null"},
        ]
    }


def build_strict_response_schema(schema: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(schema)
    properties = updated.get("properties")
    if isinstance(properties, dict):
        original_required = set(updated.get("required") or [])
        strict_properties: dict[str, Any] = {}
        for key, value in properties.items():
            normalized = build_strict_response_schema(value) if isinstance(value, dict) else value
            if key not in original_required and isinstance(normalized, dict):
                normalized = _allow_null(normalized)
            strict_properties[key] = normalized
        updated["properties"] = strict_properties
        updated["required"] = list(strict_properties.keys())
        if "type" not in updated:
            updated["type"] = "object"
        if "additionalProperties" not in updated:
            updated["additionalProperties"] = False
    items = updated.get("items")
    if isinstance(items, dict):
        updated["items"] = build_strict_response_schema(items)
    elif isinstance(items, list):
        updated["items"] = [
            build_strict_response_schema(item) if isinstance(item, dict) else item
            for item in items
        ]
    for key in ("anyOf", "oneOf", "allOf"):
        value = updated.get(key)
        if isinstance(value, list):
            updated[key] = [
                build_strict_response_schema(item) if isinstance(item, dict) else item
                for item in value
            ]
    return updated


def write_strict_response_schema(schema_path: Path, output_message_path: Path) -> Path:
    raw_schema = json.loads(load_text(schema_path))
    strict_schema = build_strict_response_schema(raw_schema)
    strict_schema_path = output_message_path.with_name(f"{schema_path.stem}.codex_response_format.schema.json")
    strict_schema_path.write_text(json.dumps(strict_schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return strict_schema_path


def run_codex_exec(
    request_text: str,
    schema_path: Path,
    output_message_path: Path,
    *,
    codex_bin: str,
    cwd: Path,
    timeout_seconds: int = 180,
    max_transient_retries: int = 3,
) -> None:
    strict_schema_path = write_strict_response_schema(schema_path, output_message_path)
    cmd = [
        codex_bin,
        "--ask-for-approval",
        "never",
        "exec",
        "--cd",
        str(cwd),
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--ignore-rules",
        "--color",
        "never",
        "--output-schema",
        str(strict_schema_path),
        "--output-last-message",
        str(output_message_path),
        "-",
    ]
    attempts = max(1, int(max_transient_retries) + 1)
    last_error: str | None = None
    for attempt in range(1, attempts + 1):
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                input=request_text,
                text=True,
                capture_output=True,
                cwd=str(cwd),
                encoding="utf-8",
                timeout=max(1, int(timeout_seconds)),
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.time() - start
            stderr = ((exc.stderr or "") if isinstance(exc.stderr, str) else "").strip()
            stdout = ((exc.stdout or "") if isinstance(exc.stdout, str) else "").strip()
            details = stderr or stdout or "codex exec timed out without producing stderr/stdout"
            raise SystemExit(
                "ERROR: codex exec timed out after "
                f"{int(elapsed)}s. This usually means the nested Codex CLI is unhealthy or its provider endpoint "
                f"is unreachable. details={details}"
            ) from exc
        if result.returncode == 0:
            if not output_message_path.exists():
                raise SystemExit(f"ERROR: Codex output file was not created: {output_message_path}")
            return
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"codex exec failed with exit code {result.returncode}"
        last_error = details
        normalized = details.lower()
        is_transient = any(hint in normalized for hint in TRANSIENT_CODEX_ERROR_HINTS)
        if not is_transient or attempt >= attempts:
            raise SystemExit(f"ERROR: {details}")
        time.sleep(min(6, attempt))
    raise SystemExit(f"ERROR: {last_error or 'codex exec failed'}")


def write_codex_output_json(output_message_path: Path, llm_output_path: Path) -> dict[str, Any]:
    raw = load_text(output_message_path)
    cleaned = clean_json_text(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: Codex output was not valid JSON: {exc}")
    llm_output_path.parent.mkdir(parents=True, exist_ok=True)
    llm_output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def cleanup_failure_artifacts(directory: Path, names: list[str]) -> None:
    for name in names:
        path = directory / name
        if path.exists():
            path.unlink()


def structured_validation_errors(errors: list[str]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for idx, message in enumerate(errors):
        path = ""
        if ":" in message and not message.startswith("missing top-level key"):
            path = message.split(":", 1)[0].strip()
        output.append({
            "code": f"validation_error_{idx + 1}",
            "path": path,
            "message": message,
        })
    return output
