#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "providers"))

from provider_config import (  # noqa: E402
    ConfigError,
    check_comfyui_server,
    check_openai_image_provider,
    load_provider_config,
    validate_provider_config,
)
import run_comfyui_txt2img  # noqa: E402
import run_openai_gpt_image2  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def refresh_manifest_prompt_patch_artifacts(manifest_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    # Rebuild review/prompt-patch artifacts from the current runtime code before
    # selecting rerun targets, so D-mode auto-reruns never keep using a stale
    # prompt_patch_plan.json from an older storefront-repair rule set.
    run_comfyui_txt2img.update_manifest_state(data, manifest_path)
    write_json(manifest_path, data)
    return data


def top_patch_items(manifest_path: Path, data: dict[str, Any]) -> list[dict[str, Any]]:
    plan_path = manifest_path.parent / "prompt_patch_plan.json"
    if plan_path.exists():
        plan = load_json(plan_path)
        patches = plan.get("all_prompt_patches")
        if isinstance(patches, list):
            return [item for item in patches if isinstance(item, dict)]
        patches = plan.get("top_prompt_patches")
        if isinstance(patches, list):
            return [item for item in patches if isinstance(item, dict)]
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    cards = quality_review.get("top_review_cards")
    if isinstance(cards, list):
        return [item for item in cards if isinstance(item, dict)]
    return []


def manually_cleared_image_ids(data: dict[str, Any]) -> set[str]:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    cleared: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        gate = job.get("quality_gate") if isinstance(job.get("quality_gate"), dict) else {}
        status = str(gate.get("manual_review_status") or "").strip().lower()
        image_id = str(job.get("image_id") or "").strip()
        if image_id and status in {"approved", "waived", "not_required"}:
            cleared.add(image_id)
    return cleared


def previously_succeeded_image_ids(manifest_path: Path) -> set[str]:
    report_path = manifest_path.parent / "prompt_patch_rerun_report.json"
    if not report_path.exists():
        return set()
    report = load_json(report_path)
    results = report.get("results")
    if not isinstance(results, list):
        return set()
    succeeded: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").strip().lower() != "succeeded":
            continue
        image_id = str(item.get("image_id") or "").strip()
        if image_id:
            succeeded.add(image_id)
    return succeeded


def remaining_pending_patch_items(data: dict[str, Any], *, include_cleared: bool = False) -> list[dict[str, Any]]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []
    cleared = manually_cleared_image_ids(data)
    pending: list[dict[str, Any]] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        image_id = str(item.get("image_id") or "").strip()
        if not image_id:
            continue
        if not include_cleared and image_id in cleared:
            continue
        pending.append(item)
    return pending


def provider_priority_for_manifest(data: dict[str, Any]) -> list[str]:
    compiled = data.get("compiled_requirements") if isinstance(data.get("compiled_requirements"), dict) else {}
    provider_preferences = compiled.get("provider_preferences") if isinstance(compiled.get("provider_preferences"), dict) else {}
    preferred = provider_preferences.get("stage05_provider_priority")
    if isinstance(preferred, list) and preferred:
        return [str(item).strip() for item in preferred if str(item).strip()]
    strategy = data.get("image_provider_strategy") if isinstance(data.get("image_provider_strategy"), dict) else {}
    priority: list[str] = []
    primary = str(strategy.get("primary") or "").strip()
    if primary:
        priority.append(primary)
    fallback = strategy.get("fallback") if isinstance(strategy.get("fallback"), list) else []
    for item in fallback:
        normalized = str(item).strip()
        if normalized and normalized not in priority:
            priority.append(normalized)
    if priority:
        return priority
    return ["comfyui_txt2img", "manual"]


def select_stage05_runner(
    data: dict[str, Any],
    *,
    config_path: str | None,
) -> dict[str, Any]:
    priority = provider_priority_for_manifest(data)
    try:
        config, resolved_path = load_provider_config(config_path=config_path)
    except ConfigError as exc:
        return {
            "provider": "manual",
            "status": "config_error",
            "reason": str(exc),
            "priority": priority,
            "probe_results": [],
            "config_path": None,
        }

    config_errors = validate_provider_config(config)
    if config_errors:
        return {
            "provider": "manual",
            "status": "invalid_config",
            "reason": "; ".join(config_errors),
            "priority": priority,
            "probe_results": [],
            "config_path": str(resolved_path).replace("\\", "/"),
        }

    probe_results: list[dict[str, Any]] = []
    for provider in priority:
        if provider == "openai_gpt_image2":
            result = check_openai_image_provider(config, probe=True)
            probe_results.append(result)
            if result.get("status") == "ready":
                return {
                    "provider": provider,
                    "status": "ready",
                    "reason": "openai_probe_ready",
                    "priority": priority,
                    "probe_results": probe_results,
                    "config_path": str(resolved_path).replace("\\", "/"),
                }
        elif provider == "comfyui_txt2img":
            result = check_comfyui_server(config)
            probe_results.append(result)
            if result.get("status") == "ready":
                return {
                    "provider": provider,
                    "status": "ready",
                    "reason": "comfyui_probe_ready",
                    "priority": priority,
                    "probe_results": probe_results,
                    "config_path": str(resolved_path).replace("\\", "/"),
                }
        elif provider == "manual":
            return {
                "provider": "manual",
                "status": "manual_only",
                "reason": "manual_in_provider_priority",
                "priority": priority,
                "probe_results": probe_results,
                "config_path": str(resolved_path).replace("\\", "/"),
            }

    return {
        "provider": "manual",
        "status": "no_provider_ready",
        "reason": "all_provider_probes_failed",
        "priority": priority,
        "probe_results": probe_results,
        "config_path": str(resolved_path).replace("\\", "/"),
    }


def build_runner_args(
    manifest_path: Path,
    image_id: str,
    *,
    config_path: str | None,
    allow_beyond_requested_scope: bool,
    fail_fast: bool,
) -> list[str]:
    argv = [str(manifest_path), "--image-id", image_id]
    if config_path:
        argv.extend(["--config", config_path])
    if allow_beyond_requested_scope:
        argv.append("--allow-beyond-requested-scope")
    if fail_fast:
        argv.append("--fail-fast")
    return argv


def write_rerun_reports(manifest_path: Path, report: dict[str, Any]) -> None:
    report_json = manifest_path.parent / "prompt_patch_rerun_report.json"
    report_md = manifest_path.parent / "prompt_patch_rerun_report.md"
    write_json(report_json, report)
    lines = [
        "# Stage 05 Prompt Patch Rerun Report",
        "",
        f"- 项目：`{report.get('project_id')}`",
        f"- 执行时间：`{report.get('generated_at')}`",
        f"- 执行数量：{report.get('selected_count', 0)}",
        f"- 成功数量：{report.get('success_count', 0)}",
        f"- 失败数量：{report.get('failure_count', 0)}",
        f"- 选择执行器：`{report.get('selected_provider') or 'manual'}`",
        "",
    ]
    provider_probe = report.get("provider_probe")
    if isinstance(provider_probe, dict):
        lines.append(f"- 选择原因：{provider_probe.get('reason') or provider_probe.get('status')}")
        lines.append("")
    cleared = report.get("skipped_manually_cleared_image_ids")
    if isinstance(cleared, list) and cleared:
        lines.append(f"- 已跳过人工确认通过图片：{', '.join(f'`{item}`' for item in cleared if str(item).strip())}")
        lines.append("")
    previous_successes = report.get("previously_succeeded_image_ids")
    if isinstance(previous_successes, list) and previous_successes:
        lines.append(f"- 历史已成功重跑图片：{', '.join(f'`{item}`' for item in previous_successes if str(item).strip())}")
        lines.append("")
    skipped = report.get("skipped_previously_succeeded_image_ids")
    if isinstance(skipped, list) and skipped:
        lines.append(f"- 已记录历史重跑成功图片：{', '.join(f'`{item}`' for item in skipped if str(item).strip())}")
        lines.append("")
    for item in report.get("results") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"## {item.get('image_id') or 'unknown'}")
        lines.append("")
        lines.append(f"- 状态：`{item.get('status')}`")
        if item.get("command"):
            lines.append(f"- 调用参数：`{item.get('command')}`")
        if item.get("message"):
            lines.append(f"- 说明：{item.get('message')}")
        if item.get("provider"):
            lines.append(f"- 执行器：`{item.get('provider')}`")
        lines.append("")
    remaining = report.get("remaining_pending_image_ids")
    if isinstance(remaining, list):
        lines.extend([
            "## 剩余待处理",
            "",
            f"- 剩余待人工确认或继续重跑数量：{report.get('remaining_pending_count', 0)}",
        ])
        next_pending = report.get("next_pending_image_ids")
        if isinstance(next_pending, list) and next_pending:
            lines.append(f"- 下一轮建议先处理：{', '.join(f'`{item}`' for item in next_pending if str(item).strip())}")
        if remaining:
            lines.append(f"- 当前剩余队列：{', '.join(f'`{item}`' for item in remaining if str(item).strip())}")
        lines.append("")
    write_text(report_md, "\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--config", default=None, help="Optional path to config/providers.yaml")
    parser.add_argument("--limit", type=int, default=3, help="How many top prompt patches to rerun; defaults to 3")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first rerun failure")
    parser.add_argument("--dry-run", action="store_true", help="Only write the rerun report without invoking the runner")
    parser.add_argument("--include-manually-cleared", action="store_true", help="Also include image_ids whose manual_review_status is already approved, waived, or not_required")
    parser.add_argument("--skip-already-succeeded", action="store_true", help="Skip image_ids that already succeeded in a prior prompt patch rerun report")
    parser.add_argument("--allow-beyond-requested-scope", action="store_true", help="Forward the scope override flag to the Stage 05 runner")
    parser.add_argument("--image-id", default=None, help="Optional single image_id to rerun through the auto-repair entry")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    data = refresh_manifest_prompt_patch_artifacts(manifest_path, data)
    items = top_patch_items(manifest_path, data)
    if args.image_id:
        items = [item for item in items if isinstance(item, dict) and str(item.get("image_id") or "").strip() == args.image_id]
    skipped_manually_cleared = manually_cleared_image_ids(data) if not args.include_manually_cleared else set()
    previous_successes = previously_succeeded_image_ids(manifest_path)
    skipped_previously_succeeded = previous_successes if args.skip_already_succeeded else set()
    items = [
        item for item in items
        if isinstance(item, dict)
        and str(item.get("image_id") or "").strip() not in skipped_manually_cleared
        and str(item.get("image_id") or "").strip() not in skipped_previously_succeeded
    ]
    limit = max(0, int(args.limit))
    selected = items[:limit]
    provider_probe = select_stage05_runner(data, config_path=args.config)
    report = {
        "project_id": data.get("project_id"),
        "manifest_path": str(manifest_path.resolve()).replace("\\", "/"),
        "generated_at": utc_now(),
        "selected_count": len(selected),
        "success_count": 0,
        "failure_count": 0,
        "dry_run": bool(args.dry_run),
        "skipped_manually_cleared_image_ids": sorted(skipped_manually_cleared),
        "previously_succeeded_image_ids": sorted(previous_successes),
        "skipped_previously_succeeded_image_ids": sorted(skipped_previously_succeeded),
        "selected_provider": provider_probe.get("provider"),
        "provider_probe": provider_probe,
        "results": [],
    }
    if not selected:
        report["results"].append({
            "image_id": None,
            "status": "skipped",
            "message": "No top prompt patches were available to rerun.",
        })
        write_rerun_reports(manifest_path, report)
        print(f"PROMPT PATCH RERUN REPORT WRITTEN: {manifest_path.parent / 'prompt_patch_rerun_report.json'}")
        return 0
    if provider_probe.get("provider") == "manual":
        report["failure_count"] = len(selected)
        for item in selected:
            image_id = str(item.get("image_id") or "").strip() or None
            report["results"].append({
                "image_id": image_id,
                "provider": "manual",
                "status": "manual_recovery_required",
                "command": str(item.get("rerun_command") or ""),
                "message": provider_probe.get("reason") or "No Stage 05 provider is ready for auto repair.",
            })
        write_rerun_reports(manifest_path, report)
        print(f"PROMPT PATCH RERUN REPORT WRITTEN: {manifest_path.parent / 'prompt_patch_rerun_report.json'}")
        return 1

    failed = False
    runner_main = run_openai_gpt_image2.main if provider_probe.get("provider") == "openai_gpt_image2" else run_comfyui_txt2img.main
    for item in selected:
        image_id = str(item.get("image_id") or "").strip()
        if not image_id:
            continue
        runner_args = build_runner_args(
            manifest_path,
            image_id,
            config_path=args.config,
            allow_beyond_requested_scope=args.allow_beyond_requested_scope,
            fail_fast=args.fail_fast,
        )
        result_record = {
            "image_id": image_id,
            "status": "planned" if args.dry_run else "pending",
            "command": str(item.get("rerun_command") or " ".join(runner_args)),
            "provider": provider_probe.get("provider"),
            "message": item.get("quick_fix") or item.get("risk_summary") or "",
        }
        if args.dry_run:
            result_record["status"] = "dry_run"
            report["success_count"] += 1
            report["results"].append(result_record)
            continue
        exit_code = runner_main(runner_args)
        if exit_code == 0:
            result_record["status"] = "succeeded"
            report["success_count"] += 1
        else:
            result_record["status"] = "failed"
            result_record["exit_code"] = exit_code
            report["failure_count"] += 1
            failed = True
        report["results"].append(result_record)
        if failed and args.fail_fast:
            break

    refreshed = load_json(manifest_path)
    remaining_pending = remaining_pending_patch_items(refreshed)
    report["remaining_pending_count"] = len(remaining_pending)
    report["remaining_pending_image_ids"] = [
        str(item.get("image_id") or "").strip() for item in remaining_pending if str(item.get("image_id") or "").strip()
    ]
    report["next_pending_image_ids"] = report["remaining_pending_image_ids"][:3]

    write_rerun_reports(manifest_path, report)
    print(f"PROMPT PATCH RERUN REPORT WRITTEN: {manifest_path.parent / 'prompt_patch_rerun_report.json'}")
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
