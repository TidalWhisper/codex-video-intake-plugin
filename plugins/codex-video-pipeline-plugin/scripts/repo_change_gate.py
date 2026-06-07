#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

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


def print_blocked_paths(denied: list[str]) -> int:
    if not denied:
        return 0
    print("repo_change_gate: blocked generated or temporary paths detected:", file=sys.stderr)
    for path in denied:
        print(f"  - {path}", file=sys.stderr)
    return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("pre-commit", "pre-push", "manual"), default="manual")
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

    if args.mode == "pre-push":
        print("repo_change_gate: pre-push gate skipped (temporary-file blocking is enforced at commit time)")
        return 0

    if not staged_paths:
        staged_paths = list_staged_paths()
    if not staged_paths:
        print("repo_change_gate: no staged changes, skipping")
        return 0

    denied = blocked_paths(staged_paths)
    if denied:
        return print_blocked_paths(denied)

    print("repo_change_gate: staged paths passed temporary-file gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
