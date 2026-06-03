Repair the Stage 04 keyframe and motion prompt JSON.

Rules:
- Fix only the fields required by failed checks and the repair packet.
- Preserve already-correct shot coverage, character consistency anchors, and readiness fields.
- Do not rewrite the approved shot order, story logic, or protagonist identity.
- Return the full corrected JSON object, not a diff.
