#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PYTEST_BASETEMP_ROOT = REPO_ROOT / ".pytest-tmp" / "repo-change-gate"

BLOCKED_PREFIXES = (
    ".pytest-",
    ".pytest_",
    ".tmp-",
    ".tmp_",
    ".video_project/",
    "video_projects/",
)
BLOCKED_NAMES = {
    ".pytest_cache",
    ".pytest-tmp",
    ".video_project",
    "__pycache__",
}
BLOCKED_FILE_PREFIXES = (
    ".codex_tmp",
)
FORMAL_STAGE01_FILES = (
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/run_stage01_from_locked_brief.py",
    "plugins/codex-video-pipeline-plugin/skills/video-script-generation/scripts/run_stage01_codex_flow.py",
)
FORBIDDEN_STAGE01_TOKENS = (
    "stage01_local_semantics",
    "build_stage01_llm_output",
    "STAGE01_LOCAL_EXECUTION_MODE",
    "STAGE01_LOCAL_REPAIR_MODE",
)
FORMAL_STAGE02_FILES = (
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/run_stage02_from_confirmed_script.py",
    "plugins/codex-video-pipeline-plugin/skills/video-storyboard-generation/scripts/run_stage02_codex_flow.py",
)
FORBIDDEN_STAGE02_TOKENS = (
    "stage02_local_semantics",
    "build_stage02_llm_output",
    "STAGE02_LOCAL_EXECUTION_MODE",
    "STAGE02_LOCAL_REPAIR_MODE",
)
FORMAL_STAGE03_FILES = (
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/run_stage03_from_confirmed_storyboard.py",
    "plugins/codex-video-pipeline-plugin/skills/video-character-bible/scripts/run_stage03_codex_flow.py",
)
FORBIDDEN_STAGE03_TOKENS = (
    "stage03_local_semantics",
    "build_stage03_llm_output",
    "STAGE03_LOCAL_EXECUTION_MODE",
    "STAGE03_LOCAL_REPAIR_MODE",
)
FORMAL_STAGE04_FILES = (
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/run_stage04_from_confirmed_character_bible.py",
    "plugins/codex-video-pipeline-plugin/skills/video-keyframe-prompts/scripts/run_stage04_codex_flow.py",
)
FORBIDDEN_STAGE04_TOKENS = (
    "stage04_local_semantics",
    "build_stage04_llm_output",
    "STAGE04_LOCAL_EXECUTION_MODE",
    "STAGE04_LOCAL_REPAIR_MODE",
)
FORMAL_CONFIRMATION_FILES = (
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/confirm_stage01_and_continue.py",
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/confirm_stage02_and_continue.py",
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/confirm_stage03_and_continue.py",
    "plugins/codex-video-pipeline-plugin/skills/video-production-pipeline/scripts/confirm_stage04_and_continue.py",
)
FORBIDDEN_CONFIRMATION_TOKENS = (
    "stage01_local_semantics",
    "stage02_local_semantics",
    "stage03_local_semantics",
    "stage04_local_semantics",
)


def normalize_repo_path(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if text.startswith("./"):
        return text[2:]
    return text


def is_blocked_path(path: str) -> bool:
    normalized = normalize_repo_path(path)
    if not normalized:
        return False
    parts = normalized.split("/")
    if any(part in BLOCKED_NAMES for part in parts):
        return True
    filename = parts[-1]
    if any(filename.startswith(prefix) for prefix in BLOCKED_FILE_PREFIXES):
        return True
    return any(normalized.startswith(prefix) for prefix in BLOCKED_PREFIXES)


def blocked_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if is_blocked_path(path)]


def python_source_paths(paths: list[str]) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        normalized = normalize_repo_path(path)
        if not normalized.endswith(".py"):
            continue
        candidate = (REPO_ROOT / normalized).resolve()
        if candidate.exists():
            result.append(candidate)
    return result


def run_command(cmd: list[str], cwd: Path) -> int:
    print("$", " ".join(str(part) for part in cmd))
    completed = subprocess.run(cmd, cwd=str(cwd), text=True)
    return int(completed.returncode)


def git_output(args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stderr.strip() or "git command failed")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def list_staged_paths() -> list[str]:
    return git_output(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])


def run_python_compile(paths: list[Path]) -> int:
    if not paths:
        print("repo_change_gate: no staged python files to compile")
        return 0
    return run_command([sys.executable, "-m", "py_compile", *[str(path) for path in paths]], REPO_ROOT)


def run_full_repo_suite() -> int:
    return run_command([sys.executable, str(REPO_ROOT / "run_all_tests.py")], REPO_ROOT)


def assert_stage01_formal_chain_clean() -> None:
    for relative_path in FORMAL_STAGE01_FILES:
        path = (REPO_ROOT / relative_path).resolve()
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_STAGE01_TOKENS:
            if token in source:
                raise SystemExit(
                    "repo_change_gate: Stage01 formal chain forbidden token detected: "
                    f"{token} in {relative_path}"
                )


def assert_stage02_formal_chain_clean() -> None:
    for relative_path in FORMAL_STAGE02_FILES:
        path = (REPO_ROOT / relative_path).resolve()
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_STAGE02_TOKENS:
            if token in source:
                raise SystemExit(
                    "repo_change_gate: Stage02 formal chain forbidden token detected: "
                    f"{token} in {relative_path}"
                )


def assert_stage03_formal_chain_clean() -> None:
    for relative_path in FORMAL_STAGE03_FILES:
        path = (REPO_ROOT / relative_path).resolve()
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_STAGE03_TOKENS:
            if token in source:
                raise SystemExit(
                    "repo_change_gate: Stage03 formal chain forbidden token detected: "
                    f"{token} in {relative_path}"
                )


def assert_stage04_formal_chain_clean() -> None:
    for relative_path in FORMAL_STAGE04_FILES:
        path = (REPO_ROOT / relative_path).resolve()
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_STAGE04_TOKENS:
            if token in source:
                raise SystemExit(
                    "repo_change_gate: Stage04 formal chain forbidden token detected: "
                    f"{token} in {relative_path}"
                )


def assert_formal_confirmation_chain_clean() -> None:
    for relative_path in FORMAL_CONFIRMATION_FILES:
        path = (REPO_ROOT / relative_path).resolve()
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_CONFIRMATION_TOKENS:
            if token in source:
                raise SystemExit(
                    "repo_change_gate: formal confirmation chain forbidden token detected: "
                    f"{token} in {relative_path}"
                )


def run_stage_contract_suite() -> int:
    assert_stage01_formal_chain_clean()
    assert_stage02_formal_chain_clean()
    assert_stage03_formal_chain_clean()
    assert_stage04_formal_chain_clean()
    assert_formal_confirmation_chain_clean()
    PYTEST_BASETEMP_ROOT.mkdir(parents=True, exist_ok=True)
    run_root = PYTEST_BASETEMP_ROOT / f"run-{os.getpid()}"
    run_root.mkdir(parents=True, exist_ok=True)
    tests = [
        [
            "-q",
            f"--basetemp={run_root / 'official-entry'}",
            "plugins/codex-video-pipeline-plugin/tests/test_stage00_codex_first.py",
            "-k",
            "official_pipeline_blank_project_reaches_stage01_without_rainy_store_phrase_regression",
        ],
        [
            "-q",
            f"--basetemp={run_root / 'stage-contracts'}",
            "plugins/codex-video-pipeline-plugin/tests/test_stage00_stage01.py",
            "-k",
            (
                "stage01_formal_runner_no_longer_imports_local_semantics "
                "or stage01_formal_entry_chain_has_no_local_semantics_reference "
                "or stage02_formal_runner_no_longer_imports_local_semantics "
                "or stage02_formal_entry_chain_has_no_local_semantics_reference "
                "or stage03_formal_runner_no_longer_imports_local_semantics "
                "or stage03_formal_entry_chain_has_no_local_semantics_reference "
                "or stage04_formal_runner_no_longer_imports_local_semantics "
                "or stage04_formal_entry_chain_has_no_local_semantics_reference "
                "or stage01_to_stage02_contract_preserves_beats_sections_and_anchors "
                "or stage01_formal_output_flows_through_stage02_formal_entry "
                "or stage02_formal_output_flows_through_stage03_formal_entry "
                "or stage03_formal_output_flows_through_stage04_formal_entry "
                "or run_stage01_codex_flow_generates_stage01_package_without_manual_llm_fill "
                "or run_stage02_codex_flow_generates_storyboard_package_without_manual_llm_fill "
                "or run_stage02_codex_flow_auto_repairs_failed_first_attempt "
                "or run_stage03_codex_flow_generates_character_bible_without_manual_llm_fill "
                "or run_stage03_codex_flow_auto_repairs_failed_first_attempt "
                "or run_stage04_codex_flow_generates_keyframe_prompts_without_manual_llm_fill "
                "or run_stage04_codex_flow_auto_repairs_failed_first_attempt"
            ),
        ],
    ]
    for args in tests:
        if run_command([sys.executable, "-m", "pytest", *args], REPO_ROOT) != 0:
            return 1
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pre-commit", "pre-push", "manual"), default="manual")
    parser.add_argument(
        "--with-full-suite",
        action="store_true",
        help="Also run the legacy full-repo suite after the hard Stage00-Stage02 gate passes.",
    )
    parser.add_argument(
        "--staged-path",
        dest="staged_paths",
        action="append",
        default=[],
        help="Override staged paths for testing or manual verification.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    staged_paths = [normalize_repo_path(path) for path in (args.staged_paths or []) if normalize_repo_path(path)]
    if not staged_paths and args.mode == "pre-commit":
        staged_paths = list_staged_paths()

    if args.mode == "pre-commit":
        if not staged_paths:
            print("repo_change_gate: no staged changes, skipping pre-commit gate")
            return 0
        denied = blocked_paths(staged_paths)
        if denied:
            print("repo_change_gate: blocked generated or temporary paths detected:", file=sys.stderr)
            for path in denied:
                print(f"  - {path}", file=sys.stderr)
            return 1
        if run_python_compile(python_source_paths(staged_paths)) != 0:
            return 1
        if run_stage_contract_suite() != 0:
            return 1
        if args.with_full_suite:
            return run_full_repo_suite()
        print("repo_change_gate: hard gate passed (legacy full suite not enforced in pre-commit mode)")
        return 0

    if args.mode == "pre-push":
        if run_stage_contract_suite() != 0:
            return 1
        if args.with_full_suite:
            return run_full_repo_suite()
        print("repo_change_gate: hard gate passed (legacy full suite not enforced in pre-push mode)")
        return 0

    if staged_paths:
        denied = blocked_paths(staged_paths)
        if denied:
            print("repo_change_gate: blocked generated or temporary paths detected:", file=sys.stderr)
            for path in denied:
                print(f"  - {path}", file=sys.stderr)
            return 1
        if run_python_compile(python_source_paths(staged_paths)) != 0:
            return 1
    if run_stage_contract_suite() != 0:
        return 1
    if args.with_full_suite:
        return run_full_repo_suite()
    print("repo_change_gate: hard gate passed (legacy full suite skipped in manual mode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
