#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "scripts" / "providers"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


scene_matrix_smoke = load_module("stage05_scene_matrix_smoke_test", PROVIDERS / "run_stage05_scene_matrix_smoke.py")


def test_scene_matrix_smoke_prepare_only_creates_multi_pack_manifests(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(scene_matrix_smoke, "ROOT", tmp_path)
    monkeypatch.setattr(scene_matrix_smoke, "TEMPLATES", ROOT / "templates")
    monkeypatch.setattr(scene_matrix_smoke, "IMAGES", ROOT / "skills" / "video-keyframe-images" / "scripts")

    prefix = "stage05_scene_matrix_test"
    summary_path = tmp_path / "video_projects" / f"{prefix}_summary.json"
    assert scene_matrix_smoke.main([
        "--scene-pack",
        "realistic_review_pack",
        "--scene-pack",
        "guofeng_review_pack",
        "--scene-pack",
        "stylized_review_pack",
        "--project-prefix",
        prefix,
        "--summary-out",
        str(summary_path),
    ]) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["project_prefix"] == prefix
    assert summary["provider"] == "comfyui_txt2img"
    assert summary["executed_packs"] == []
    assert len(summary["prepared_packs"]) == 3

    prepared = {item["pack_key"]: item for item in summary["prepared_packs"]}
    assert prepared["realistic_review_pack"]["stage05_route_key"] == "realistic_cinematic"
    assert prepared["guofeng_review_pack"]["stage05_route_key"] == "guofeng_ink"
    assert prepared["stylized_review_pack"]["normalized_style"] == "游戏CG感"
    assert prepared["stylized_review_pack"]["stage05_route_key"] == "game_cg"
    assert prepared["realistic_review_pack"]["quality_review"]["risky_image_count"] == 4
    assert prepared["guofeng_review_pack"]["quality_review"]["risky_image_count"] == 6
    assert prepared["realistic_review_pack"]["semantic_review_template"][0]["expected_subject_count"] == 1
    assert "不能多手多脚" in prepared["realistic_review_pack"]["semantic_review_template"][0]["must_match"][-1]


def test_scene_matrix_smoke_prepare_only_supports_realistic_expanded_packs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(scene_matrix_smoke, "ROOT", tmp_path)
    monkeypatch.setattr(scene_matrix_smoke, "TEMPLATES", ROOT / "templates")
    monkeypatch.setattr(scene_matrix_smoke, "IMAGES", ROOT / "skills" / "video-keyframe-images" / "scripts")

    prefix = "stage05_realistic_expanded_test"
    summary_path = tmp_path / "video_projects" / f"{prefix}_summary.json"
    assert scene_matrix_smoke.main([
        "--scene-pack",
        "realistic_establishing_expanded_pack",
        "--scene-pack",
        "realistic_healing_expanded_pack",
        "--scene-pack",
        "realistic_editorial_expanded_pack",
        "--project-prefix",
        prefix,
        "--summary-out",
        str(summary_path),
    ]) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    prepared = {item["pack_key"]: item for item in summary["prepared_packs"]}

    assert len(prepared) == 3
    assert prepared["realistic_establishing_expanded_pack"]["stage05_route_key"] == "realistic_cinematic"
    assert prepared["realistic_healing_expanded_pack"]["stage05_route_key"] == "realistic_cinematic"
    assert prepared["realistic_editorial_expanded_pack"]["stage05_route_key"] == "realistic_cinematic"
    assert prepared["realistic_establishing_expanded_pack"]["normalized_style"] == "写实电影感"
    assert prepared["realistic_healing_expanded_pack"]["normalized_style"] == "温暖治愈"
    assert prepared["realistic_editorial_expanded_pack"]["normalized_style"] == "广告高级感"
    assert all(
        item["expected_subject_count"] == 1
        for pack in prepared.values()
        for item in pack["semantic_review_template"]
    )
    assert all(
        "镜头与构图大方向一致" in item["must_match"][1]
        for pack in prepared.values()
        for item in pack["semantic_review_template"]
    )


def test_scene_matrix_smoke_summary_refreshes_manifest_after_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(scene_matrix_smoke, "ROOT", tmp_path)
    monkeypatch.setattr(scene_matrix_smoke, "TEMPLATES", ROOT / "templates")
    monkeypatch.setattr(scene_matrix_smoke, "IMAGES", ROOT / "skills" / "video-keyframe-images" / "scripts")

    def fake_run_scene_pack_images(**kwargs):
        manifest_path = Path(kwargs["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        first_job = manifest["jobs"][0]
        first_job["status"] = "generated"
        first_job["provider"] = "comfyui_txt2img"
        first_job["output_path"] = "05_images/keyframes/S001_start.png"
        manifest["allowed_next_stage"] = "manual_review_required"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "pack_key": kwargs["pack"].pack_key,
            "manifest_path": str(manifest_path).replace("\\", "/"),
            "provider": "comfyui_txt2img",
            "selected_role": "start",
            "results": [{"image_id": first_job["image_id"], "exit_code": 0, "job_status": "generated"}],
            "quality_review": manifest.get("quality_review"),
            "self_check": manifest.get("self_check"),
            "allowed_next_stage": manifest.get("allowed_next_stage"),
        }

    monkeypatch.setattr(scene_matrix_smoke, "run_scene_pack_images", fake_run_scene_pack_images)

    prefix = "stage05_scene_matrix_test_run"
    summary_path = tmp_path / "video_projects" / f"{prefix}_summary.json"
    assert scene_matrix_smoke.main([
        "--scene-pack",
        "stylized_review_pack",
        "--project-prefix",
        prefix,
        "--run",
        "--summary-out",
        str(summary_path),
    ]) == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert len(summary["executed_packs"]) == 1

    prepared = summary["prepared_packs"][0]
    assert prepared["stage05_route_key"] == "game_cg"
    assert prepared["allowed_next_stage"] == "manual_review_required"
    assert prepared["jobs"][0]["status"] == "generated"
    assert prepared["jobs"][0]["provider"] == "comfyui_txt2img"
    assert prepared["semantic_review_template"][0]["start_image_id"] == "IMG_S001_START"
