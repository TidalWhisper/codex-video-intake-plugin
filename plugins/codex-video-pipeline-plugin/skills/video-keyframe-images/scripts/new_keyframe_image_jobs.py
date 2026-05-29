#!/usr/bin/env python3
"""Create Stage 05 keyframe image generation jobs from Stage 04 prompts.

Usage:
  python new_keyframe_image_jobs.py <locked_brief.json> <keyframe_prompts.json> <keyframe_image_manifest.json>
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from pipeline_core.pipeline_blueprints import routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.quality_contracts import build_quality_contract, build_stage_quality_targets  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage, stage_meets_requested_output  # noqa: E402


STYLE_FAMILY_TO_WORKFLOW = {
    "realistic": "txt2img_keyframe_realistic",
    "anime": "txt2img_keyframe_anime",
    "guofeng": "txt2img_keyframe_guofeng",
    "stylized": "txt2img_keyframe_stylized",
}

ANIME_STYLE_HINTS = (
    "日系动画",
    "日本动漫",
    "国漫动画",
    "中国动画",
    "美式动画",
    "卡通",
    "动漫",
    "anime",
    "manga",
    "cel shading",
    "cel-shading",
    "key visual",
    "line art",
)
GUOFENG_STYLE_HINTS = (
    "国风水墨",
    "古风",
    "国风",
    "水墨",
    "guofeng",
    "ink wash",
    "brush texture",
    "poetic composition",
)
STYLIZED_STYLE_HINTS = (
    "赛博朋克",
    "暗黑惊悚",
    "高饱和潮流",
    "游戏cg",
    "游戏CG",
    "stylized",
    "concept art",
    "illustrative rendering",
    "bold shape design",
    "dramatic color",
)


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def parse_visual_spec(brief: dict) -> tuple[str, str]:
    # Supports both old brief fields and v0.1+ user-answer-derived fields.
    aspect = brief.get("aspect_ratio") or brief.get("visual_spec", {}).get("aspect_ratio") or "9:16"
    resolution = brief.get("resolution") or brief.get("visual_spec", {}).get("resolution") or "1080P"
    return str(aspect), str(resolution)


def normalized_brief(brief: dict) -> dict:
    normalized = brief.get("normalized")
    return normalized if isinstance(normalized, dict) else brief


def infer_style_family(brief: dict, prompts: dict) -> str:
    normalized = normalized_brief(brief)
    style = str(normalized.get("style") or brief.get("style") or "").strip()
    genre = str(normalized.get("genre") or brief.get("genre") or "").strip()
    joined = " ".join(
        [
            style,
            genre,
            str(prompts.get("prompt_language") or ""),
            *[
                str(shot.get("style_prompt") or "")
                for shot in (prompts.get("shot_prompts") or [])
                if isinstance(shot, dict)
            ],
        ]
    ).lower()
    if any(keyword.lower() in joined for keyword in ANIME_STYLE_HINTS):
        return "anime"
    if any(keyword.lower() in joined for keyword in GUOFENG_STYLE_HINTS):
        return "guofeng"
    if any(keyword.lower() in joined for keyword in STYLIZED_STYLE_HINTS):
        return "stylized"
    return "realistic"


def provider_strategy_from_brief(brief: dict) -> dict:
    compiled = compile_requirements(brief)
    configured_priority = list((compiled.get("provider_preferences") or {}).get("stage05_provider_priority") or [])
    image_generation = brief.get("image_generation") if isinstance(brief.get("image_generation"), dict) else {}
    primary = image_generation.get("primary") or (configured_priority[0] if configured_priority else "openai_gpt_image2")
    fallback = image_generation.get("fallback") or (configured_priority[1:] if len(configured_priority) > 1 else ["comfyui_txt2img", "manual"])
    if isinstance(fallback, str):
        fallback = [fallback]
    return {
        "primary": primary,
        "fallback": fallback,
        "execution_mode": "provider_or_manual",
        "notes": "Use OpenAI image generation when available; otherwise use local ComfyUI or manually place generated images under 05_images/keyframes/."
    }


def request_record(job: dict, provider: str) -> dict:
    return {
        "request_id": f"REQ_{provider.upper()}_{job['image_id']}",
        "image_id": job["image_id"],
        "shot_id": job["shot_id"],
        "frame_role": job["frame_role"],
        "provider": provider,
        "style_family": job.get("style_family"),
        "comfyui_workflow_name": job.get("comfyui_workflow_name"),
        "prompt": job["prompt"],
        "negative_prompt": job["negative_prompt"],
        "aspect_ratio": job["aspect_ratio"],
        "resolution": job["resolution"],
        "output_path": job["output_path"],
        "status": "planned"
    }


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    argv = [arg for arg in argv if arg != "--allow-beyond-requested-scope"]
    if len(argv) != 4:
        print("Usage: python new_keyframe_image_jobs.py <locked_brief.json> <keyframe_prompts.json> <keyframe_image_manifest.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    prompts_path = Path(argv[2])
    out_path = Path(argv[3])
    brief = load_json(brief_path)
    prompts = load_json(prompts_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_05", compiled):
        print("ERROR: requested output scope does not allow Stage 05. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if prompts.get("stage") != "STAGE_04_KEYFRAME_PROMPTS":
        print("ERROR: keyframe_prompts.stage must be STAGE_04_KEYFRAME_PROMPTS", file=sys.stderr)
        return 1
    if prompts.get("status") not in {"draft", "confirmed"}:
        print("ERROR: keyframe_prompts.status must be draft or confirmed", file=sys.stderr)
        return 1

    project_id = brief.get("project_id") or prompts.get("project_id") or out_path.parents[1].name
    aspect, resolution = parse_visual_spec(brief)
    style_family = infer_style_family(brief, prompts)
    comfyui_workflow_name = STYLE_FAMILY_TO_WORKFLOW[style_family]
    quality_contract = build_quality_contract(brief, compiled)
    quality_targets = build_stage_quality_targets("STAGE_05", quality_contract)
    provider_priority = list((compiled.get("provider_preferences") or {}).get("stage05_provider_priority") or ["openai_gpt_image2", "comfyui_txt2img", "manual"])
    keyframes_dir = out_path.parent / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    prompts_ref = str(prompts_path).replace("\\", "/")
    routing = routing_from_brief(brief)

    jobs = []
    for idx, shot in enumerate(prompts.get("shot_prompts") or []):
        if not isinstance(shot, dict):
            continue
        shot_id = shot.get("shot_id") or f"S{idx+1:03d}"
        for frame_role, prompt_key in [("start", "start_keyframe_prompt"), ("end", "end_keyframe_prompt")]:
            image_id = f"IMG_{shot_id}_{frame_role.upper()}"
            output_path = keyframes_dir / f"{shot_id}_{frame_role}.png"
            jobs.append({
                "image_id": image_id,
                "shot_id": shot_id,
                "frame_role": frame_role,
                "source_prompt_ref": f"{prompts_ref}#{shot_id}.{frame_role}",
                "prompt": shot.get(prompt_key) or "",
                "negative_prompt": shot.get("negative_prompt") or prompts.get("global_negative_prompt") or "",
                "consistency_prompt": shot.get("consistency_prompt") or "",
                "style_prompt": shot.get("style_prompt") or "",
                "camera_prompt": shot.get("camera_prompt") or "",
                "style_family": style_family,
                "comfyui_workflow_name": comfyui_workflow_name,
                "aspect_ratio": aspect,
                "resolution": resolution,
                "provider_priority": provider_priority,
                "provider": None,
                "status": "pending",
                "seed": None,
                "output_path": str(output_path).replace("\\", "/"),
                "evidence": {
                    "file_path": str(output_path).replace("\\", "/"),
                    "file_exists": output_path.exists(),
                    "file_size_bytes": output_path.stat().st_size if output_path.exists() else 0,
                    "created_at": None
                },
                "errors": [],
                "notes": ""
            })

    manifest = {
        "schema_version": "0.6.0",
        "stage": "STAGE_05_KEYFRAME_IMAGES",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_keyframe_prompts": str(prompts_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "image_provider_strategy": provider_strategy_from_brief(brief),
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing,
        "output_root": str(out_path.parent).replace("\\", "/"),
        "keyframes_dir": str(keyframes_dir).replace("\\", "/"),
        "style_family": style_family,
        "comfyui_workflow_router": STYLE_FAMILY_TO_WORKFLOW,
        "jobs": jobs,
        "summary": {
            "shot_count": len({j["shot_id"] for j in jobs}),
            "expected_image_count": len(jobs),
            "generated_image_count": sum(1 for j in jobs if j["evidence"]["file_exists"]),
            "failed_image_count": 0
        },
        "quality_signals": {
            "intent_route_matches_strategy": routing.get("legacy_mode") or requested_output_allows_stage("STAGE_05", compiled),
            "style_route_matches_strategy": style_family == compiled.get("visual_family_hint"),
            "consistency_prompts_present": all(bool(j.get("consistency_prompt")) for j in jobs),
            "quality_targets_defined": bool(quality_targets),
        },
        "self_check": {
            "covers_all_keyframe_prompts": len(jobs) == 2 * len(prompts.get("shot_prompts") or []),
            "has_start_and_end_for_each_shot": True,
            "all_required_images_exist": False,
            "ready_for_video_clip_generation": False,
            "notes": []
        },
        "allowed_next_stage": None
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "image_generation_jobs.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "openai_image_requests.json").write_text(json.dumps({"provider": "openai_gpt_image2", "requests": [request_record(j, "openai_gpt_image2") for j in jobs]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "comfyui_image_requests.json").write_text(json.dumps({"provider": "comfyui_txt2img", "requests": [request_record(j, "comfyui_txt2img") for j in jobs]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "image_generation_plan.md").write_text(
        "# Stage 05 Keyframe Image Generation Plan\n\n"
        f"Project: `{project_id}`\n\n"
        f"Style family: `{style_family}`\n\n"
        f"ComfyUI workflow route: `{comfyui_workflow_name}`\n\n"
        f"Expected images: {len(jobs)}\n\n"
        "Provider order: OpenAI image → ComfyUI txt2img → manual placement.\n\n"
        "Do not mark Stage 05 complete until `keyframe_image_manifest.json` passes final validation.\n",
        encoding="utf-8"
    )
    (out_path.parent / "image_review.md").write_text(
        "# Stage 05 Image Review\n\nPending generation. After files are created, run `sync_keyframe_image_manifest.py` and final validation.\n",
        encoding="utf-8"
    )
    print(f"KEYFRAME IMAGE JOBS CREATED: {out_path}")
    print(f"EXPECTED_IMAGES: {len(jobs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
