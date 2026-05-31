#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))
if str(THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(THIS_DIR.parent))

from openai_image_client import OpenAIImageError, generate_image, image_size_for_aspect_ratio
from pipeline_core.requirement_compiler import compiled_requirements_from_context, requested_output_scope_guard_message
from provider_config import (
    ConfigError,
    check_comfyui_server,
    check_openai_image_provider,
    get_openai_image_settings,
    load_provider_config,
    validate_provider_config,
)
from stage05_image_utils import (
    append_blocked,
    append_error,
    build_missing_reference_manual_recovery,
    build_provider_prompt,
    effective_negative_prompt,
    load_json,
    missing_character_reference_block,
    resolve_path,
    update_manifest_state,
    utc_now,
    write_json,
)


def request_record(job: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": f"REQ_{settings['provider_name'].upper()}_{job['image_id']}",
        "image_id": job["image_id"],
        "shot_id": job["shot_id"],
        "frame_role": job["frame_role"],
        "provider": settings["provider_name"],
        "model": settings["model"],
        "prompt": job["prompt"],
        "resolved_prompt": build_provider_prompt(job),
        "negative_prompt": effective_negative_prompt(job),
        "aspect_ratio": job.get("aspect_ratio"),
        "resolved_size": image_size_for_aspect_ratio(job.get("aspect_ratio")),
        "output_format": settings["output_format"],
        "quality": settings["quality"],
        "background": settings["background"],
        "output_path": job["output_path"],
        "status": "planned",
        "error_message": None,
        "revised_prompt": None,
        "usage": None,
        "requested_at": None,
        "completed_at": None,
    }


def _record_provider_decision(
    data: dict[str, Any],
    *,
    provider: str,
    decision: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> None:
    data.setdefault("provider_decisions", [])
    data["provider_decisions"].append({
        "provider": provider,
        "decision": decision,
        "reason": reason,
        "details": details or {},
        "created_at": utc_now(),
    })


def _append_fallback_history(
    jobs: list[dict[str, Any]],
    *,
    provider: str,
    outcome: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> None:
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job.setdefault("fallback_history", [])
        job["fallback_history"].append({
            "provider": provider,
            "outcome": outcome,
            "reason": reason,
            "details": details or {},
            "created_at": utc_now(),
        })


def _manual_recovery_payload(manifest_path: Path, reason: str, comfyui_result: dict[str, Any] | None = None) -> dict[str, Any]:
    keyframes_dir = manifest_path.parent / "keyframes"
    keyframes_dir_text = str(keyframes_dir).replace("\\", "/")
    steps = [
        f"1. 修复 OpenAI 或 ComfyUI provider 可用性后，重新运行 Stage 05 执行器。",
        f"2. 如果暂时只能人工兜底，请把最终关键帧图片放到 {keyframes_dir_text}。",
        "3. 放置完成后运行 sync_keyframe_image_manifest.py 刷新 evidence，再做 final validation。",
    ]
    if comfyui_result and comfyui_result.get("error"):
        steps.insert(1, f"1.5. ComfyUI 当前不可用：{comfyui_result['error']}")
    return {
        "status": "required",
        "reason": reason,
        "steps": steps,
        "created_at": utc_now(),
    }

def _run_comfyui_fallback(
    manifest_path: Path,
    *,
    config_path: str | None,
    image_id: str | None,
    allow_beyond_requested_scope: bool,
    fail_fast: bool,
) -> int:
    from run_comfyui_txt2img import main as run_comfyui_main

    argv = [str(manifest_path)]
    if config_path:
        argv.extend(["--config", config_path])
    if image_id:
        argv.extend(["--image-id", image_id])
    if fail_fast:
        argv.append("--fail-fast")
    if allow_beyond_requested_scope:
        argv.append("--allow-beyond-requested-scope")
    return int(run_comfyui_main(argv))


def _remaining_failed_jobs(manifest_path: Path, selected_image_id: str | None = None) -> list[dict[str, Any]]:
    data = load_json(manifest_path)
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    return [
        job
        for job in jobs
        if isinstance(job, dict)
        and job.get("status") != "succeeded"
        and (selected_image_id is None or job.get("image_id") == selected_image_id)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--image-id", default=None, help="Optional single image_id to generate")
    parser.add_argument("--dry-run", action="store_true", help="Only refresh openai_image_requests.json without calling the API")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Allow this executor to run even when the project brief requested an earlier terminal output")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    if data.get("stage") != "STAGE_05_KEYFRAME_IMAGES":
        print("ERROR: manifest.stage must be STAGE_05_KEYFRAME_IMAGES", file=sys.stderr)
        return 1
    if not args.allow_beyond_requested_scope:
        scope_error = requested_output_scope_guard_message("STAGE_05", compiled_requirements_from_context(data))
        if scope_error:
            print(f"ERROR: {scope_error}", file=sys.stderr)
            return 1

    try:
        config, _ = load_provider_config(config_path=args.config)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    config_errors = validate_provider_config(config)
    if config_errors:
        for error in config_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        print("ERROR: manifest.jobs must be a non-empty list", file=sys.stderr)
        return 1

    selected_jobs = [job for job in jobs if isinstance(job, dict) and (args.image_id is None or job.get("image_id") == args.image_id)]
    if args.image_id and not selected_jobs:
        print(f"ERROR: image_id not found in manifest: {args.image_id}", file=sys.stderr)
        return 1
    blocked_jobs_by_image_id: dict[str, dict[str, Any]] = {}
    for job in selected_jobs:
        block = missing_character_reference_block(job)
        if block:
            blocked_jobs_by_image_id[str(job.get("image_id") or "")] = block
    runnable_jobs = [
        job
        for job in selected_jobs
        if isinstance(job, dict) and str(job.get("image_id") or "") not in blocked_jobs_by_image_id
    ]
    fallback_strategy = data.get("image_provider_strategy") if isinstance(data.get("image_provider_strategy"), dict) else {}
    fallback_providers = fallback_strategy.get("fallback") if isinstance(fallback_strategy.get("fallback"), list) else []

    settings = get_openai_image_settings(config)
    if not settings["enabled"]:
        print("ERROR: openai_image.enabled is false", file=sys.stderr)
        return 1
    if not settings["api_key"]:
        print(f"ERROR: missing API key in env var {settings['api_key_env']}", file=sys.stderr)
        return 1

    request_manifest = {
        "provider": settings["provider_name"],
        "model": settings["model"],
        "generated_at": utc_now(),
        "requests": [request_record(job, settings) for job in selected_jobs],
    }
    requests_by_id = {record["image_id"]: record for record in request_manifest["requests"]}
    if blocked_jobs_by_image_id:
        blocked_payload = list(blocked_jobs_by_image_id.values())
        for job in selected_jobs:
            blocked = blocked_jobs_by_image_id.get(str(job.get("image_id") or ""))
            if not blocked:
                continue
            message = (
                f"{blocked['reason']} Missing reference image(s): "
                + ", ".join(str(item) for item in blocked["missing_reference_images"])
            )
            append_blocked(job, settings["provider_name"], message, details=blocked)
            requests_by_id[str(job.get("image_id") or "")].update({
                "status": "blocked",
                "error_message": message,
                "completed_at": utc_now(),
                "blocked_reason": blocked["reason"],
                "missing_reference_images": blocked["missing_reference_images"],
                "reference_images": blocked["reference_images"],
            })
        _record_provider_decision(
            data,
            provider="manual",
            decision="manual_recovery_required",
            reason="missing_character_reference_before_generation",
            details={
                "blocked_image_ids": [item.get("image_id") for item in blocked_payload],
                "missing_reference_images": [
                    path_text
                    for item in blocked_payload
                    for path_text in item.get("missing_reference_images", [])
                ],
            },
        )
        data["manual_recovery"] = build_missing_reference_manual_recovery(manifest_path, blocked_payload)
        data["creator_runtime_status"] = {
            "headline": "已阻断高风险关键帧自动生成，先补角色参考图。",
            "detail": "当前镜头属于 character-locked 高风险镜头，缺少 Stage 03 参考图时继续生图最容易前后换人。",
            "source_provider": settings["provider_name"],
            "active_provider": "manual",
            "created_at": utc_now(),
        }
    write_json(manifest_path.parent / "openai_image_requests.json", request_manifest)
    if not runnable_jobs:
        update_manifest_state(data, manifest_path)
        write_json(manifest_path, data)
        print(f"OPENAI IMAGE GENERATION BLOCKED: {manifest_path}")
        return 1

    provider_ready = check_openai_image_provider(
        config,
        probe=True,
        timeout_seconds=settings["timeout_seconds"],
    )
    if provider_ready["status"] != "ready":
        error_message = provider_ready.get("error") or provider_ready["status"]
        _record_provider_decision(
            data,
            provider=settings["provider_name"],
            decision="failed_preflight",
            reason=provider_ready["status"],
            details=provider_ready,
        )
        _append_fallback_history(
            selected_jobs,
            provider=settings["provider_name"],
            outcome="failed_preflight",
            reason=provider_ready["status"],
            details={"error": error_message},
        )
        comfyui_result = check_comfyui_server(config)
        if "comfyui_txt2img" in fallback_providers and comfyui_result.get("status") == "ready":
            _record_provider_decision(
                data,
                provider="comfyui_txt2img",
                decision="auto_fallback_selected",
                reason="openai_preflight_failed",
                details=comfyui_result,
            )
            data["creator_runtime_status"] = {
                "headline": "OpenAI 不可用，已自动切到本地 ComfyUI。",
                "detail": "本地生成通常更慢，但当前任务会继续完成。",
                "source_provider": "openai_gpt_image2",
                "active_provider": "comfyui_txt2img",
                "created_at": utc_now(),
            }
            write_json(manifest_path, data)
            print("INFO: OpenAI unavailable, automatically switching to local ComfyUI. Generation may be slower.")
            return _run_comfyui_fallback(
                manifest_path,
                config_path=args.config,
                image_id=args.image_id,
                allow_beyond_requested_scope=args.allow_beyond_requested_scope,
                fail_fast=args.fail_fast,
            )

        _record_provider_decision(
            data,
            provider="manual",
            decision="manual_recovery_required",
            reason="no_provider_ready_after_openai_preflight_failure",
            details={"openai": provider_ready, "comfyui": comfyui_result},
        )
        for job in selected_jobs:
            append_error(job, settings["provider_name"], error_message)
            job["notes"] = "OpenAI preflight failed before generation. Manual recovery required."
        data["manual_recovery"] = _manual_recovery_payload(
            manifest_path,
            "OpenAI 鉴权失败且 ComfyUI 不可用，无法自动完成 Stage 05。",
            comfyui_result,
        )
        data["creator_runtime_status"] = {
            "headline": "OpenAI 不可用，且本地 ComfyUI 也未就绪。",
            "detail": "当前无法自动继续，请按 manual recovery 指引处理。",
            "source_provider": "openai_gpt_image2",
            "active_provider": "manual",
            "created_at": utc_now(),
        }
        update_manifest_state(data, manifest_path)
        write_json(manifest_path, data)
        print(
            f"ERROR: OpenAI image provider is not ready before Stage 05 generation "
            f"({provider_ready['status']}): {error_message}",
            file=sys.stderr,
        )
        return 1

    requests_path = manifest_path.parent / "openai_image_requests.json"
    write_json(requests_path, request_manifest)
    if args.dry_run:
        if blocked_jobs_by_image_id:
            update_manifest_state(data, manifest_path)
            write_json(manifest_path, data)
            print(f"OPENAI IMAGE DRY RUN BLOCKED: {manifest_path}")
            return 1
        print(f"OPENAI REQUEST MANIFEST UPDATED: {requests_path}")
        return 0

    failed = False
    for job in runnable_jobs:
        request_item = requests_by_id[job["image_id"]]
        request_item["requested_at"] = utc_now()
        try:
            result = generate_image(
                base_url=settings["base_url"],
                api_key=settings["api_key"],
                model=settings["model"],
                prompt=build_provider_prompt(job),
                output_format=settings["output_format"],
                quality=settings["quality"],
                background=settings["background"],
                size=image_size_for_aspect_ratio(job.get("aspect_ratio")),
                timeout_seconds=settings["timeout_seconds"],
            )
            output_path = resolve_path(manifest_path, job.get("output_path") or job.get("evidence", {}).get("file_path"))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(result["image_bytes"])
            job["provider"] = settings["provider_name"]
            job["status"] = "succeeded"
            job["errors"] = []
            job.setdefault("evidence", {})
            job["evidence"].update({
                "file_path": str(output_path).replace("\\", "/"),
                "file_exists": True,
                "file_size_bytes": output_path.stat().st_size,
                "created_at": utc_now(),
            })
            job["notes"] = f"model={settings['model']}; size={result['size']}; quality={result['quality']}"
            request_item.update({
                "status": "succeeded",
                "completed_at": utc_now(),
                "revised_prompt": result.get("revised_prompt"),
                "usage": result.get("usage"),
            })
        except OpenAIImageError as exc:
            failed = True
            append_error(job, settings["provider_name"], str(exc))
            request_item.update({
                "status": "failed",
                "completed_at": utc_now(),
                "error_message": str(exc),
            })
            if args.fail_fast:
                break

    update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    request_manifest["generated_at"] = utc_now()
    write_json(requests_path, request_manifest)

    if failed:
        failed_jobs = [job for job in runnable_jobs if isinstance(job, dict) and job.get("status") == "failed"]
        if failed_jobs:
            _record_provider_decision(
                data,
                provider=settings["provider_name"],
                decision="partial_failure",
                reason="provider_error_during_generation",
                details={"failed_image_ids": [job.get("image_id") for job in failed_jobs]},
            )
            _append_fallback_history(
                failed_jobs,
                provider=settings["provider_name"],
                outcome="failed_generation",
                reason="provider_error_during_generation",
            )
            comfyui_result = check_comfyui_server(config)
            if "comfyui_txt2img" in fallback_providers and comfyui_result.get("status") == "ready":
                _record_provider_decision(
                    data,
                    provider="comfyui_txt2img",
                    decision="auto_fallback_selected",
                    reason="openai_generation_failed",
                    details={"failed_image_ids": [job.get("image_id") for job in failed_jobs]},
                )
                data["creator_runtime_status"] = {
                    "headline": "OpenAI 生成中失败，已自动切到本地 ComfyUI。",
                    "detail": "本地生成通常更慢，但系统会继续补完剩余关键帧。",
                    "source_provider": "openai_gpt_image2",
                    "active_provider": "comfyui_txt2img",
                    "created_at": utc_now(),
                }
                write_json(manifest_path, data)
                print("INFO: OpenAI generation failed, automatically switching to local ComfyUI for the remaining images.")
                fallback_failed = False
                for job in failed_jobs:
                    exit_code = _run_comfyui_fallback(
                        manifest_path,
                        config_path=args.config,
                        image_id=str(job.get("image_id") or ""),
                        allow_beyond_requested_scope=args.allow_beyond_requested_scope,
                        fail_fast=args.fail_fast,
                    )
                    if exit_code != 0:
                        fallback_failed = True
                        if args.fail_fast:
                            break
                if not fallback_failed and not _remaining_failed_jobs(manifest_path, args.image_id):
                    print(f"OPENAI IMAGE GENERATION RECOVERED VIA COMFYUI FALLBACK: {manifest_path}")
                    return 0
                data = load_json(manifest_path)
                data["manual_recovery"] = _manual_recovery_payload(
                    manifest_path,
                    "OpenAI 生成失败后已尝试自动切换 ComfyUI，但仍有未成功关键帧需要人工补位。",
                    comfyui_result,
                )
                data["creator_runtime_status"] = {
                    "headline": "已切到本地 ComfyUI，但仍有关键帧未修复完成。",
                    "detail": "请优先查看 remaining failed images，并按 manual recovery 指引补位。",
                    "source_provider": "comfyui_txt2img",
                    "active_provider": "manual",
                    "created_at": utc_now(),
                }
                _record_provider_decision(
                    data,
                    provider="manual",
                    decision="manual_recovery_required",
                    reason="fallback_left_failed_jobs",
                    details={"remaining_failed_image_ids": [job.get("image_id") for job in _remaining_failed_jobs(manifest_path, args.image_id)]},
                )
                write_json(manifest_path, data)
                return 1

            data["manual_recovery"] = _manual_recovery_payload(
                manifest_path,
                "OpenAI 生成失败，且 ComfyUI 当前不可用，需要人工补位关键帧。",
                comfyui_result,
            )
            data["creator_runtime_status"] = {
                "headline": "OpenAI 失败，且本地 ComfyUI 当前不可用。",
                "detail": "当前无法自动继续，请按 manual recovery 指引处理。",
                "source_provider": "openai_gpt_image2",
                "active_provider": "manual",
                "created_at": utc_now(),
            }
            _record_provider_decision(
                data,
                provider="manual",
                decision="manual_recovery_required",
                reason="openai_failed_and_comfyui_unavailable",
                details={"openai_failed_image_ids": [job.get("image_id") for job in failed_jobs], "comfyui": comfyui_result},
            )
            write_json(manifest_path, data)
        print(f"OPENAI IMAGE GENERATION COMPLETED WITH FAILURES: {manifest_path}")
        return 1
    if blocked_jobs_by_image_id:
        update_manifest_state(data, manifest_path)
        write_json(manifest_path, data)
        request_manifest["generated_at"] = utc_now()
        write_json(requests_path, request_manifest)
        print(f"OPENAI IMAGE GENERATION BLOCKED: {manifest_path}")
        return 1
    print(f"OPENAI IMAGE GENERATION COMPLETED: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
