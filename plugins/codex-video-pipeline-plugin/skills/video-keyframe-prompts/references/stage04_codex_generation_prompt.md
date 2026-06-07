Generate Stage 04 keyframe and motion prompt JSON for the current project.

Rules:
- Preserve the locked brief plus all approved Stage 01-03 artifacts.
- Cover every approved storyboard shot exactly once.
- Keep character identity, clothing, props, lighting direction, and emotional continuity stable across prompts.
- Write usable image/video generation prompts, not generic high-level notes.
- Avoid prompt bloat that introduces irrelevant cameras, gear, logos, watermarks, or extra people unless the storyboard explicitly requires them.
- Every shot must include `intent_summary`, `story_anchor_bundle`, `identity_anchor_prompt`, `performance_prompt`, and `dialogue_delivery_prompt`.
- You must provide `prompt_language` and `visual_strategy`; Python will not fill them for you.
- You must decide `stage05_handoff.ready_for_stage05`, `summary`, `block_reason`, `next_action`, and `must_open_reference_entry` from the supplied reference-image facts and prompt package.
- If `upstream_character_bible.reference_image_status.target_paths` or `reference_image_plan` provides canonical Stage 03 reference-image target paths, every `shot_prompts[].dependencies.reference_images` entry must reuse those exact paths. Do not invent filenames such as `CHAR_001.png` when the upstream target is `CHAR_001_primary.png`.
