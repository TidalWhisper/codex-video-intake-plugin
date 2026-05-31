#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def _route_requirements(capabilities: dict[str, Any], route_hint: str) -> dict[str, Any]:
    value = capabilities.get("requires_additional_guides_for_route_hints")
    if not isinstance(value, dict):
        return {}
    item = value.get(route_hint)
    return item if isinstance(item, dict) else {}


def evaluate_stage06_route_policy(
    *,
    profile: dict[str, Any],
    workflow_entry: dict[str, Any] | None,
    has_mid_guide: bool,
) -> dict[str, Any]:
    route_hint = str(profile.get("route_hint") or "").strip()
    expected_subject_count = int(profile.get("expected_subject_count") or 1)
    capabilities = workflow_entry.get("capabilities") if isinstance(workflow_entry, dict) and isinstance(workflow_entry.get("capabilities"), dict) else {}
    blocking_reasons: list[str] = []
    warnings: list[str] = []
    required_additional_guides: list[str] = []

    restricted_routes = set(_clean_list(capabilities.get("restricted_route_hints")))
    if route_hint and route_hint in restricted_routes:
        blocking_reasons.append(
            f"workflow capability restriction: route '{route_hint}' is not safe on this Stage 06 workflow"
        )

    subject_range = capabilities.get("supports_subject_count_range")
    if isinstance(subject_range, dict):
        min_subjects = int(subject_range.get("min") or 1)
        max_subjects = int(subject_range.get("max") or min_subjects)
        if expected_subject_count < min_subjects or expected_subject_count > max_subjects:
            blocking_reasons.append(
                f"workflow supports {min_subjects}-{max_subjects} readable subjects, but this shot expects {expected_subject_count}"
            )

    route_requirements = _route_requirements(capabilities, route_hint)
    if route_requirements:
        required_count = int(route_requirements.get("required_count") or 0)
        if required_count >= 3:
            required_additional_guides.append("mid")
            if not has_mid_guide:
                fallback_action = str(route_requirements.get("fallback_action") or "add_mid_keyframe").strip()
                blocking_reasons.append(
                    f"route '{route_hint}' requires at least {required_count} guide keyframes on this workflow; current shot only has start/end. Next action: {fallback_action}"
                )
        elif not has_mid_guide:
            warnings.append(f"route '{route_hint}' has extra guide recommendations but no mid guide is currently present")

    return {
        "blocked": bool(blocking_reasons),
        "blocking_reasons": blocking_reasons,
        "warnings": warnings,
        "required_additional_guides": required_additional_guides,
        "has_mid_guide": has_mid_guide,
    }
