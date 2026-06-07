from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


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


def test_pre_commit_uses_staged_paths_and_blocks_temp_files() -> None:
    assert (
        repo_change_gate.main(
            [
                "--mode",
                "pre-commit",
                "--staged-path",
                ".pytest-tmp/session.log",
            ]
        )
        == 1
    )


def test_manual_mode_passes_real_source_files() -> None:
    assert (
        repo_change_gate.main(
            [
                "--mode",
                "manual",
                "--staged-path",
                "plugins/codex-video-pipeline-plugin/scripts/repo_change_gate.py",
            ]
        )
        == 0
    )


def test_pre_push_is_a_fast_no_op() -> None:
    assert repo_change_gate.main(["--mode", "pre-push"]) == 0
