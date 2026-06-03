---
name: video-keyframe-style-selection
description: Select and validate Stage 05 ComfyUI models and workflows for keyframe image style families such as realistic, anime, guofeng, and stylized. Use when adding or changing Stage 05 style routes, auditing whether a local checkpoint or LoRA is actually suitable for a style family, deciding if a workflow may ship, or documenting reusable model-selection rules for later runs.
---

# Stage 05 Style Selection

Use this skill before changing any Stage 05 ComfyUI style route.

## Read first

Load:

```text
config/stage05_style_profiles.example.yaml
references/stage05-style-selection-spec.md
references/zimage-style-switch-unified-spec.md
```

If the target workflow is the local original Amazing Z-Photo UI graph, load this skill first and follow it as a hard supplement:

```text
$video-keyframe-amazing-z-photo-style-switch
```

If the target workflow is the local original Amazing Z-Comics UI graph, load this skill first and follow it as a hard supplement:

```text
$video-keyframe-amazing-z-comics-style-switch
```

If the target workflow is the local original Amazing Z-Image-A UI graph, load this skill first and follow it as a hard supplement:

```text
$video-keyframe-amazing-z-image-a-style-switch
```

If working on an existing route, also read:

```text
workflows/comfyui/txt2img_keyframe_<style>.workflow_api.json
config/workflow_node_mapping.yaml
```

## Core rule

Do not approve a Stage 05 style route only because a prompt can coerce a general model into something vaguely similar.

A style route is acceptable only when all of the following are true:

1. The selected local model family is appropriate for that style family.
2. The workflow actually loads that model or style LoRA, not just the same base graph with different text.
3. At least one real local smoke render exists for that route.
4. The result is visually distinguishable from other routes.
5. The route status is recorded in the style profile spec.

## Required workflow

1. Audit the current local model inventory.
2. Identify the exact checkpoint, diffusion model, CLIP, VAE, and LoRA used by the route.
3. Classify the model as:
   - `native-fit`
   - `adapted-fit`
   - `prompt-only`
   - `unsupported`
4. Reject `prompt-only` as a production answer for style-specialized routes like `guofeng` or `stylized` unless a smoke-test proves the route is clearly acceptable.
5. Render a real local sample.
6. Record the decision in the style profile spec.

## Output expectation

For every Stage 05 style family, leave behind:

- exact loaded model stack
- suitability decision
- smoke-test evidence path
- known risks
- next action

## Hard rules

- Do not claim a style route is solved if it still uses the same base model with only prompt text changes and the output is not clearly differentiated.
- Do not treat timeout handling or prompt wording as a substitute for model selection.
- Do not mark `guofeng` or `stylized` production-ready without style-specific evidence.
- If no suitable local model exists, say so explicitly and keep the route in a blocked or provisional state.
- For `amazing-z-photo_SAFETENSORS.json`, do not fake style switching by copying one style template into another node; the real control surface is `#88 STYLE SELECTOR`, with `#57` remaining the only main prompt field.
- For `amazing-z-comics_SAFETENSORS.json`, do not fake style switching by copying one style template into another node; the real control surface is `#88 STYLE SELECTOR`, with `#57` remaining the only main prompt field.
- For `amazing-z-image-a_SAFETENSORS.json`, do not fake style switching by copying one style template into another node; the real control surface is `#88 STYLE SELECTOR`, with `#57` remaining the only main prompt field.
