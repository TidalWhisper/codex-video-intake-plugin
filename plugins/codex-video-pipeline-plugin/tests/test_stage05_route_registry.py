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


stage05_route_registry = load_module(
    "stage05_route_registry_test",
    PIPELINE_CORE / "stage05_route_registry.py",
)


def test_load_stage05_route_registry_is_valid() -> None:
    path = ROOT / "config" / "stage05_route_registry.yaml"
    data, resolved = stage05_route_registry.load_stage05_route_registry(path, validate=True)
    assert resolved == path.resolve()
    assert data["schema_version"] == "0.1.0"
    assert data["stage05_policy"]["provider_order"] == ["comfyui_txt2img", "manual"]

    route_key, style_entry, route_entry = stage05_route_registry.get_stage05_route_for_style(data, "日系动画风（日本动漫感）")
    assert route_key == "anime_jp"
    assert style_entry["primary_route"] == "anime_jp"
    assert route_entry["current_workflow_mapping_key"] == "stage05_anime_jp"
    assert route_entry["current_workflow_target"] == "amazing_z_image_a_safetensors"
    target = stage05_route_registry.resolve_current_comfyui_target(route_key, route_entry)
    assert target["workflow_mapping_key"] == "stage05_anime_jp"
    assert target["workflow_name"] == "amazing_z_image_a_safetensors"
    assert target["preferred_workflow_source_ref"] == "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json"
    assert target["preferred_workflow_format"] == "ui_graph"

    cn_route_key, _, cn_route_entry = stage05_route_registry.get_stage05_route_for_style(data, "国漫动画风（中国动画/新国风）")
    assert cn_route_key == "anime_cn_newguofeng"
    assert cn_route_entry["current_workflow_mapping_key"] == "stage05_anime_jp"
    assert cn_route_entry["current_workflow_target"] == "amazing_z_image_a_safetensors"

    guofeng_route_key, guofeng_style_entry, guofeng_route_entry = stage05_route_registry.get_stage05_route_for_style(data, "国风水墨/古风")
    assert guofeng_route_key == "guofeng_ink"
    guofeng_preset = stage05_route_registry.resolve_route_style_preset(guofeng_style_entry, guofeng_route_entry)
    assert guofeng_preset["preset_key"] == "elegant_single_subject_umbrella"
    scenic_preset = stage05_route_registry.resolve_named_style_preset(guofeng_route_entry, "scenic_single_subject_umbrella")
    assert scenic_preset["style_selector"] == "whimsical_watercolor"
    assert "scenic medium-wide guofeng illustration" in scenic_preset["positive_anchor"]

    stylized_route_key, stylized_style_entry, stylized_route_entry = stage05_route_registry.get_stage05_route_for_style(data, "赛博朋克")
    assert stylized_route_key == "stylized_concept"
    assert stylized_route_entry["current_workflow_mapping_key"] == "stage05_western_cartoon"
    assert stylized_route_entry["current_workflow_target"] == "amazing_z_comics_safetensors"
    stylized_preset = stage05_route_registry.resolve_route_style_preset(stylized_style_entry, stylized_route_entry)
    assert stylized_preset["preset_key"] == "cyberpunk_neon"
    assert stylized_preset["style_selector"] == "digital_cyberpunk"
    stylized_target = stage05_route_registry.resolve_current_comfyui_target(stylized_route_key, stylized_route_entry)
    assert stylized_target["workflow_mapping_key"] == "stage05_western_cartoon"
    assert stylized_target["workflow_name"] == "amazing_z_comics_safetensors"
    assert stylized_target["preferred_workflow_source_ref"] == "F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-comics_SAFETENSORS.json"
    assert stylized_target["preferred_workflow_format"] == "ui_graph"

    game_cg_route_key, game_cg_style_entry, game_cg_route_entry = stage05_route_registry.get_stage05_route_for_style(data, "游戏CG感")
    assert game_cg_route_key == "game_cg"
    assert game_cg_route_entry["current_workflow_mapping_key"] == "stage05_western_cartoon"
    game_cg_preset = stage05_route_registry.resolve_route_style_preset(game_cg_style_entry, game_cg_route_entry)
    assert game_cg_preset["style_selector"] == "comic_book_cover"

    realistic_route_key, _, realistic_route_entry = stage05_route_registry.get_stage05_route_for_style(data, "写实电影感")
    assert realistic_route_key == "realistic_cinematic"
    assert realistic_route_entry["current_workflow_mapping_key"] == "stage05_realistic_cinematic_amazing_z_photo_original"
    assert realistic_route_entry["current_workflow_target"] == "amazing_z_photo_safetensors"
    realistic_default_preset = stage05_route_registry.resolve_route_style_preset(
        data["stage00_style_to_route"]["写实电影感"],
        realistic_route_entry,
    )
    assert realistic_default_preset["preset_key"] == "classic_film_realism"
    assert realistic_default_preset["style_selector"] == "classic_film_photo"
    realistic_establishing_preset = stage05_route_registry.resolve_named_style_preset(realistic_route_entry, "environmental_establishing_film")
    assert realistic_establishing_preset["style_selector"] == "classic_film_photo"
    assert "story-world environmental establishing shot" in realistic_establishing_preset["positive_anchor"]
    assert "prompt_only_target" not in realistic_route_entry
    assert "reference_guided_target" not in realistic_route_entry


def test_resolve_stage05_route_registry_path_returns_primary_when_missing(tmp_path: Path) -> None:
    resolved = stage05_route_registry.resolve_stage05_route_registry_path(root=tmp_path)
    assert resolved == (tmp_path / "config" / "stage05_route_registry.yaml").resolve()


def test_load_stage05_route_registry_requires_real_file(tmp_path: Path) -> None:
    try:
        stage05_route_registry.load_stage05_route_registry(root=tmp_path)
    except stage05_route_registry.RouteRegistryError as exc:
        assert "config/stage05_route_registry.yaml is required" in str(exc)
    else:
        raise AssertionError("expected RouteRegistryError for missing registry")


def test_validate_stage05_route_registry_rejects_unknown_primary_route() -> None:
    data = yaml.safe_load((ROOT / "config" / "stage05_route_registry.yaml").read_text(encoding="utf-8"))
    data["stage00_style_to_route"]["写实电影感"]["primary_route"] = "missing_route"
    errors = stage05_route_registry.validate_stage05_route_registry(data)
    assert any("references unknown route: missing_route" in error for error in errors)


def test_validate_stage05_route_registry_rejects_candidate_without_workflow_candidates() -> None:
    data = yaml.safe_load((ROOT / "config" / "stage05_route_registry.yaml").read_text(encoding="utf-8"))
    data["routes"]["anime_jp"]["workflow_candidates"] = []
    errors = stage05_route_registry.validate_stage05_route_registry(data)
    assert any("routes.anime_jp.workflow_candidates must be non-empty unless status=backlog" in error for error in errors)


def test_validate_stage05_route_registry_rejects_unknown_preferred_workflow_candidate() -> None:
    data = yaml.safe_load((ROOT / "config" / "stage05_route_registry.yaml").read_text(encoding="utf-8"))
    data["routes"]["stylized_concept"]["adoption_strategy"]["preferred_workflow_candidate"] = "missing_workflow"
    errors = stage05_route_registry.validate_stage05_route_registry(data)
    assert any(
        "routes.stylized_concept.adoption_strategy.preferred_workflow_candidate must match one workflow_candidates.workflow_name"
        in error
        for error in errors
    )


def test_load_stage05_route_registry_raises_for_invalid_yaml(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "stage05_route_registry.yaml"
    path.write_text("stage05_policy: [\n", encoding="utf-8")
    try:
        stage05_route_registry.load_stage05_route_registry(path)
    except stage05_route_registry.RouteRegistryError as exc:
        assert "not valid YAML" in str(exc)
    else:
        raise AssertionError("expected RouteRegistryError for invalid YAML")
