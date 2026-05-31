#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from provider_config import ConfigError, check_openai_image_provider, load_provider_config, validate_provider_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    parser.add_argument("--timeout", type=int, default=None, help="Override OpenAI auth probe timeout in seconds")
    parser.add_argument("--no-probe", action="store_true", help="Skip live auth probe and only validate local config presence")
    args = parser.parse_args(argv)

    try:
        data, path = load_provider_config(config_path=args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate_provider_config(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    result = check_openai_image_provider(
        data,
        probe=not args.no_probe,
        timeout_seconds=args.timeout,
    )
    result["config_path"] = str(path).replace("\\", "/")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"CONFIG_PATH: {result['config_path']}")
        print(f"PROVIDER: {result['provider']}")
        print(f"OPENAI_ENABLED: {result['enabled']}")
        print(f"API_KEY_ENV: {result['api_key_env']}")
        print(f"API_KEY_PRESENT: {result['api_key_present']}")
        print(f"STATUS: {result['status']}")
        print(f"AUTH_CHECKED: {result.get('auth_checked', False)}")
        if result.get("http_status") is not None:
            print(f"HTTP_STATUS: {result['http_status']}")
        if result.get("error"):
            print(f"ERROR: {result['error']}")
    return 0 if result["status"] in {"ready", "disabled"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
