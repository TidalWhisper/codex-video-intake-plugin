from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
codex_flow = importlib.import_module("pipeline_core.codex_flow")


class _FakePopen:
    def __init__(self, *, returncode: int = 0, stdout: str = "", stderr: str = "", on_stdin_close=None) -> None:  # noqa: ANN001
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._on_stdin_close = on_stdin_close
        self._terminated = False
        self.stdin = self

    def write(self, data: str) -> int:
        self._input = data
        return len(data)

    def close(self) -> None:
        if self._on_stdin_close is not None:
            self._on_stdin_close()

    def poll(self) -> int | None:
        return self.returncode if self._terminated else None

    def terminate(self) -> None:
        self._terminated = True

    def kill(self) -> None:
        self._terminated = True

    def communicate(self, timeout=None):  # noqa: ANN001
        del timeout
        self._terminated = True
        return self._stdout, self._stderr


def test_build_strict_response_schema_requires_all_properties_and_allows_null_for_optional_fields() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["shots", "self_check"],
        "properties": {
            "status": {"type": "string"},
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["shot_id"],
                    "properties": {
                        "shot_id": {"type": "string"},
                        "location": {"type": "string"},
                    },
                },
            },
            "self_check": {
                "type": "object",
                "additionalProperties": False,
                "required": ["ready"],
                "properties": {
                    "ready": {"type": "boolean"},
                    "notes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    }

    strict = codex_flow.build_strict_response_schema(schema)

    assert strict["required"] == ["status", "shots", "self_check"]
    assert strict["properties"]["status"]["type"] == ["string", "null"]
    shot_item = strict["properties"]["shots"]["items"]
    assert shot_item["required"] == ["shot_id", "location"]
    assert shot_item["properties"]["location"]["type"] == ["string", "null"]
    self_check = strict["properties"]["self_check"]
    assert self_check["required"] == ["ready", "notes"]
    assert self_check["properties"]["notes"]["type"] == ["array", "null"]


def test_run_codex_exec_uses_generated_strict_schema_and_preserves_user_config(tmp_path: Path, monkeypatch) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({
        "type": "object",
        "additionalProperties": False,
        "required": ["self_check"],
        "properties": {
            "status": {"type": "string"},
            "self_check": {
                "type": "object",
                "additionalProperties": False,
                "required": ["ready"],
                "properties": {
                    "ready": {"type": "boolean"},
                    "notes": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    output_message_path = tmp_path / "last_message.txt"
    captured: dict[str, object] = {}

    def fake_popen(cmd, **kwargs):  # noqa: ANN001
        captured["cmd"] = list(cmd)
        captured["cwd"] = kwargs.get("cwd")
        output_message_path.write_text("{}", encoding="utf-8")
        process = _FakePopen(returncode=0, stdout="", stderr="")
        process._terminated = True
        return process

    monkeypatch.setattr(codex_flow.subprocess, "Popen", fake_popen)

    codex_flow.run_codex_exec(
        "return {}",
        schema_path,
        output_message_path,
        codex_bin="codex.cmd",
        cwd=tmp_path,
        timeout_seconds=5,
        max_transient_retries=0,
    )

    cmd = captured["cmd"]
    assert "--ignore-user-config" not in cmd
    schema_arg_index = cmd.index("--output-schema") + 1
    strict_schema_path = Path(cmd[schema_arg_index])
    assert strict_schema_path.exists()
    strict_schema = json.loads(strict_schema_path.read_text(encoding="utf-8"))
    assert strict_schema["required"] == ["status", "self_check"]
    assert strict_schema["properties"]["status"]["type"] == ["string", "null"]
    assert strict_schema["properties"]["self_check"]["required"] == ["ready", "notes"]


def test_run_codex_exec_returns_early_when_output_last_message_becomes_valid_json(tmp_path: Path, monkeypatch) -> None:
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({
        "type": "object",
        "additionalProperties": False,
        "required": ["status"],
        "properties": {
            "status": {"type": "string"},
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    output_message_path = tmp_path / "last_message.txt"

    def fake_popen(cmd, **kwargs):  # noqa: ANN001
        del cmd, kwargs

        def _write_output() -> None:
            output_message_path.write_text('{"status":"ok"}', encoding="utf-8")

        return _FakePopen(returncode=0, stdout="", stderr="", on_stdin_close=_write_output)

    monkeypatch.setattr(codex_flow.subprocess, "Popen", fake_popen)

    start = time.time()
    codex_flow.run_codex_exec(
        "return {\"status\":\"ok\"}",
        schema_path,
        output_message_path,
        codex_bin="codex.cmd",
        cwd=tmp_path,
        timeout_seconds=5,
        max_transient_retries=0,
    )
    elapsed = time.time() - start

    assert elapsed < 2
    assert json.loads(output_message_path.read_text(encoding="utf-8")) == {"status": "ok"}
