Generate the Stage 05 semantic contract JSON for the current project.

Rules:
- This is a Stage 05 task, not a Stage 04 rewrite. You are deciding Stage 05 image-generation semantics so Python can execute mechanically.
- Preserve the locked brief plus all approved Stage 01-04 artifacts.
- Keep the official Stage 05 mainline:
  - `Stage05-A`: bootstrap the canonical primary character reference image.
  - `Stage05-B`: fixed `reference_guided_storyboard` mainline for keyframe generation.
- Python must not decide provider prompt body, fallback strategy, repair direction, or review conclusion for you.
- You must return a complete `stage05_semantic_contract` object that Python can execute without inventing missing semantics.
- Reuse the exact canonical Stage 03 reference-image target paths from upstream facts. Do not invent new reference filenames.
- Every Stage 05 job must be explicit. If a shot only needs `start` and `end`, output exactly those jobs. If a shot truly requires `mid`, output it explicitly and explain it through the job fields instead of making Python infer it.
- Prefer the minimal contract that still keeps Codex in charge:
  - always provide explicit provider prompt body
  - always provide explicit negative prompt
  - always provide explicit review decision
  - always provide explicit repair plan
  - only provide optional workflow override fields when a shot truly needs to diverge from the mainline defaults
  - `review_card` is optional; if omitted, Python may mechanically render it from your review + repair fields
- Do not repeat large mechanical workflow metadata on every job unless it is a real semantic override for that job.
- Do not hardcode scene-specific business rules in Python terms. If a special scene needs special handling, express it only inside this contract as scene semantics for the current project.
- `self_check.matches_stage04_prompts`, `self_check.preserves_reference_guided_mainline`, and `self_check.python_can_execute_mechanically` must all be true.
