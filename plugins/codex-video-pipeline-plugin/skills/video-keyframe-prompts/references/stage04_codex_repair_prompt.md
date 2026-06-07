Repair the Stage 04 keyframe and motion prompt JSON.

Rules:
- Fix only the fields required by failed checks and the repair packet.
- Preserve already-correct shot coverage, character consistency anchors, and readiness fields.
- Do not rewrite the approved shot order, story logic, or protagonist identity.
- Return the full corrected JSON object, not a diff.
- Keep every required shot-level semantic field present, including `intent_summary`, `story_anchor_bundle`, `identity_anchor_prompt`, `performance_prompt`, and `dialogue_delivery_prompt`.
- Keep `stage05_handoff` aligned with the repaired reference-image facts.
