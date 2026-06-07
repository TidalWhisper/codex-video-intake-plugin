#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTEST_BASETEMP = ROOT / ".pytest_tmp"

REQUIRED_FILES = [
    ROOT / "VERSION",
    ROOT / "README_快速开始.md",
    ROOT / "INSTALL_WINDOWS_CMD.md",
    ROOT / "verify_package.cmd",
    ROOT / "install_personal_plugin.cmd",
    ROOT / ".codex-plugin" / "plugin.json",
    ROOT / "CODEX_START_HERE.md",
    ROOT / "docs" / "PROVIDER_INTEGRATION_CONTRACTS.md",
    ROOT / "docs" / "COMFYUI_WORKFLOW_EXPORT_GUIDE.md",
    ROOT / "docs" / "CODEX_LOCAL_TASK_RUNBOOK.md",
    ROOT / "docs" / "STAGE00_STAGE02_ARCHITECTURE_CONTRACT.md",
    ROOT / "docs" / "STAGE05_MAINLINE_GUARDRAILS.md",
    ROOT / "config" / "providers.example.yaml",
    ROOT / "config" / "workflow_node_mapping.example.yaml",
    ROOT / "workflows" / "comfyui" / "README_WORKFLOWS.md",
]

REQUIRED_SKILLS = [
    "video-production-pipeline",
    "video-project-intake",
    "video-script-generation",
    "video-storyboard-generation",
    "video-character-bible",
    "video-keyframe-prompts",
    "video-keyframe-images",
    "video-video-clips",
    "video-audio",
    "video-assembly",
    "video-qa-delivery",
]


def run(cmd: list[str], cwd: Path | None = None) -> int:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd or ROOT), text=True)
    return p.returncode


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    print("=== codex-video-pipeline-plugin self test ===")
    if (ROOT / "plugins" / "codex-video-intake-plugin").exists():
        fail("old nested plugins/codex-video-intake-plugin directory still exists")

    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing required file: {path.relative_to(ROOT)}")
    print("required files: OK")

    for skill in REQUIRED_SKILLS:
        skill_md = ROOT / "skills" / skill / "SKILL.md"
        if not skill_md.exists():
            fail(f"missing skill: {skill_md.relative_to(ROOT)}")
    print("required skills: OK")

    try:
        meta = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    except Exception as exc:
        fail(f"invalid plugin.json: {exc}")
    if meta.get("name") != "codex-video-pipeline-plugin":
        fail(f"unexpected plugin name: {meta.get('name')}")
    print("plugin metadata: OK")

    py_files = [str(p) for p in ROOT.rglob("*.py") if "__pycache__" not in str(p)]
    if run([sys.executable, "-m", "py_compile", *py_files]) != 0:
        fail("python syntax check failed")
    print("python syntax: OK")

    result = subprocess.run([sys.executable, "-m", "pytest", "-q", f"--basetemp={PYTEST_BASETEMP}"], cwd=str(ROOT), text=True)
    if result.returncode != 0:
        fail("pytest failed")
    print("pytest: OK")

    print("SELF TEST PASSED")


if __name__ == "__main__":
    main()
