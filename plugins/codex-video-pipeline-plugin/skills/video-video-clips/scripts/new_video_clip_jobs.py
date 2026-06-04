#!/usr/bin/env python3
"""Create Stage 06 video clip generation jobs from Stage 04 prompts and Stage 05 keyframe images.

Usage:
  python new_video_clip_jobs.py <locked_brief.json> <storyboard.json> <keyframe_prompts.json> <keyframe_image_manifest.json> <video_clip_manifest.json>
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "providers"))
from pipeline_core.pipeline_blueprints import routing_from_brief  # noqa: E402
from pipeline_core.project_state import load_json_file  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402
from pipeline_core.quality_contracts import build_quality_contract, build_stage_quality_targets  # noqa: E402
from pipeline_core.stage06_route_policy import evaluate_stage06_route_policy  # noqa: E402
from pipeline_core.requirement_compiler import compile_requirements, requested_output_allows_stage, stage_meets_requested_output  # noqa: E402
from pipeline_core.stage06_risk_profiles import classify_stage06_generation  # noqa: E402
from pipeline_core.story_continuity import build_continuity_anchor_text, has_template_leak, key_props_text, pick_story_anchors, shot_anchor_bundle, style_label_from_sources  # noqa: E402
from workflow_mapping import get_workflow_mapping, load_workflow_mapping  # noqa: E402


def load_json(path: Path) -> dict:
    try:
        return load_json_file(path)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def resolve_path(base_json: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    p = Path(str(raw))
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    anchors: list[Path] = []
    seen: set[str] = set()
    for anchor in [Path.cwd(), base_json.parent, *base_json.parents]:
        key = str(anchor.resolve()).lower()
        if key not in seen:
            anchors.append(anchor)
            seen.add(key)
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.exists():
            return candidate
    for anchor in anchors:
        candidate = (anchor / p).resolve()
        if candidate.parent.exists():
            return candidate
    return (base_json.parent / p).resolve()


def parse_visual_spec(brief: dict) -> tuple[str, str, int]:
    normalized = brief.get("normalized") if isinstance(brief.get("normalized"), dict) else {}
    aspect = normalized.get("aspect_ratio") or brief.get("aspect_ratio") or brief.get("visual_spec", {}).get("aspect_ratio") or "9:16"
    resolution = normalized.get("resolution") or brief.get("resolution") or brief.get("visual_spec", {}).get("resolution") or "1080P"
    fps = normalized.get("fps") or brief.get("fps") or brief.get("visual_spec", {}).get("fps") or 24
    try:
        fps = int(fps)
    except Exception:
        fps = 24
    return str(aspect), str(resolution), fps


def provider_strategy_from_brief(brief: dict) -> dict:
    video_generation = brief.get("video_generation") if isinstance(brief.get("video_generation"), dict) else {}
    primary = video_generation.get("primary") or "comfyui_ltx_i2v"
    fallback = video_generation.get("fallback") or ["manual"]
    if isinstance(fallback, str):
        fallback = [fallback]
    duration_range = video_generation.get("clip_duration_sec_range") or [5, 15]
    return {
        "primary": primary,
        "fallback": fallback,
        "execution_mode": "provider_or_manual",
        "clip_duration_sec_range": duration_range,
        "notes": "Use local ComfyUI LTX I2V when available; otherwise manually place generated clips under 06_video_clips/clips/."
    }


def stage06_primary_workflow_entry(provider_priority: list[str]) -> dict | None:
    workflow_name = None
    for provider in provider_priority:
        if provider == "comfyui_ltx_i2v":
            workflow_name = "i2v_ltx"
            break
    if not workflow_name:
        return None
    try:
        mapping_data, _ = load_workflow_mapping()
        return get_workflow_mapping(mapping_data, workflow_name)
    except Exception:
        return None


def image_lookup(image_manifest: dict) -> dict[tuple[str, str], dict]:
    lookup = {}
    for job in image_manifest.get("jobs") or []:
        if isinstance(job, dict):
            shot_id = job.get("shot_id")
            role = job.get("frame_role")
            if shot_id and role:
                lookup[(shot_id, role)] = job
    return lookup


def storyboard_lookup(storyboard: dict) -> dict[str, dict]:
    return {shot.get("shot_id"): shot for shot in storyboard.get("shots") or [] if isinstance(shot, dict) and shot.get("shot_id")}


def realized_keyframe_path(image_manifest_path: Path, job: dict) -> str:
    if not isinstance(job, dict):
        return ""
    raw = job.get("evidence", {}).get("file_path") or job.get("output_path") or ""
    if not raw:
        return ""
    resolved = resolve_path(image_manifest_path, str(raw))
    if resolved is None or not resolved.exists() or not resolved.is_file() or resolved.stat().st_size <= 0:
        return ""
    return str(resolved).replace("\\", "/")


def stage05_formal_progression_ready(image_manifest: dict) -> bool:
    self_check = image_manifest.get("self_check") if isinstance(image_manifest.get("self_check"), dict) else {}
    stage05_mode = str(image_manifest.get("stage05_mode") or "").strip()
    reference_guidance_active = bool(image_manifest.get("reference_guidance_active"))
    return bool(
        self_check.get("ready_for_video_clip_generation")
        and stage05_mode == "reference_guided_storyboard"
        and reference_guidance_active
    )


def request_record(job: dict, provider: str) -> dict:
    return {
        "request_id": f"REQ_{provider.upper()}_{job['clip_id']}",
        "clip_id": job["clip_id"],
        "shot_id": job["shot_id"],
        "provider": provider,
        "start_keyframe_path": job["source_keyframes"]["start"],
        "end_keyframe_path": job["source_keyframes"]["end"],
        "motion_prompt": job["motion_prompt"],
        "performance_prompt": job.get("performance_prompt"),
        "negative_prompt": job["negative_prompt"],
        "duration_sec": job["duration_sec"],
        "fps": job["fps"],
        "aspect_ratio": job["aspect_ratio"],
        "resolution": job["resolution"],
        "output_path": job["output_path"],
        "status": "planned"
    }


def motion_prompt_with_anchor_fallback(existing: str, bundle: dict[str, str], profile: dict[str, object]) -> str:
    text = str(existing or "").strip()
    lower = text.lower()
    stale_motion_markers = [
        "gentle camera movement",
        "preserve identity and continuity",
        "baseline expression",
        "scene anchor",
    ]
    if text and not has_template_leak(text) and not any(marker in lower for marker in stale_motion_markers):
        return text
    action = bundle.get("action") or "推进故事"
    emotion = bundle.get("emotion") or "当前情绪变化"
    location = bundle.get("location") or "当前场景"
    weather = bundle.get("weather") or "当前氛围"
    key_prop = bundle.get("key_prop") or "关键道具"
    expected_subject_count = int(profile.get("expected_subject_count") or 1)
    route_hint = str(profile.get("route_hint") or "").strip()
    if route_hint == "interaction_handoff":
        return (
            f"{action}，镜头只完成一次清晰的交接动作，从起始姿态推进到明确终态。"
            f"{weather}{location}里必须始终保持两个人与同一把{key_prop}同时可读，交接双方身份不能漂移。"
            "机位锁定在稳定正面轴线，不要路人遮挡前景，不要漂浮式微动作，不要额外手臂或重复道具。"
            f"情绪落点保持{emotion}，必须有清晰可见的身体位移与重心变化，重点让握持关系一眼可读。"
        )
    return (
        f"{action}，从起始姿态推进到明确终态，必须有清晰可见的身体位移与重心变化。"
        f"{weather}{location}里，主体要和{key_prop}形成可读的真实交互，手部接触关系明确。"
        f"情绪落点保持{emotion}，镜头内完成一次明确动作，不要漂浮式微动作。"
        f"避免额外手臂、重复道具、错误握持，以及偏离预期的{expected_subject_count}人构图。"
    )


def performance_prompt_with_anchor_fallback(existing: str, bundle: dict[str, str], profile: dict[str, object]) -> str:
    text = str(existing or "").strip()
    if text and not has_template_leak(text):
        return text
    action = bundle.get("action") or "推进故事"
    emotion = bundle.get("emotion") or "当前情绪变化"
    if str(profile.get("route_hint") or "").strip() == "interaction_handoff":
        return f"{action} with restrained handoff timing, readable grip change, no exaggerated arm swing, baseline expression {emotion}."
    return f"{action} with 自然、克制、可停顿, baseline expression {emotion}."


def dialogue_prompt_with_anchor_fallback(existing: str, bundle: dict[str, str], profile: dict[str, object]) -> str:
    text = str(existing or "").strip()
    if text and not has_template_leak(text):
        return text
    emotion = bundle.get("emotion") or "当前情绪变化"
    if str(profile.get("route_hint") or "").strip() == "interaction_handoff":
        return f"Deliver any spoken line with low-key intimacy and clean pauses, matching {emotion}, without breaking the handoff beat."
    return f"Deliver any spoken line with 自然、克制、可停顿, matching {emotion}."


def continuity_prompt_with_anchor_fallback(existing: str, anchors: dict, bundle: dict[str, str], style_label: str) -> str:
    text = str(existing or "").strip()
    location = bundle.get("location") or anchors.get("scene_label") or anchors.get("location")
    subject = anchors.get("subject") or "主体"
    if text and not has_template_leak(text) and subject in text and str(location or "") in text:
        return text
    scene_label = f"{bundle.get('weather') or ''}{location or ''}".strip() or anchors.get("scene_label") or anchors.get("location") or "当前场景"
    primary_line = (
        f"{subject} 在{scene_label}中的外观、服装和道具关系要保持完全一致，便于跨镜头识别。"
    )
    continuity_anchor = build_continuity_anchor_text(subject, scene_label, style_label, anchors.get("key_props") or [])
    return f"{primary_line}; {continuity_anchor}"


def main(argv: list[str]) -> int:
    allow_beyond_scope = "--allow-beyond-requested-scope" in argv
    allow_stage05_in_progress = "--allow-stage05-in-progress" in argv
    argv = [arg for arg in argv if arg not in {"--allow-beyond-requested-scope", "--allow-stage05-in-progress"}]
    if len(argv) != 6:
        print("Usage: python new_video_clip_jobs.py <locked_brief.json> <storyboard.json> <keyframe_prompts.json> <keyframe_image_manifest.json> <video_clip_manifest.json>", file=sys.stderr)
        return 2
    brief_path = Path(argv[1])
    storyboard_path = Path(argv[2])
    prompts_path = Path(argv[3])
    image_manifest_path = Path(argv[4])
    out_path = Path(argv[5])

    brief = load_json(brief_path)
    storyboard = load_json(storyboard_path)
    prompts = load_json(prompts_path)
    image_manifest = load_json(image_manifest_path)

    if brief.get("status") != "locked" or brief.get("confirmed_by_user") is not True:
        print("ERROR: brief must be locked and confirmed_by_user=true", file=sys.stderr)
        return 1
    compiled = compile_requirements(brief)
    if not allow_beyond_scope and not requested_output_allows_stage("STAGE_06", compiled):
        print("ERROR: requested output scope does not allow Stage 06. Re-run with --allow-beyond-requested-scope to override.", file=sys.stderr)
        return 1
    if prompts.get("stage") != "STAGE_04_KEYFRAME_PROMPTS":
        print("ERROR: keyframe_prompts.stage must be STAGE_04_KEYFRAME_PROMPTS", file=sys.stderr)
        return 1
    if image_manifest.get("stage") != "STAGE_05_KEYFRAME_IMAGES":
        print("ERROR: keyframe image manifest stage must be STAGE_05_KEYFRAME_IMAGES", file=sys.stderr)
        return 1
    image_manifest_status = str(image_manifest.get("status") or "").strip()
    image_manifest_mode = str(image_manifest.get("stage05_mode") or "").strip()
    stage05_ready_for_stage06 = stage05_formal_progression_ready(image_manifest)
    allowed_stage05_statuses = {"generated", "confirmed"}
    if allow_stage05_in_progress:
        allowed_stage05_statuses.add("in_progress")
    if image_manifest_status not in allowed_stage05_statuses:
        print("ERROR: keyframe_image_manifest.status must be generated or confirmed before Stage 06", file=sys.stderr)
        print(
            "CREATOR_HINT: 你还没有真正拿到并确认关键帧图片，所以现在不能生成视频片段。"
            " 下一步请先补角色参考图、完成关键帧出图，并在 Stage 05 工作台里完成复核。",
            file=sys.stderr,
        )
        return 1
    if image_manifest_mode != "reference_guided_storyboard":
        print("ERROR: Stage 06 now requires Stage05-B reference_guided_storyboard outputs.", file=sys.stderr)
        print(
            "CREATOR_HINT: 当前 Stage 05 产物还不是正式的 Stage05-B 一致性分镜图。"
            " 请先完成 Stage05-A 主参考图回填，再用 Qwen NextScene 生成 Stage05-B 分镜图。",
            file=sys.stderr,
        )
        return 1

    project_id = brief.get("project_id") or prompts.get("project_id") or image_manifest.get("project_id") or out_path.parents[1].name
    aspect, resolution, fps = parse_visual_spec(brief)
    quality_contract = build_quality_contract(brief, compiled)
    quality_targets = build_stage_quality_targets("STAGE_06", quality_contract)
    provider_priority = list((compiled.get("provider_preferences") or {}).get("stage06_provider_priority") or ["comfyui_ltx_i2v", "manual"])
    primary_workflow_entry = stage06_primary_workflow_entry(provider_priority)
    anchors = pick_story_anchors(brief, max(1, len(prompts.get("shot_prompts") or [])), prompts, storyboard)
    style_label = style_label_from_sources(brief, prompts, storyboard)
    clips_dir = out_path.parent / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    storyboard_ref = str(storyboard_path).replace("\\", "/")
    prompts_ref = str(prompts_path).replace("\\", "/")
    routing = routing_from_brief(brief)

    images = image_lookup(image_manifest)
    story = storyboard_lookup(storyboard)
    jobs = []
    for idx, shot_prompt in enumerate(prompts.get("shot_prompts") or []):
        if not isinstance(shot_prompt, dict):
            continue
        shot_id = shot_prompt.get("shot_id") or f"S{idx+1:03d}"
        sshot = story.get(shot_id, {})
        duration = shot_prompt.get("duration_sec") or sshot.get("duration_sec") or 5
        try:
            duration = float(duration)
        except Exception:
            duration = 5.0
        # Keep open-source I2V clip duration bounded. Flag out-of-range in validator, but scaffold practical values.
        if duration < 1:
            duration = 5.0
        start_job = images.get((shot_id, "start")) or {}
        end_job = images.get((shot_id, "end")) or {}
        mid_job = images.get((shot_id, "mid")) or {}
        start_path = realized_keyframe_path(image_manifest_path, start_job)
        end_path = realized_keyframe_path(image_manifest_path, end_job)
        mid_path = realized_keyframe_path(image_manifest_path, mid_job)
        clip_id = f"CLIP_{shot_id}"
        out_clip = clips_dir / f"{shot_id}.mp4"
        bundle = shot_anchor_bundle(anchors, idx, shot=sshot, shot_prompt=shot_prompt)
        generation_profile = classify_stage06_generation(shot_prompt, sshot, bundle)
        route_policy = evaluate_stage06_route_policy(
            profile=generation_profile,
            workflow_entry=primary_workflow_entry,
            has_mid_guide=bool(mid_path),
        )
        initial_status = "blocked" if route_policy.get("blocked") else "pending"
        initial_notes = ""
        if route_policy.get("blocked"):
            initial_notes = "Blocked before Stage 06 execution: " + " | ".join(route_policy.get("blocking_reasons") or [])
        jobs.append({
            "clip_id": clip_id,
            "shot_id": shot_id,
            "source_stage05_mode": image_manifest_mode,
            "source_storyboard_ref": f"{storyboard_ref}#{shot_id}",
            "source_prompt_ref": f"{prompts_ref}#{shot_id}",
            "source_keyframes": {
                "start": str(start_path).replace("\\", "/"),
                "end": str(end_path).replace("\\", "/"),
                "mid": str(mid_path).replace("\\", "/") if mid_path else "",
            },
            "source_keyframe_image_ids": {
                "start": start_job.get("image_id"),
                "end": end_job.get("image_id"),
                "mid": mid_job.get("image_id"),
            },
            "motion_prompt": motion_prompt_with_anchor_fallback(shot_prompt.get("motion_prompt") or "", bundle, generation_profile),
            "performance_prompt": performance_prompt_with_anchor_fallback(shot_prompt.get("performance_prompt") or "", bundle, generation_profile),
            "dialogue_delivery_prompt": dialogue_prompt_with_anchor_fallback(shot_prompt.get("dialogue_delivery_prompt") or "", bundle, generation_profile),
            "transition_in_prompt": "",
            "transition_out_prompt": "",
            "negative_prompt": shot_prompt.get("negative_prompt") or prompts.get("global_negative_prompt") or "",
            "consistency_prompt": continuity_prompt_with_anchor_fallback(shot_prompt.get("consistency_prompt") or "", anchors, bundle, style_label),
            "camera_prompt": shot_prompt.get("camera_prompt") or "",
            "style_prompt": shot_prompt.get("style_prompt") or "",
            "route_hint": generation_profile.get("route_hint"),
            "generation_risk_profile": generation_profile.get("generation_risk_profile"),
            "camera_lock_required": bool(generation_profile.get("camera_lock_required")),
            "expected_subject_count": generation_profile.get("expected_subject_count"),
            "expected_key_prop_count": generation_profile.get("expected_key_prop_count"),
            "recommended_max_duration_sec": generation_profile.get("recommended_max_duration_sec"),
            "prompt_constraints": generation_profile.get("prompt_constraints") or [],
            "runtime_notes": generation_profile.get("runtime_notes") or "",
            "requires_mid_guide": "mid" in (route_policy.get("required_additional_guides") or []),
            "required_additional_guides": route_policy.get("required_additional_guides") or [],
            "blocking_reasons": route_policy.get("blocking_reasons") or [],
            "workflow_capability_warnings": route_policy.get("warnings") or [],
            "story_anchor_bundle": bundle,
            "story_continuity_anchor": build_continuity_anchor_text(
                anchors.get("subject") or "主体",
                f"{bundle.get('weather') or ''}{bundle.get('location') or anchors.get('scene_label') or ''}".strip() or anchors.get("scene_label") or "当前场景",
                style_label,
                [bundle.get("key_prop")] if bundle.get("key_prop") else (anchors.get("key_props") or []),
            ),
            "character_ids": shot_prompt.get("characters") or [],
            "duration_sec": duration,
            "fps": fps,
            "aspect_ratio": aspect,
            "resolution": resolution,
            "provider_priority": provider_priority,
            "provider": None,
            "status": initial_status,
            "seed": None,
            "output_path": str(out_clip).replace("\\", "/"),
            "evidence": {
                "file_path": str(out_clip).replace("\\", "/"),
                "file_exists": out_clip.exists(),
                "file_size_bytes": out_clip.stat().st_size if out_clip.exists() else 0,
                "created_at": None
            },
            "errors": [],
            "notes": initial_notes
        })

    blocked_count = sum(1 for j in jobs if j.get("status") == "blocked")
    formal_progression_blocked = not stage05_ready_for_stage06
    formal_progression_status = "draft_only" if formal_progression_blocked else "ready_for_formal_progression"
    stage05_gate_note = (
        "Stage 05 review is not cleared yet; Stage 06 stays in draft_only mode and must not formally advance to Stage 07."
        if formal_progression_blocked
        else ""
    )
    manifest = {
        "schema_version": "0.7.0",
        "stage": "STAGE_06_VIDEO_CLIPS",
        "status": "blocked" if blocked_count else "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_storyboard": str(storyboard_path).replace("\\", "/"),
        "source_keyframe_prompts": str(prompts_path).replace("\\", "/"),
        "source_keyframe_image_manifest": str(image_manifest_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "video_provider_strategy": provider_strategy_from_brief(brief),
        "story_anchors": anchors,
        "compiled_requirements": compiled,
        "quality_contract": quality_contract,
        "quality_targets": quality_targets,
        "routing": routing,
        "output_root": str(out_path.parent).replace("\\", "/"),
        "clips_dir": str(clips_dir).replace("\\", "/"),
        "planning_overrides": {
            "allow_beyond_requested_scope": allow_beyond_scope,
            "allow_stage05_in_progress": allow_stage05_in_progress,
            "stage05_gate_ready_for_stage06": stage05_ready_for_stage06,
            "source_stage05_mode": image_manifest_mode,
            "formal_progression_status": formal_progression_status,
        },
        "formal_promotion_status": formal_progression_status,
        "jobs": jobs,
        "summary": {
            "shot_count": len({j["shot_id"] for j in jobs}),
            "expected_clip_count": len(jobs),
            "generated_clip_count": sum(1 for j in jobs if j["evidence"]["file_exists"]),
            "failed_clip_count": 0,
            "blocked_clip_count": blocked_count,
            "total_duration_sec": sum(float(j.get("duration_sec") or 0) for j in jobs)
        },
        "quality_signals": {
            "intent_route_matches_strategy": routing.get("legacy_mode") or requested_output_allows_stage("STAGE_06", compiled),
            "source_stage05_mode_is_reference_guided_storyboard": image_manifest_mode == "reference_guided_storyboard",
            "continuity_sources_present": all(bool((j.get("source_keyframes") or {}).get("start")) and bool((j.get("source_keyframes") or {}).get("end")) for j in jobs),
            "performance_prompts_present": all(bool(j.get("performance_prompt") or j.get("motion_prompt")) for j in jobs),
            "quality_targets_defined": bool(quality_targets),
            "workflow_capability_safe_for_all_jobs": all(not j.get("blocking_reasons") for j in jobs),
        },
        "self_check": {
            "covers_all_storyboard_shots": len(jobs) == len(storyboard.get("shots") or []),
            "has_source_start_and_end_keyframes_for_each_shot": False,
            "all_required_clips_exist": False,
            "ready_for_audio_stage": False,
            "source_stage05_ready_for_video_clip_generation": stage05_ready_for_stage06,
            "formal_progression_ready": False,
            "notes": [
                *[
                    f"{j['clip_id']}: {' | '.join(j.get('blocking_reasons') or [])}"
                    for j in jobs
                    if j.get("blocking_reasons")
                ],
                *([stage05_gate_note] if stage05_gate_note else []),
                *(["Stage 06 now only accepts Stage05-B reference_guided_storyboard outputs."] if image_manifest_mode != "reference_guided_storyboard" else []),
                *([
                    "Stage 06 planning was explicitly allowed while Stage 05 remains in_progress; treat this manifest as a planning refresh, not final readiness."
                ] if allow_stage05_in_progress and image_manifest_status == "in_progress" else [])
            ]
        },
        "allowed_next_stage": None
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "video_clip_jobs.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "comfyui_ltx_i2v_requests.json").write_text(json.dumps({"provider": "comfyui_ltx_i2v", "requests": [request_record(j, "comfyui_ltx_i2v") for j in jobs]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "manual_video_requests.json").write_text(json.dumps({"provider": "manual", "requests": [request_record(j, "manual") for j in jobs]}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path.parent / "video_clip_generation_plan.md").write_text(
        "# Stage 06 Video Clip Generation Plan\n\n"
        f"Project: `{project_id}`\n\n"
        f"Expected clips: {len(jobs)}\n\n"
        "Provider order: ComfyUI LTX I2V → manual placement.\n\n"
        f"Blocked clips at planning time: {blocked_count}\n\n"
        "Do not mark Stage 06 complete until `video_clip_manifest.json` passes final validation.\n",
        encoding="utf-8"
    )
    (out_path.parent / "clip_review.md").write_text(
        "# Stage 06 Clip Review\n\nPending generation. After clips are created, run `sync_video_clip_manifest.py` and final validation.\n",
        encoding="utf-8"
    )
    update_project_manifest_for_stage(
        out_path,
        current_stage="STAGE_06_VIDEO_CLIPS",
        allowed_next_stage=None,
        flags={"video_clips_confirmed": False},
        status="active",
    )
    print(f"VIDEO CLIP JOBS CREATED: {out_path}")
    print(f"EXPECTED_CLIPS: {len(jobs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
