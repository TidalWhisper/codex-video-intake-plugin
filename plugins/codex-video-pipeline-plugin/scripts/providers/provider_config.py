#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml


class ConfigError(RuntimeError):
    pass


AUTH_FILE_CANDIDATES = [
    Path.home() / ".codex" / "auth.json",
    Path.home() / ".codex" / "auth-gpt.json",
    Path.home() / ".codex" / "auth-new.json",
    Path.home() / ".codex" / "auth-tokenrouter.json",
    Path.home() / ".chatgpt-local" / "auth.json",
]

def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_config_path(config_path: str | Path | None = None, root: str | Path | None = None) -> Path:
    if config_path is not None:
        path = Path(config_path)
        if path.is_absolute():
            return path.resolve()
        if path.exists():
            return path.resolve()
        cwd_candidate = (Path.cwd() / path).resolve()
        if cwd_candidate.exists():
            return cwd_candidate
        return (Path(root) if root else root_dir()).joinpath(path).resolve()
    base = Path(root) if root else root_dir()
    return (base / "config" / "providers.yaml").resolve()


def load_provider_config(config_path: str | Path | None = None, root: str | Path | None = None) -> tuple[dict[str, Any], Path]:
    path = resolve_config_path(config_path=config_path, root=root)
    if not path.exists():
        raise ConfigError(
            f"provider config not found: {path}. Copy config/providers.example.yaml to config/providers.yaml and edit locally."
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"provider config root must be an object: {path}")
    return data, path


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_object(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _require_bool(data: dict[str, Any], key: str, errors: list[str]) -> None:
    if not isinstance(data.get(key), bool):
        errors.append(f"{key} must be a boolean")


def _require_non_empty_str(data: dict[str, Any], key: str, errors: list[str]) -> None:
    if not _is_non_empty_str(data.get(key)):
        errors.append(f"{key} must be a non-empty string")


def _require_int(data: dict[str, Any], key: str, errors: list[str], minimum: int = 0) -> None:
    value = data.get(key)
    if not isinstance(value, int):
        errors.append(f"{key} must be an integer")
    elif value < minimum:
        errors.append(f"{key} must be >= {minimum}")


def _require_string_list(data: dict[str, Any], key: str, errors: list[str]) -> None:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(_is_non_empty_str(item) for item in value):
        errors.append(f"{key} must be a non-empty list of strings")


def _load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def inspect_workflow_file(path: str | Path) -> dict[str, Any]:
    workflow_path = Path(path)
    result: dict[str, Any] = {
        "path": str(workflow_path).replace("\\", "/"),
        "exists": workflow_path.exists() and workflow_path.is_file(),
        "valid": False,
        "error": None,
        "node_types": [],
    }
    if not result["exists"]:
        return result
    payload = _load_json_object(workflow_path)
    if payload is None:
        result["error"] = "workflow file is missing or invalid JSON"
        return result
    node_types: set[str] = set()
    for value in payload.values():
        if not isinstance(value, dict):
            continue
        class_type = value.get("class_type")
        if isinstance(class_type, str) and class_type.strip():
            node_types.add(class_type.strip())
    sorted_node_types = sorted(node_types)
    result.update(
        {
            "valid": True,
            "node_types": sorted_node_types,
        }
    )
    return result


def discover_openai_api_key(env_name: str = "OPENAI_API_KEY", env: dict[str, str] | None = None) -> dict[str, str]:
    env_map = env or os.environ
    value = str(env_map.get(env_name, "")).strip()
    if value:
        return {
            "value": value,
            "source": f"env:{env_name}",
        }

    if env_name == "OPENAI_API_KEY":
        for path in AUTH_FILE_CANDIDATES:
            if not path.exists() or not path.is_file():
                continue
            payload = _load_json_object(path)
            if not payload:
                continue
            candidate = str(payload.get("OPENAI_API_KEY") or "").strip()
            if candidate:
                return {
                    "value": candidate,
                    "source": f"file:{path}",
                }

    return {
        "value": "",
        "source": "missing",
    }


def validate_provider_config(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require_non_empty_str(data, "project_root", errors)

    openai_cfg = _require_object(data, "openai_image", errors)
    if openai_cfg:
        _require_bool(openai_cfg, "enabled", errors)
        _require_non_empty_str(openai_cfg, "provider_name", errors)
        _require_non_empty_str(openai_cfg, "model", errors)
        _require_non_empty_str(openai_cfg, "base_url", errors)
        _require_non_empty_str(openai_cfg, "api_key_env", errors)
        _require_non_empty_str(openai_cfg, "output_format", errors)
        _require_non_empty_str(openai_cfg, "quality", errors)
        _require_non_empty_str(openai_cfg, "background", errors)
        _require_int(openai_cfg, "timeout_seconds", errors, minimum=1)
        _require_int(openai_cfg, "retry_count", errors, minimum=0)
        if _is_non_empty_str(openai_cfg.get("base_url")) and not str(openai_cfg["base_url"]).startswith(("http://", "https://")):
            errors.append("openai_image.base_url must start with http:// or https://")
        if openai_cfg.get("output_format") not in {"png", "webp", "jpeg"}:
            errors.append("openai_image.output_format must be png, webp, or jpeg")
        if openai_cfg.get("quality") not in {"low", "medium", "high"}:
            errors.append("openai_image.quality must be low, medium, or high")
        if openai_cfg.get("background") not in {"auto", "transparent", "opaque"}:
            errors.append("openai_image.background must be auto, transparent, or opaque")

    comfyui_cfg = _require_object(data, "comfyui", errors)
    if comfyui_cfg:
        _require_bool(comfyui_cfg, "enabled", errors)
        _require_non_empty_str(comfyui_cfg, "base_url", errors)
        if _is_non_empty_str(comfyui_cfg.get("base_url")) and not str(comfyui_cfg["base_url"]).startswith(("http://", "https://")):
            errors.append("comfyui.base_url must start with http:// or https://")
        _require_int(comfyui_cfg, "timeout_seconds", errors, minimum=1)
        _require_int(comfyui_cfg, "retry_count", errors, minimum=0)
        output_dir = comfyui_cfg.get("output_dir")
        if output_dir is not None and not isinstance(output_dir, str):
            errors.append("comfyui.output_dir must be a string when provided")
        input_dir = comfyui_cfg.get("input_dir")
        if input_dir is not None and not isinstance(input_dir, str):
            errors.append("comfyui.input_dir must be a string when provided")

    stage05_cfg = _require_object(data, "stage05_keyframe_images", errors)
    if stage05_cfg:
        _require_string_list(stage05_cfg, "provider_priority", errors)
        _require_bool(stage05_cfg, "fallback_on_failure", errors)

    stage06_cfg = _require_object(data, "stage06_video_clips", errors)
    if stage06_cfg:
        _require_string_list(stage06_cfg, "provider_priority", errors)
        _require_int(stage06_cfg, "clip_duration_sec_min", errors, minimum=1)
        _require_int(stage06_cfg, "clip_duration_sec_max", errors, minimum=1)
        _require_int(stage06_cfg, "fps", errors, minimum=1)
        min_dur = stage06_cfg.get("clip_duration_sec_min")
        max_dur = stage06_cfg.get("clip_duration_sec_max")
        if isinstance(min_dur, int) and isinstance(max_dur, int) and min_dur > max_dur:
            errors.append("stage06_video_clips.clip_duration_sec_min must be <= clip_duration_sec_max")

    stage07_cfg = _require_object(data, "stage07_audio", errors)
    if stage07_cfg:
        _require_non_empty_str(stage07_cfg, "voice_provider", errors)
        _require_non_empty_str(stage07_cfg, "music_provider", errors)

    return errors


def check_openai_image_provider(data: dict[str, Any], env: dict[str, str] | None = None) -> dict[str, Any]:
    openai_cfg = data.get("openai_image") if isinstance(data.get("openai_image"), dict) else {}
    env_name = str(openai_cfg.get("api_key_env") or "OPENAI_API_KEY")
    enabled = bool(openai_cfg.get("enabled"))
    api_key_info = discover_openai_api_key(env_name=env_name, env=env)
    api_key_present = bool(api_key_info["value"])
    ready = enabled and api_key_present
    status = "ready" if ready else ("disabled" if not enabled else "missing_api_key")
    return {
        "provider": str(openai_cfg.get("provider_name") or "openai_gpt_image2"),
        "enabled": enabled,
        "model": str(openai_cfg.get("model") or "gpt-image-2"),
        "base_url": str(openai_cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/"),
        "api_key_env": env_name,
        "api_key_present": api_key_present,
        "api_key_source": api_key_info["source"],
        "ready": ready,
        "status": status,
    }


def get_openai_image_settings(data: dict[str, Any], env: dict[str, str] | None = None) -> dict[str, Any]:
    openai_cfg = data.get("openai_image") if isinstance(data.get("openai_image"), dict) else {}
    api_key_env = str(openai_cfg.get("api_key_env") or "OPENAI_API_KEY")
    api_key_info = discover_openai_api_key(env_name=api_key_env, env=env)
    settings = {
        "provider_name": str(openai_cfg.get("provider_name") or "openai_gpt_image2"),
        "model": str(openai_cfg.get("model") or "gpt-image-2"),
        "base_url": str(openai_cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/"),
        "api_key_env": api_key_env,
        "api_key": api_key_info["value"],
        "api_key_source": api_key_info["source"],
        "output_format": str(openai_cfg.get("output_format") or "png"),
        "quality": str(openai_cfg.get("quality") or "high"),
        "background": str(openai_cfg.get("background") or "auto"),
        "timeout_seconds": int(openai_cfg.get("timeout_seconds") or 180),
        "retry_count": int(openai_cfg.get("retry_count") or 2),
        "enabled": bool(openai_cfg.get("enabled")),
    }
    return settings


def get_comfyui_settings(data: dict[str, Any], env: dict[str, str] | None = None) -> dict[str, Any]:
    comfyui_cfg = data.get("comfyui") if isinstance(data.get("comfyui"), dict) else {}
    return {
        "enabled": bool(comfyui_cfg.get("enabled")),
        "base_url": str(comfyui_cfg.get("base_url") or "http://127.0.0.1:8188").rstrip("/"),
        "timeout_seconds": int(comfyui_cfg.get("timeout_seconds") or 600),
        "retry_count": int(comfyui_cfg.get("retry_count") or 1),
        "output_dir": str(comfyui_cfg.get("output_dir") or "").strip(),
        "input_dir": str(comfyui_cfg.get("input_dir") or "").strip(),
    }


def check_comfyui_server(data: dict[str, Any], timeout: int | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    settings = get_comfyui_settings(data, env=env)
    if not settings["enabled"]:
        return {
            "provider": "comfyui",
            "enabled": False,
            "base_url": settings["base_url"],
            "ready": False,
            "status": "disabled",
        }

    try:
        from comfyui_client import ComfyUIClient, ComfyUIError

        client = ComfyUIClient(
            base_url=settings["base_url"],
            timeout_seconds=int(timeout or settings["timeout_seconds"]),
            retry_count=settings["retry_count"],
            output_dir=settings["output_dir"] or None,
        )
        payload = client.get_system_stats()
    except Exception as exc:  # Keep provider_config importable without hard dependency on CLI wrappers.
        if exc.__class__.__name__ == "ComfyUIError":
            status = getattr(exc, "kind", None) or "connection_error"
            error = str(exc)
        else:
            status = "client_error"
            error = str(exc)
        return {
            "provider": "comfyui",
            "enabled": True,
            "base_url": settings["base_url"],
            "ready": False,
            "status": status,
            "error": error,
        }
    return {
        "provider": "comfyui",
        "enabled": True,
        "base_url": settings["base_url"],
        "http_status": 200,
        "ready": True,
        "status": "ready",
        "response_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
    }
