#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from comfyui_client import ComfyUIClient, ComfyUIError, load_workflow_json
from provider_config import ConfigError, get_comfyui_settings, load_provider_config, validate_provider_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_json", help="Path to a ComfyUI API workflow JSON")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--timeout", type=int, default=None, help="Override provider timeout")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    parser.add_argument("--max-wait-seconds", type=float, default=None, help="Maximum time to wait for history completion")
    parser.add_argument("--client-id", default=None, help="Optional ComfyUI client_id")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args(argv)

    try:
        config, config_path = load_provider_config(config_path=args.config)
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
        workflow = load_workflow_json(args.workflow_json)
        client = ComfyUIClient(
            base_url=settings["base_url"],
            timeout_seconds=int(args.timeout or settings["timeout_seconds"]),
            retry_count=settings["retry_count"],
            output_dir=settings["output_dir"] or None,
        )
        submitted = client.submit_prompt(workflow, client_id=args.client_id)
        prompt_id = str(submitted["prompt_id"])
        history_entry = client.wait_for_prompt(
            prompt_id,
            poll_interval=args.poll_interval,
            max_wait_seconds=args.max_wait_seconds,
        )
        outputs = client.collect_outputs(history_entry)
    except ComfyUIError as exc:
        result = {
            "ok": False,
            "status": getattr(exc, "kind", "client_error"),
            "error": str(exc),
            "details": getattr(exc, "details", None),
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"STATUS: {result['status']}")
            print(f"ERROR: {result['error']}")
        return 1

    result = {
        "ok": True,
        "config_path": str(config_path).replace("\\", "/"),
        "base_url": settings["base_url"],
        "prompt_id": prompt_id,
        "number": submitted.get("number"),
        "node_errors": submitted.get("node_errors"),
        "outputs": outputs,
        "history_status": history_entry.get("status"),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"PROMPT_ID: {prompt_id}")
        print(f"OUTPUT_COUNT: {len(outputs)}")
        for output in outputs:
            print(f"OUTPUT: {output['media_type']} {output['filename']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
