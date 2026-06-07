Generate Stage 03 character bible JSON for the current project.

Rules:
- Preserve the locked brief, approved Stage 01 script, and approved Stage 02 storyboard.
- Produce creator-usable character anchors, not abstract writing notes.
- Each character must be visually stable across shots and ready for Stage 04 / Stage 05 continuity work.
- Avoid generic filler such as "普通女孩/普通男孩" without concrete identity anchors.
- Keep the protagonist count, role logic, and visual continuity constraints aligned with the upstream materials.
- Every character must include a full `performance_profile` with `baseline_expression`, `movement_style`, `gesture_rules`, `dialogue_delivery`, and `continuity_anchor`.
- You must decide `reference_image_required` from the supplied story/continuity facts. Do not assume a Python default.
- You must fill `reference_image_handoff.ready_for_stage05`, `summary`, `next_action`, and `capture_focus` so downstream creator guidance stays Codex-led.
