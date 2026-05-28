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


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
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
        return p
    return (base_json.parent / p).resolve()


def parse_visual_spec(brief: dict) -> tuple[str, str, int]:
    aspect = brief.get("aspect_ratio") or brief.get("visual_spec", {}).get("aspect_ratio") or "9:16"
    resolution = brief.get("resolution") or brief.get("visual_spec", {}).get("resolution") or "1080P"
    fps = brief.get("fps") or brief.get("visual_spec", {}).get("fps") or 24
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


def request_record(job: dict, provider: str) -> dict:
    return {
        "request_id": f"REQ_{provider.upper()}_{job['clip_id']}",
        "clip_id": job["clip_id"],
        "shot_id": job["shot_id"],
        "provider": provider,
        "start_keyframe_path": job["source_keyframes"]["start"],
        "end_keyframe_path": job["source_keyframes"]["end"],
        "motion_prompt": job["motion_prompt"],
        "negative_prompt": job["negative_prompt"],
        "duration_sec": job["duration_sec"],
        "fps": job["fps"],
        "aspect_ratio": job["aspect_ratio"],
        "resolution": job["resolution"],
        "output_path": job["output_path"],
        "status": "planned"
    }


def main(argv: list[str]) -> int:
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
    if prompts.get("stage") != "STAGE_04_KEYFRAME_PROMPTS":
        print("ERROR: keyframe_prompts.stage must be STAGE_04_KEYFRAME_PROMPTS", file=sys.stderr)
        return 1
    if image_manifest.get("stage") != "STAGE_05_KEYFRAME_IMAGES":
        print("ERROR: keyframe image manifest stage must be STAGE_05_KEYFRAME_IMAGES", file=sys.stderr)
        return 1
    if image_manifest.get("status") not in {"generated", "confirmed"}:
        print("ERROR: keyframe_image_manifest.status must be generated or confirmed before Stage 06", file=sys.stderr)
        return 1

    project_id = brief.get("project_id") or prompts.get("project_id") or image_manifest.get("project_id") or out_path.parents[1].name
    aspect, resolution, fps = parse_visual_spec(brief)
    clips_dir = out_path.parent / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

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
        start_path = start_job.get("output_path") or start_job.get("evidence", {}).get("file_path") or ""
        end_path = end_job.get("output_path") or end_job.get("evidence", {}).get("file_path") or ""
        clip_id = f"CLIP_{shot_id}"
        out_clip = clips_dir / f"{shot_id}.mp4"
        jobs.append({
            "clip_id": clip_id,
            "shot_id": shot_id,
            "source_storyboard_ref": f"{str(storyboard_path).replace('\\', '/') }#{shot_id}",
            "source_prompt_ref": f"{str(prompts_path).replace('\\', '/') }#{shot_id}",
            "source_keyframes": {
                "start": str(start_path).replace("\\", "/"),
                "end": str(end_path).replace("\\", "/")
            },
            "source_keyframe_image_ids": {
                "start": start_job.get("image_id"),
                "end": end_job.get("image_id")
            },
            "motion_prompt": shot_prompt.get("motion_prompt") or "",
            "transition_in_prompt": "",
            "transition_out_prompt": "",
            "negative_prompt": shot_prompt.get("negative_prompt") or prompts.get("global_negative_prompt") or "",
            "consistency_prompt": shot_prompt.get("consistency_prompt") or "",
            "camera_prompt": shot_prompt.get("camera_prompt") or "",
            "style_prompt": shot_prompt.get("style_prompt") or "",
            "duration_sec": duration,
            "fps": fps,
            "aspect_ratio": aspect,
            "resolution": resolution,
            "provider_priority": ["comfyui_ltx_i2v", "manual"],
            "provider": None,
            "status": "pending",
            "seed": None,
            "output_path": str(out_clip).replace("\\", "/"),
            "evidence": {
                "file_path": str(out_clip).replace("\\", "/"),
                "file_exists": out_clip.exists(),
                "file_size_bytes": out_clip.stat().st_size if out_clip.exists() else 0,
                "created_at": None
            },
            "errors": [],
            "notes": ""
        })

    manifest = {
        "schema_version": "0.7.0",
        "stage": "STAGE_06_VIDEO_CLIPS",
        "status": "draft",
        "project_id": project_id,
        "source_brief": str(brief_path).replace("\\", "/"),
        "source_storyboard": str(storyboard_path).replace("\\", "/"),
        "source_keyframe_prompts": str(prompts_path).replace("\\", "/"),
        "source_keyframe_image_manifest": str(image_manifest_path).replace("\\", "/"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "video_provider_strategy": provider_strategy_from_brief(brief),
        "output_root": str(out_path.parent).replace("\\", "/"),
        "clips_dir": str(clips_dir).replace("\\", "/"),
        "jobs": jobs,
        "summary": {
            "shot_count": len({j["shot_id"] for j in jobs}),
            "expected_clip_count": len(jobs),
            "generated_clip_count": sum(1 for j in jobs if j["evidence"]["file_exists"]),
            "failed_clip_count": 0,
            "total_duration_sec": sum(float(j.get("duration_sec") or 0) for j in jobs)
        },
        "self_check": {
            "covers_all_storyboard_shots": len(jobs) == len(storyboard.get("shots") or []),
            "has_source_start_and_end_keyframes_for_each_shot": False,
            "all_required_clips_exist": False,
            "ready_for_audio_stage": False,
            "notes": []
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
        "Do not mark Stage 06 complete until `video_clip_manifest.json` passes final validation.\n",
        encoding="utf-8"
    )
    (out_path.parent / "clip_review.md").write_text(
        "# Stage 06 Clip Review\n\nPending generation. After clips are created, run `sync_video_clip_manifest.py` and final validation.\n",
        encoding="utf-8"
    )
    print(f"VIDEO CLIP JOBS CREATED: {out_path}")
    print(f"EXPECTED_CLIPS: {len(jobs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
