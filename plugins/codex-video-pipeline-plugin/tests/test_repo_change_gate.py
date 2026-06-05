from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


repo_change_gate = load_module("repo_change_gate_test", SCRIPTS / "repo_change_gate.py")


def test_is_blocked_path_rejects_generated_and_temp_paths() -> None:
    blocked = [
        ".pytest_cache/state",
        ".pytest-tmp/session.log",
        ".tmp-official-entry-verify-20260605b/output.json",
        ".video_project/intake/project_brief.draft.json",
        "video_projects/video_20260605_124153_demo/01_script/script.json",
        "plugins/codex-video-pipeline-plugin/__pycache__/helper.pyc",
        ".codex_tmp_ping_prompt.txt",
    ]

    assert all(repo_change_gate.is_blocked_path(path) for path in blocked)


def test_is_blocked_path_allows_real_repo_source_files() -> None:
    allowed = [
        "run_all_tests.py",
        ".githooks/pre-commit",
        "plugins/codex-video-pipeline-plugin/scripts/pipeline_blueprints.py",
        "plugins/codex-video-pipeline-plugin/tests/test_stage00_stage01.py",
        "README_快速开始.md",
    ]

    assert all(not repo_change_gate.is_blocked_path(path) for path in allowed)


def test_python_source_paths_only_returns_existing_python_files() -> None:
    paths = [
        "plugins/codex-video-pipeline-plugin/scripts/repo_change_gate.py",
        "plugins/codex-video-pipeline-plugin/tests/test_repo_change_gate.py",
        "README_快速开始.md",
        "not_real.py",
    ]

    resolved = repo_change_gate.python_source_paths(paths)
    labels = {path.name for path in resolved}

    assert "repo_change_gate.py" in labels
    assert "test_repo_change_gate.py" in labels
    assert "README_快速开始.md" not in labels
    assert "not_real.py" not in labels


def test_stage01_formal_chain_token_gate_accepts_current_sources() -> None:
    repo_change_gate.assert_stage01_formal_chain_clean()


def test_stage02_formal_chain_token_gate_accepts_current_sources() -> None:
    repo_change_gate.assert_stage02_formal_chain_clean()


def test_stage03_formal_chain_token_gate_accepts_current_sources() -> None:
    repo_change_gate.assert_stage03_formal_chain_clean()


def test_stage04_formal_chain_token_gate_accepts_current_sources() -> None:
    repo_change_gate.assert_stage04_formal_chain_clean()


def test_manual_mode_passes_after_stage_contract_suite_without_full_repo_suite(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(repo_change_gate, "run_stage_contract_suite", lambda: calls.append("contract") or 0)
    monkeypatch.setattr(repo_change_gate, "run_full_repo_suite", lambda: calls.append("full") or 0)

    assert repo_change_gate.main([
        "--mode",
        "manual",
        "--staged-path",
        "plugins/codex-video-pipeline-plugin/scripts/repo_change_gate.py",
    ]) == 0
    assert calls == ["contract"]


def test_manual_mode_can_explicitly_run_full_repo_suite(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(repo_change_gate, "run_stage_contract_suite", lambda: calls.append("contract") or 0)
    monkeypatch.setattr(repo_change_gate, "run_full_repo_suite", lambda: calls.append("full") or 0)

    assert repo_change_gate.main([
        "--mode",
        "manual",
        "--with-full-suite",
        "--staged-path",
        "plugins/codex-video-pipeline-plugin/scripts/repo_change_gate.py",
    ]) == 0
    assert calls == ["contract", "full"]
