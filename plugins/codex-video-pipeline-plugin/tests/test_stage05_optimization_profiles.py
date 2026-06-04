#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_CORE = ROOT / "scripts" / "pipeline_core"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


optimization_profiles = load_module(
    "stage05_optimization_profiles_test",
    PIPELINE_CORE / "stage05_optimization_profiles.py",
)


def test_load_stage05_optimization_profiles_is_valid() -> None:
    path = ROOT / "config" / "stage05_optimization_profiles.yaml"
    data, resolved = optimization_profiles.load_stage05_optimization_profiles(path, validate=True)
    assert resolved == path.resolve()
    assert data["default_profile"] == "balanced"
    resolved_profile = optimization_profiles.resolve_stage05_workflow_optimization(
        data,
        "stage05_western_cartoon",
    )
    assert resolved_profile["profile_key"] == "balanced"
    assert resolved_profile["profile_label"] == "Balanced"
    assert resolved_profile["dimension_scale"] == 0.875
    assert resolved_profile["workflow_replacements"]["style_selector"] == "comic_1"


def test_resolve_stage05_optimization_profiles_supports_inheritance_and_override() -> None:
    path = ROOT / "config" / "stage05_optimization_profiles.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    resolved_profile = optimization_profiles.resolve_stage05_workflow_optimization(
        data,
        "stage05_anime_jp",
        requested_profile="quality",
    )
    assert resolved_profile["profile_key"] == "quality"
    assert resolved_profile["dimension_scale"] == 1.0
    assert resolved_profile["workflow_replacements"]["style_selector"] == "anime"


def test_validate_stage05_optimization_profiles_rejects_unknown_profile_key() -> None:
    path = ROOT / "config" / "stage05_optimization_profiles.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["workflow_profiles"]["stage05_realistic_cinematic_amazing_z_photo_original"]["profiles"] = {
        "ultra": {
            "dimension_scale": 1.0,
            "workflow_replacements": {"style_selector": "production_photo"},
        }
    }
    errors = optimization_profiles.validate_stage05_optimization_profiles(data)
    assert any(
        "workflow_profiles.stage05_realistic_cinematic_amazing_z_photo_original.profiles.ultra must exist in profile_catalog"
        in error
        for error in errors
    )
