#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from provider_config import ConfigError, load_provider_config, validate_provider_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args(argv)

    try:
        data, path = load_provider_config(config_path=args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate_provider_config(data)
    result = {
        "config_path": str(path).replace("\\", "/"),
        "valid": not errors,
        "errors": errors,
        "openai_enabled": bool((data.get("openai_image") or {}).get("enabled")),
        "comfyui_enabled": bool((data.get("comfyui") or {}).get("enabled")),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"CONFIG_PATH: {result['config_path']}")
        print("CONFIG_STATUS: OK" if result["valid"] else "CONFIG_STATUS: INVALID")
        print(f"OPENAI_ENABLED: {result['openai_enabled']}")
        print(f"COMFYUI_ENABLED: {result['comfyui_enabled']}")
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

