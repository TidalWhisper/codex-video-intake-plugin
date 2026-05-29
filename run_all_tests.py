#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGIN = ROOT / "plugins" / "codex-video-pipeline-plugin"
PYTEST_BASETEMP = PLUGIN / ".pytest_tmp"

REQUIRED_ROOT_FILES = [
    ROOT / "VERSION",
    ROOT / "README_快速开始.md",
    ROOT / "INSTALL_WINDOWS_CMD.md",
    ROOT / "CODEX_START_HERE.md",
    ROOT / ".agents" / "plugins" / "marketplace.json",
    ROOT / "install_personal_plugin.cmd",
    ROOT / "verify_package.cmd",
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


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str], cwd: Path) -> None:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd), text=True)
    if p.returncode != 0:
        fail(f"command failed: {' '.join(cmd)}")


def main() -> None:
    print("=== codex-video-intake-plugin wrapper self test ===")
    if (ROOT / "plugins" / "codex-video-intake-plugin").exists():
        fail("old duplicate plugins/codex-video-intake-plugin directory still exists")

    for path in REQUIRED_ROOT_FILES:
        if not path.exists():
            fail(f"missing root file: {path.relative_to(ROOT)}")
    if not PLUGIN.exists():
        fail("missing plugin root: plugins/codex-video-pipeline-plugin")

    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8-sig"))
    plugin_entries = marketplace.get("plugins") or []
    if not any(e.get("name") == "codex-video-pipeline-plugin" and e.get("source", {}).get("path") == "./plugins/codex-video-pipeline-plugin" for e in plugin_entries):
        fail("marketplace does not point to ./plugins/codex-video-pipeline-plugin")
    print("marketplace: OK")

    meta = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    if meta.get("name") != "codex-video-pipeline-plugin":
        fail(f"unexpected plugin name: {meta.get('name')}")
    print("plugin metadata: OK")

    for skill in REQUIRED_SKILLS:
        if not (PLUGIN / "skills" / skill / "SKILL.md").exists():
            fail(f"missing skill: {skill}")
    print("skills: OK")

    py_files = [str(p) for p in PLUGIN.rglob("*.py") if "__pycache__" not in str(p)]
    run([sys.executable, "-m", "py_compile", *py_files], cwd=PLUGIN)
    print("python syntax: OK")

    run([sys.executable, "-m", "pytest", "-q", f"--basetemp={PYTEST_BASETEMP}"], cwd=PLUGIN)
    print("pytest: OK")

    print("SELF TEST PASSED")


if __name__ == "__main__":
    main()
