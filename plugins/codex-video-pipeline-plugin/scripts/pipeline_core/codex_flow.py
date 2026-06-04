from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


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


def run_codex_exec(
    request_text: str,
    schema_path: Path,
    output_message_path: Path,
    *,
    codex_bin: str,
    cwd: Path,
    timeout_seconds: int = 180,
) -> None:
    cmd = [
        codex_bin,
        "--ask-for-approval",
        "never",
        "exec",
        "--cd",
        str(cwd),
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--ignore-rules",
        "--color",
        "never",
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_message_path),
        "-",
    ]
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
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"codex exec failed with exit code {result.returncode}"
        raise SystemExit(f"ERROR: {details}")
    if not output_message_path.exists():
        raise SystemExit(f"ERROR: Codex output file was not created: {output_message_path}")


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
