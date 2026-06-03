# Zimage Style Switch Unified Spec

## Purpose

This spec unifies the verified style-switch rules for the three local Zimage UI workflows:

- `F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json`
- `F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-comics_SAFETENSORS.json`
- `F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json`

It exists to prevent a repeated failure mode:

- the workflow is treated like a plain prompt patch target
- internal style template nodes are mistaken for user prompt inputs
- the real style switch is not exercised
- the workflow runs, but the claimed understanding is false

## Shared verified structure

All three local Zimage workflows were locally verified to share the same control pattern:

1. `#57 PROMPT` is the only main user-written prompt field.
2. `#88 STYLE SELECTOR` is the real user-facing style switch in the UI.
3. `#88` is a frontend muter-style control, not a text prompt field.
4. `#104 Style Collector (rgthree)` is the authoritative source of the style list.
5. `#87 Any Switch (rgthree)` forwards the currently enabled style string.
6. `#31 STYLE INTEGRATOR` applies the selected style template to the prompt from `#57`.

## Hard rules

- Do not describe internal style template nodes as a second prompt input area.
- Do not treat `#90` or any other style text node as the style switch itself.
- Do not claim a workflow is understood if only prompt text changed and the real style branch was never toggled.
- Do not present a reduced bridge or custom reconstruction as the original community workflow unless stated explicitly.
- Do not approve automation as correct until a real multi-style render set proves the switch works semantically.

## Canonical automation procedure

For any of the three Zimage UI workflows:

1. Read `#104 Style Collector (rgthree)` from the workflow JSON.
2. Extract every non-empty style input label from the collector.
3. Resolve each collector input back through any `Reroute` nodes until the terminal style node is found.
4. Treat that terminal style node as the actual branch node to enable or disable.
5. Keep `#57 PROMPT` as the only main prompt input.
6. For a single-style run, set exactly one terminal style node to `mode = 0`.
7. Set the remaining terminal style nodes in that workflow to `mode = 2`.
8. Convert the UI workflow through the real ComfyUI frontend path before submission.
9. Confirm the converted prompt reflects the active style branch through `#87`.

## Validation standard

To prove that a Zimage style switch is really understood:

1. Use one fixed prompt in `#57`.
2. Use one fixed seed.
3. Use one fixed output size.
4. Render one image per style with only that style branch enabled.
5. Produce a contact sheet for side-by-side review.

Passing evidence is not "the workflow produced files".
Passing evidence is:

- the active style changes the output treatment or semantics
- the output set is clearly distinguishable across styles
- subject integrity remains sane unless the style itself strongly biases the scene

## Current local evidence baseline

Local full-style runs were verified on `2026-06-02`:

- Amazing Z-Photo:
  - `E:/Codex-Plugin/codex-video-intake-plugin/.tmp-style-compare-20260602-photo-allstyles/`
- Amazing Z-Comics:
  - `E:/Codex-Plugin/codex-video-intake-plugin/.tmp-style-compare-20260602-comics-allstyles/`
- Amazing Z-Image-A:
  - `E:/Codex-Plugin/codex-video-intake-plugin/.tmp-style-compare-20260602-image-a-allstyles/`

Each directory contains:

- `manifest.json`
- `contact_sheet_allstyles.png`

These are the current local baseline sets for regression checking.

## Workflow-specific supplements

After reading this unified spec, load the matching workflow-specific skill:

- `$video-keyframe-amazing-z-photo-style-switch`
- `$video-keyframe-amazing-z-comics-style-switch`
- `$video-keyframe-amazing-z-image-a-style-switch`

Use the workflow-specific skill for the exact verified style-node list and workflow-local evidence path.
