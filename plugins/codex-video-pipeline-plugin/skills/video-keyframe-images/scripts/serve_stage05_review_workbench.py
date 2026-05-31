#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import io
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[3]
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "providers"))

import approve_stage05_review_queue  # noqa: E402
import rerun_top_prompt_patches  # noqa: E402
import sync_keyframe_image_manifest  # noqa: E402
from stage05_image_utils import load_json, update_manifest_state, write_json  # noqa: E402


def refresh_stage05_workbench(manifest_path: Path) -> dict[str, Any]:
    data = load_json(manifest_path)
    update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    return data


def capture_action(main_fn: Any, argv: list[str]) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = int(main_fn(argv))
    output = stdout.getvalue()
    error_output = stderr.getvalue()
    combined = output if not error_output else (output + ("\n" if output and not output.endswith("\n") else "") + error_output)
    return exit_code, combined.strip()


def run_action(action: str, manifest_path: Path, *, image_id: str | None, limit: int, config_path: str | None) -> dict[str, Any]:
    action = str(action or "").strip()
    if action == "approve_image":
        if not image_id:
            return {"ok": False, "exit_code": 1, "error": "approve_image requires image_id"}
        exit_code, output = capture_action(
            approve_stage05_review_queue.main,
            [str(manifest_path), "--image-id", image_id],
        )
    elif action == "approve_top":
        exit_code, output = capture_action(
            approve_stage05_review_queue.main,
            [str(manifest_path), "--top", str(max(1, int(limit)))],
        )
    elif action == "auto_repair_image":
        if not image_id:
            return {"ok": False, "exit_code": 1, "error": "auto_repair_image requires image_id"}
        argv = [str(manifest_path), "--image-id", image_id, "--allow-beyond-requested-scope"]
        if config_path:
            argv.extend(["--config", config_path])
        exit_code, output = capture_action(rerun_top_prompt_patches.main, argv)
    elif action == "auto_repair_top":
        argv = [str(manifest_path), "--limit", str(max(1, int(limit))), "--allow-beyond-requested-scope"]
        if config_path:
            argv.extend(["--config", config_path])
        exit_code, output = capture_action(rerun_top_prompt_patches.main, argv)
    elif action == "sync_manifest":
        exit_code, output = capture_action(sync_keyframe_image_manifest.main, [str(manifest_path)])
    else:
        return {"ok": False, "exit_code": 1, "error": f"Unsupported action: {action}"}

    refreshed = refresh_stage05_workbench(manifest_path)
    return {
        "ok": exit_code == 0,
        "exit_code": exit_code,
        "output": output,
        "manifest_path": str(manifest_path.resolve()).replace("\\", "/"),
        "state": json.loads((manifest_path.parent / "stage05_review_workbench.json").read_text(encoding="utf-8")),
        "status": refreshed.get("status"),
    }


class Stage05WorkbenchHandler(BaseHTTPRequestHandler):
    manifest_path: Path
    config_path: str | None

    def _send_bytes(self, body: bytes, *, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        self._send_bytes(
            json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"", "/"}:
            refresh_stage05_workbench(type(self).manifest_path)
            html_path = type(self).manifest_path.parent / "stage05_review_workbench.html"
            self._send_bytes(html_path.read_bytes(), content_type="text/html; charset=utf-8")
            return
        if parsed.path == "/stage05_review_workbench.html":
            refresh_stage05_workbench(type(self).manifest_path)
            html_path = type(self).manifest_path.parent / "stage05_review_workbench.html"
            self._send_bytes(html_path.read_bytes(), content_type="text/html; charset=utf-8")
            return
        if parsed.path in {"/api/state", "/stage05_review_workbench.json"}:
            refresh_stage05_workbench(type(self).manifest_path)
            payload = json.loads((type(self).manifest_path.parent / "stage05_review_workbench.json").read_text(encoding="utf-8"))
            self._send_json(payload)
            return
        if parsed.path == "/api/file":
            query = parse_qs(parsed.query)
            raw_path = str((query.get("path") or [""])[0]).strip()
            if not raw_path:
                self._send_json({"ok": False, "error": "Missing path query parameter"}, status=400)
                return
            target = Path(raw_path)
            if not target.exists() or not target.is_file():
                self._send_json({"ok": False, "error": f"File not found: {raw_path}"}, status=404)
                return
            mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send_bytes(target.read_bytes(), content_type=mime_type)
            return
        self._send_json({"ok": False, "error": f"Not found: {parsed.path}"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/action":
            self._send_json({"ok": False, "error": f"Not found: {parsed.path}"}, status=404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError as exc:
            self._send_json({"ok": False, "error": f"Invalid JSON: {exc}"}, status=400)
            return
        action = str(payload.get("action") or "").strip()
        image_id = str(payload.get("image_id") or "").strip() or None
        limit = int(payload.get("limit") or 3)
        result = run_action(
            action,
            type(self).manifest_path,
            image_id=image_id,
            limit=limit,
            config_path=type(self).config_path,
        )
        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
        self._send_json(result, status=int(status))

    def log_message(self, format: str, *args: object) -> None:
        return


def build_server(manifest_path: Path, *, host: str, port: int, config_path: str | None = None) -> ThreadingHTTPServer:
    refresh_stage05_workbench(manifest_path)
    class BoundStage05WorkbenchHandler(Stage05WorkbenchHandler):
        pass

    BoundStage05WorkbenchHandler.manifest_path = manifest_path
    BoundStage05WorkbenchHandler.config_path = config_path
    return ThreadingHTTPServer((host, port), BoundStage05WorkbenchHandler)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Use 0 for an auto-selected free port")
    parser.add_argument("--config", default=None, help="Optional provider config path forwarded to auto-repair actions")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest_json).resolve()
    server = build_server(manifest_path, host=str(args.host), port=int(args.port), config_path=args.config)
    try:
        host, port = server.server_address[:2]
        manifest_text = str(manifest_path).replace("\\", "/")
        print(f"STAGE05_REVIEW_WORKBENCH_URL: http://{host}:{port}/")
        print(f"STAGE05_REVIEW_WORKBENCH_MANIFEST: {manifest_text}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("STAGE05_REVIEW_WORKBENCH_STOPPED")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
