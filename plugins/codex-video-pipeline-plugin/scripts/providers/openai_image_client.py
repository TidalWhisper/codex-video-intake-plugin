#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Any


class OpenAIImageError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def image_size_for_aspect_ratio(aspect_ratio: str | None) -> str:
    aspect = str(aspect_ratio or "").strip()
    if aspect in {"16:9", "4:3", "3:2"}:
        return "1536x1024"
    if aspect in {"9:16", "3:4", "2:3", "4:5"}:
        return "1024x1536"
    return "1024x1024"


def _error_message_from_payload(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str) and error["message"].strip():
            return error["message"].strip()
    return fallback


def generate_image(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    output_format: str = "png",
    quality: str = "high",
    background: str = "auto",
    size: str = "1024x1536",
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    if not api_key.strip():
        raise OpenAIImageError("OPENAI_API_KEY is missing")
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "output_format": output_format,
    }
    if background:
        payload["background"] = background

    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            status_code = getattr(response, "status", None) or response.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        raise OpenAIImageError(
            _error_message_from_payload(payload, f"OpenAI image request failed with HTTP {exc.code}"),
            status_code=exc.code,
            details=payload,
        ) from exc
    except urllib.error.URLError as exc:
        raise OpenAIImageError(f"OpenAI image request failed: {exc.reason or exc}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OpenAIImageError("OpenAI image response was not valid JSON", status_code=status_code, details=body) from exc
    if not isinstance(data, dict):
        raise OpenAIImageError("OpenAI image response must be a JSON object", status_code=status_code, details=data)
    images = data.get("data")
    if not isinstance(images, list) or not images or not isinstance(images[0], dict):
        raise OpenAIImageError("OpenAI image response did not include image data", status_code=status_code, details=data)
    item = images[0]
    image_b64 = item.get("b64_json")
    if not isinstance(image_b64, str) or not image_b64.strip():
        raise OpenAIImageError("OpenAI image response did not include b64_json", status_code=status_code, details=item)
    try:
        image_bytes = base64.b64decode(image_b64, validate=True)
    except Exception as exc:  # pragma: no cover - decode library exception detail is not stable
        raise OpenAIImageError("OpenAI image response contained invalid base64 data", status_code=status_code, details=item) from exc
    if not image_bytes:
        raise OpenAIImageError("OpenAI image response contained empty image bytes", status_code=status_code, details=item)
    return {
        "status_code": status_code,
        "image_bytes": image_bytes,
        "created": data.get("created"),
        "revised_prompt": item.get("revised_prompt"),
        "response": data,
        "usage": data.get("usage"),
        "output_format": data.get("output_format") or output_format,
        "quality": data.get("quality") or quality,
        "size": data.get("size") or size,
        "background": data.get("background") or background,
    }

