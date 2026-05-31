#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

INTERACTION_TRANSFER_MARKERS = (
    "handoff",
    "hand off",
    "pass to",
    "pass the",
    "give to",
    "leave for",
    "share umbrella",
    "递给",
    "交给",
    "留给",
    "送给",
    "让给",
)

TWO_SUBJECT_MARKERS = (
    "stranger",
    "another person",
    "someone else",
    "receiver",
    "giver",
    "two people",
    "two subjects",
    "双人",
    "两人",
    "二人",
    "陌生人",
    "另一个人",
    "对方",
)

UMBRELLA_MARKERS = ("umbrella", "伞")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _combined_text(shot_prompt: dict[str, Any], shot: dict[str, Any], bundle: dict[str, Any]) -> str:
    pieces = [
        bundle.get("action"),
        bundle.get("composition_focus"),
        bundle.get("key_prop"),
        shot_prompt.get("scene_summary"),
        shot_prompt.get("intent_summary"),
        shot_prompt.get("motion_prompt"),
        shot_prompt.get("performance_prompt"),
        shot.get("action"),
        shot.get("composition"),
        shot.get("production_note"),
    ]
    return " ".join(_clean_text(item) for item in pieces if _clean_text(item))


def classify_stage06_generation(
    shot_prompt: dict[str, Any],
    shot: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    combined = _combined_text(shot_prompt, shot, bundle)
    expected_subject_count = 2 if _contains_any(combined, TWO_SUBJECT_MARKERS) else 1
    has_transfer = _contains_any(combined, INTERACTION_TRANSFER_MARKERS)
    has_umbrella = _contains_any(combined, UMBRELLA_MARKERS)
    key_prop = _clean_text(bundle.get("key_prop"))

    if expected_subject_count >= 2 and (has_transfer or has_umbrella):
        constraints = [
            "Lock the camera on a stable frontal axis; no orbit, whip, or handheld sway.",
            "Keep exactly two readable subjects in frame from start to finish.",
            f"Keep exactly one shared {key_prop} in frame." if key_prop else "Keep exactly one shared key prop in frame.",
            "Preserve a clear giver-receiver handoff relationship with readable hand contact.",
            "No foreground passerby occlusion, no crowd takeover, no identity swap.",
            "No extra hands, limb duplication, prop duplication, or melted silhouettes.",
        ]
        return {
            "route_hint": "interaction_handoff",
            "generation_risk_profile": "high_interaction_semantic_delta",
            "camera_lock_required": True,
            "expected_subject_count": 2,
            "expected_key_prop_count": 1 if key_prop else 0,
            "recommended_max_duration_sec": 2.5,
            "prompt_constraints": constraints,
            "runtime_notes": "High-risk two-subject transfer shot. Clamp duration and force camera/prop relationship stability.",
        }

    constraints = [
        "Keep one clear primary subject and preserve face, clothing, and silhouette consistency.",
        f"Keep exactly one {key_prop} with stable count and grip." if key_prop else "Keep prop count stable and hand-object relationships readable.",
        "Avoid static micro-motion, identity drift, extra limbs, and extra background subjects.",
    ]
    return {
        "route_hint": "single_subject_motion",
        "generation_risk_profile": "standard_motion",
        "camera_lock_required": False,
        "expected_subject_count": 1,
        "expected_key_prop_count": 1 if key_prop else 0,
        "recommended_max_duration_sec": None,
        "prompt_constraints": constraints,
        "runtime_notes": "Standard single-subject first-last-frame motion route.",
    }
