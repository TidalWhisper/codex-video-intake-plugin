#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from comfyui_client import ComfyUIClient
from comfyui_music_sync_utils import sync_request_and_job
from provider_config import ConfigError, get_comfyui_settings, load_provider_config, validate_provider_config
from stage07_audio_utils import load_json, update_manifest_state, utc_now, write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 07_audio/audio_manifest.json")
    parser.add_argument("--requests-json", default=None, help="Optional path to 07_audio/music_requests.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--audio-id", default=None, help="Optional single audio_id to sync")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    if data.get("stage") != "STAGE_07_AUDIO":
        print("ERROR: manifest.stage must be STAGE_07_AUDIO", file=sys.stderr)
        return 1

    requests_path = Path(args.requests_json) if args.requests_json else (manifest_path.parent / "music_requests.json")
    request_manifest = load_json(requests_path)

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

    client = ComfyUIClient(
        base_url=settings["base_url"],
        timeout_seconds=settings["timeout_seconds"],
        retry_count=settings["retry_count"],
        output_dir=settings["output_dir"] or None,
    )

    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    job_by_id = {
        str(job.get("audio_id")): job
        for job in jobs
        if isinstance(job, dict) and job.get("audio_type") == "music" and job.get("audio_id")
    }
    requests = request_manifest.get("requests") if isinstance(request_manifest.get("requests"), list) else []

    synced = 0
    failed = False
    active = False
    for request_item in requests:
        if not isinstance(request_item, dict):
            continue
        audio_id = str(request_item.get("audio_id") or "").strip()
        if not audio_id:
            continue
        if args.audio_id and audio_id != args.audio_id:
            continue
        job = job_by_id.get(audio_id)
        if job is None:
            continue
        state = sync_request_and_job(
            client=client,
            manifest_path=manifest_path,
            workflow_name=str(request_manifest.get("workflow_name") or "music_generation"),
            request_item=request_item,
            job=job,
        )
        synced += 1
        if state in {"queued", "running"}:
            active = True
        elif state in {"failed", "cancelled"}:
            failed = True

    update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    request_manifest["generated_at"] = utc_now()
    write_json(requests_path, request_manifest)

    print(f"COMFYUI MUSIC SYNCED: {manifest_path}")
    print(f"SYNCED_REQUESTS: {synced}")
    if failed:
        return 1
    if active:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
