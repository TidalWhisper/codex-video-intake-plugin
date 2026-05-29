#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(THIS_DIR.parent))

from openai_image_client import OpenAIImageError, generate_image, image_size_for_aspect_ratio
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from provider_config import ConfigError, get_openai_image_settings, load_provider_config, validate_provider_config
from stage05_image_utils import append_error, build_provider_prompt, load_json, resolve_path, update_manifest_state, utc_now, write_json


def request_record(job: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": f"REQ_{settings['provider_name'].upper()}_{job['image_id']}",
        "image_id": job["image_id"],
        "shot_id": job["shot_id"],
        "frame_role": job["frame_role"],
        "provider": settings["provider_name"],
        "model": settings["model"],
        "prompt": job["prompt"],
        "resolved_prompt": build_provider_prompt(job),
        "negative_prompt": job.get("negative_prompt") or "",
        "aspect_ratio": job.get("aspect_ratio"),
        "resolved_size": image_size_for_aspect_ratio(job.get("aspect_ratio")),
        "output_format": settings["output_format"],
        "quality": settings["quality"],
        "background": settings["background"],
        "output_path": job["output_path"],
        "status": "planned",
        "error_message": None,
        "revised_prompt": None,
        "usage": None,
        "requested_at": None,
        "completed_at": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--image-id", default=None, help="Optional single image_id to generate")
    parser.add_argument("--dry-run", action="store_true", help="Only refresh openai_image_requests.json without calling the API")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error")
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

    settings = get_openai_image_settings(config)
    if not settings["enabled"]:
        print("ERROR: openai_image.enabled is false", file=sys.stderr)
        return 1
    if not settings["api_key"]:
        print(f"ERROR: missing API key in env var {settings['api_key_env']}", file=sys.stderr)
        return 1

    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        print("ERROR: manifest.jobs must be a non-empty list", file=sys.stderr)
        return 1

    selected_jobs = [job for job in jobs if isinstance(job, dict) and (args.image_id is None or job.get("image_id") == args.image_id)]
    if args.image_id and not selected_jobs:
        print(f"ERROR: image_id not found in manifest: {args.image_id}", file=sys.stderr)
        return 1

    requests_path = manifest_path.parent / "openai_image_requests.json"
    request_manifest = {
        "provider": settings["provider_name"],
        "model": settings["model"],
        "generated_at": utc_now(),
        "requests": [request_record(job, settings) for job in selected_jobs],
    }
    requests_by_id = {record["image_id"]: record for record in request_manifest["requests"]}
    write_json(requests_path, request_manifest)
    if args.dry_run:
        print(f"OPENAI REQUEST MANIFEST UPDATED: {requests_path}")
        return 0

    failed = False
    for job in selected_jobs:
        request_item = requests_by_id[job["image_id"]]
        request_item["requested_at"] = utc_now()
        try:
            result = generate_image(
                base_url=settings["base_url"],
                api_key=settings["api_key"],
                model=settings["model"],
                prompt=build_provider_prompt(job),
                output_format=settings["output_format"],
                quality=settings["quality"],
                background=settings["background"],
                size=image_size_for_aspect_ratio(job.get("aspect_ratio")),
                timeout_seconds=settings["timeout_seconds"],
            )
            output_path = resolve_path(manifest_path, job.get("output_path") or job.get("evidence", {}).get("file_path"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(result["image_bytes"])
            job["provider"] = settings["provider_name"]
            job["status"] = "succeeded"
            job["errors"] = []
            job.setdefault("evidence", {})
            job["evidence"].update({
                "file_path": str(output_path).replace("\\", "/"),
                "file_exists": True,
                "file_size_bytes": output_path.stat().st_size,
                "created_at": utc_now(),
            })
            job["notes"] = f"model={settings['model']}; size={result['size']}; quality={result['quality']}"
            request_item.update({
                "status": "succeeded",
                "completed_at": utc_now(),
                "revised_prompt": result.get("revised_prompt"),
                "usage": result.get("usage"),
            })
        except OpenAIImageError as exc:
            failed = True
            append_error(job, settings["provider_name"], str(exc))
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
        print(f"OPENAI IMAGE GENERATION COMPLETED WITH FAILURES: {manifest_path}")
        return 1
    print(f"OPENAI IMAGE GENERATION COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
