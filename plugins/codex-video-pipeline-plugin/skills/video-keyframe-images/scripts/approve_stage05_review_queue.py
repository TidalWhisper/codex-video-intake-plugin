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

from pipeline_blueprints import next_stage_after  # noqa: E402
from pipeline_core.project_state import update_project_manifest_for_stage  # noqa: E402
from pipeline_core.stage05_quality_gates import MANUAL_REVIEW_CLEAR_STATES, build_quality_gate  # noqa: E402
from stage05_image_utils import resolve_path, update_manifest_state  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {exc}")


def pending_review_image_ids(data: dict[str, Any]) -> list[str]:
    quality_review = data.get("quality_review") if isinstance(data.get("quality_review"), dict) else {}
    queue = quality_review.get("review_queue") if isinstance(quality_review.get("review_queue"), list) else []
    ids: list[str] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        image_id = str(item.get("image_id") or "").strip()
        if image_id:
            ids.append(image_id)
    if ids:
        return ids

    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    fallback: list[str] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        gate = build_quality_gate(job)
        image_id = str(job.get("image_id") or "").strip()
        status = str(gate.get("manual_review_status") or "").strip().lower()
        if image_id and gate.get("requires_manual_review") and status not in MANUAL_REVIEW_CLEAR_STATES:
            fallback.append(image_id)
    return fallback


def find_job(data: dict[str, Any], image_id: str) -> dict[str, Any] | None:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), list) else []
    for job in jobs:
        if isinstance(job, dict) and str(job.get("image_id") or "").strip() == image_id:
            return job
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_json", help="Path to 05_images/keyframe_image_manifest.json")
    parser.add_argument("--image-id", action="append", default=[], help="Approve one specific image_id. May be passed multiple times.")
    parser.add_argument("--top", type=int, default=None, help="Approve the first N pending review items in current priority order. Defaults to 1 when no selector is given.")
    parser.add_argument("--all-pending", action="store_true", help="Approve all currently pending manual-review items.")
    parser.add_argument("--status", choices=["approved", "waived"], default="approved", help="Review decision to apply.")
    parser.add_argument("--note", default=None, help="Optional reviewer note recorded on each selected image.")
    parser.add_argument("--content-aligned", action="store_true", help="Confirm that the image content matches the shot's text description before approving.")
    parser.add_argument("--content-alignment-note", default=None, help="Required for approved status. Explain why the image content matches the text description.")
    parser.add_argument("--allow-missing-files", action="store_true", help="Allow approval even if the image file is missing on disk.")
    parser.add_argument("--dry-run", action="store_true", help="Preview which image_ids would be updated without writing the manifest.")
    return parser.parse_args(argv)


def selected_image_ids(args: argparse.Namespace, data: dict[str, Any]) -> list[str]:
    explicit_ids = [str(item).strip() for item in args.image_id if str(item).strip()]
    if explicit_ids:
        return explicit_ids
    pending_ids = pending_review_image_ids(data)
    if args.all_pending:
        return pending_ids
    limit = 1 if args.top is None else max(0, int(args.top))
    return pending_ids[:limit]


def apply_review_decision(
    job: dict[str, Any],
    *,
    manifest_path: Path,
    status: str,
    note: str | None,
    content_aligned: bool,
    content_alignment_note: str | None,
    allow_missing_files: bool,
) -> tuple[bool, str]:
    gate = build_quality_gate(job)
    image_id = str(job.get("image_id") or "").strip() or "unknown"
    if not gate.get("requires_manual_review"):
        return False, f"{image_id}: no manual review required"

    output_path = job.get("output_path") or job.get("evidence", {}).get("file_path")
    resolved = resolve_path(manifest_path, output_path)
    exists = resolved.exists() and resolved.is_file() and resolved.stat().st_size > 0
    if not exists and not allow_missing_files:
        return False, f"{image_id}: image file missing on disk"
    if status == "approved":
        if not content_aligned:
            return False, f"{image_id}: approval requires --content-aligned confirmation"
        if not str(content_alignment_note or "").strip():
            return False, f"{image_id}: approval requires --content-alignment-note"

    gate["manual_review_status"] = status
    gate["review_decision_source"] = "approve_stage05_review_queue.py"
    gate["review_note"] = (note or "").strip() or None
    timestamp = utc_now()
    if status == "approved":
        gate["approved_at"] = timestamp
        gate["content_text_alignment_confirmed"] = True
        gate["content_text_alignment_note"] = str(content_alignment_note or "").strip()
        gate["content_text_alignment_checked_at"] = timestamp
    else:
        gate["waived_at"] = timestamp
        gate["content_text_alignment_confirmed"] = False
        gate["content_text_alignment_note"] = None
        gate["content_text_alignment_checked_at"] = None
    job["quality_gate"] = gate
    return True, f"{image_id}: {status}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest_path = Path(args.manifest_json)
    data = load_json(manifest_path)
    targets = selected_image_ids(args, data)

    if not targets:
        print("NO_PENDING_STAGE05_REVIEW_ITEMS")
        return 0

    updated_ids: list[str] = []
    skipped_messages: list[str] = []
    missing_ids: list[str] = []
    seen: set[str] = set()
    for image_id in targets:
        if image_id in seen:
            continue
        seen.add(image_id)
        job = find_job(data, image_id)
        if not isinstance(job, dict):
            missing_ids.append(image_id)
            continue
        changed, message = apply_review_decision(
            job,
            manifest_path=manifest_path,
            status=args.status,
            note=args.note,
            content_aligned=bool(args.content_aligned),
            content_alignment_note=args.content_alignment_note,
            allow_missing_files=bool(args.allow_missing_files),
        )
        if changed:
            updated_ids.append(image_id)
        else:
            skipped_messages.append(message)

    if args.dry_run:
        print("STAGE05_REVIEW_DRY_RUN")
        print(f"TARGET_IMAGE_IDS: {', '.join(targets)}")
        if updated_ids:
            print(f"WOULD_MARK_{args.status.upper()}: {', '.join(updated_ids)}")
        for message in skipped_messages:
            print(f"SKIP: {message}")
        for image_id in missing_ids:
            print(f"MISSING_JOB: {image_id}")
        return 0 if updated_ids or not (skipped_messages or missing_ids) else 1

    if missing_ids:
        for image_id in missing_ids:
            print(f"MISSING_JOB: {image_id}")
        return 1

    update_manifest_state(data, manifest_path)
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {"legacy_mode": True}
    if data.get("self_check", {}).get("ready_for_video_clip_generation") is True:
        data["allowed_next_stage"] = next_stage_after("STAGE_05_KEYFRAME_IMAGES", routing, "STAGE_06_VIDEO_CLIPS")
        update_project_manifest_for_stage(
            manifest_path,
            current_stage="STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
            allowed_next_stage=data["allowed_next_stage"],
            flags={"keyframe_images_confirmed": True},
            status="active",
        )
    else:
        data["allowed_next_stage"] = None
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STAGE05_REVIEW_UPDATED: {manifest_path}")
    if updated_ids:
        print(f"MARKED_{args.status.upper()}: {', '.join(updated_ids)}")
    for message in skipped_messages:
        print(f"SKIP: {message}")
    refreshed = load_json(manifest_path)
    quality_review = refreshed.get("quality_review") if isinstance(refreshed.get("quality_review"), dict) else {}
    pending_count = int(quality_review.get("pending_count") or 0)
    next_ids = quality_review.get("next_review_image_ids") if isinstance(quality_review.get("next_review_image_ids"), list) else []
    print(f"REMAINING_PENDING_MANUAL_REVIEW: {pending_count}")
    if next_ids:
        print(f"NEXT_PENDING_IMAGE_IDS: {', '.join(str(item) for item in next_ids[:3] if str(item).strip())}")
    if refreshed.get("self_check", {}).get("ready_for_video_clip_generation") is True:
        print("READY_FOR_STAGE06: yes")
    return 0 if updated_ids or not skipped_messages else 1


if __name__ == "__main__":
    raise SystemExit(main())
