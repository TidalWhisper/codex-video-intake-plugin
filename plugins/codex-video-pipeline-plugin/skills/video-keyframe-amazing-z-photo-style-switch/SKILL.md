---
name: video-keyframe-amazing-z-photo-style-switch
description: Use when working with the local Amazing Z-Photo ComfyUI workflow, especially when switching internal styles, validating style semantics, or integrating Stage 05 automation without breaking the original community workflow logic.
---

# Amazing Z-Photo Style Switch

Before using this workflow-specific skill, read:

```text
skills/video-keyframe-style-selection/references/zimage-style-switch-unified-spec.md
```

Use this skill whenever the task touches:

- `F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json`
- `#88 STYLE SELECTOR`
- internal style A/B tests for Amazing Z-Photo
- Stage 05 automation that claims to support the original Amazing Z-Photo UI workflow

## Verified control surfaces

These points were verified locally in real runs and should be treated as hard facts for this workflow:

1. `#57 PROMPT` is the only user-written main prompt field.
2. `#88 STYLE SELECTOR` is the real style switch the user interacts with in the UI.
3. `#88` is a frontend muter-style control, not a second prompt field.
4. `#104 Style Collector (rgthree)` is the canonical source of the internal style list.
5. `#87 Any Switch (rgthree)` forwards the currently enabled style string into `#31 STYLE INTEGRATOR`.
6. `#31 STYLE INTEGRATOR` applies the selected style template to the text from `#57`.

## Hard rules

- Do not describe internal style template nodes as user prompt input fields.
- Do not treat `#90` or any other style text node as a substitute for the UI style switch.
- Do not claim you understood the workflow if you only changed prompt text and never switched the real style branch.
- Do not rebuild a reduced bridge and present it as "the original Amazing Z-Photo workflow" unless you say explicitly that it is a reduced bridge.
- Do not approve an automation path as correct until a real all-style or multi-style render set proves the switch works semantically.

## Canonical automation logic

When automating this workflow, follow this order:

1. Read `#104 Style Collector (rgthree)` and extract every non-empty style input label from the workflow itself.
2. Resolve each collector input back through any `Reroute` nodes until you reach the terminal style node.
3. Treat the terminal style node as the real branch node to enable/disable.
4. Keep `#57 PROMPT` as the only main prompt input.
5. For each style run, set exactly one terminal style node to `mode = 0` and set the other Amazing Z-Photo style nodes to `mode = 2`.
6. Convert the UI workflow through the real ComfyUI frontend path before submission, so `#87` reflects the active branch.

## Verified Amazing Z-Photo style nodes

The current local workflow was verified to expose these terminal style nodes:

- `none` -> `#90`
- `STYLE: Phone Photo` -> `#125`
- `STYLE: Casual Photo` -> `#101`
- `STYLE: Vintage Photo` -> `#117`
- `STYLE: Portra Film Photo` -> `#63`
- `STYLE: Flash 90s Photo` -> `#47`
- `STYLE: Production Photo` -> `#38`
- `STYLE: Classic Film Photo` -> `#92`
- `STYLE: Noir Photo` -> `#37`
- `STYLE: Lomography` -> `#41`
- `STYLE: Drone Photo` -> `#122`
- `STYLE: Minimalist Photo` -> `#43`
- `STYLE: High-Key Fashion Photo` -> `#93`
- `STYLE: Light and Airy Photo` -> `#130`
- `STYLE: Teal and Orange Photo` -> `#45`
- `STYLE: Orthochromatic Spirit Photo` -> `#124`
- `STYLE: Street Documentary Photo` -> `#459`
- `STYLE: Tilt Shift / Toy Photo` -> `#460`
- `STYLE: Pop Photo` -> `#461`

If the upstream workflow changes, re-extract from `#104` instead of trusting this list blindly.

## Validation procedure

When proving that the style switch is understood:

1. Use one fixed prompt in `#57`.
2. Use one fixed seed.
3. Use one fixed output size.
4. Render one image per style with only that style branch enabled.
5. Produce a contact sheet so style differences can be judged side by side.

Passing evidence is not "the workflow ran". Passing evidence is:

- the active style actually changes the rendered image semantics or treatment
- the image still keeps one sane subject unless the style itself strongly biases the scene
- the output set is clearly distinguishable across styles

## Latest local evidence

Local validation on `2026-06-02` produced a full 19-style render set for this exact workflow under:

- `E:/Codex-Plugin/codex-video-intake-plugin/.tmp-style-compare-20260602-photo-allstyles/`

Key evidence files:

- `manifest.json`
- `contact_sheet_allstyles.png`

Use that render set as the current local baseline when checking whether future automation regressed.
