# Stage 05 Style Selection Spec

## Purpose

This spec defines how Stage 05 should choose local ComfyUI models and workflows for keyframe image style families.

It exists to prevent a repeated failure mode:

- one general model is copied into multiple workflow files
- only the prompt text changes
- the route names look different
- the outputs are not reliably different enough for production

## Hard requirements

### 1. Model-first, not prompt-first

Choose the model family first, then design the workflow around it.

Prompt tuning is allowed only after the model choice is defensible.

### 2. Route identity must be real

A route counts as distinct only if at least one of these changes:

- checkpoint or diffusion model
- LoRA stack
- style model
- text encoder path when style support differs materially
- workflow structure that materially changes the image prior

Changing only prompt text is not enough for style-specialized routes unless smoke renders clearly prove the route is acceptable.

### 3. Every route needs smoke evidence

For each style family, keep at least one real local sample render and request log:

- `05_images/keyframes/*.png`
- `05_images/comfyui_image_requests.json`

### 4. Status language

Use one of these statuses in the style profile registry:

- `approved`
- `provisional`
- `blocked`
- `deprecated`

## Suitability classes

### `native-fit`

The underlying model or checkpoint is already known to handle the target style family well.

Example:

- anime-tuned illustration model for `anime`
- ink-wash or Chinese-painting-tuned model for `guofeng`

### `adapted-fit`

The base model is general-purpose, but a specific LoRA or style stack makes the route clearly usable.

This requires smoke evidence.

### `prompt-only`

The route still uses the same general base model and mostly depends on prompt wording to imitate the style.

This is weak evidence and should not be approved for difficult routes like `guofeng` and `stylized` unless the output quality is demonstrably strong.

### `unsupported`

No defensible local model stack exists for the style family.

## Decision checklist

For each style family, answer:

1. What exact model does the workflow load
2. What exact LoRA or style module does it load
3. Why is that model appropriate for this style family
4. What local sample proves it
5. Is the result visually distinct from `realistic`
6. What known defects remain

If questions 1 through 4 cannot be answered clearly, the route is not ready.

## Current local audit

Audit date: `2026-05-29`

### Local installed image-model evidence

Observed local assets include:

- diffusion model: `Qwen/qwen_image_2512_fp8_e4m3fn.safetensors`
- edit diffusion model: `Qwen/qwen_image_edit_2511_bf16.safetensors`
- diffusion model: `Zimage/z_image_turbo_bf16.safetensors`
- text encoder: `Zimage/qwen_3_4b.safetensors`
- vae: `Zimage/ae.safetensors`
- checkpoint: `Qwen-Rapid-AIO-NSFW-v18.safetensors`
- realistic-leaning LoRAs:
  - `Kook_Qwen_V3极致真实.safetensors`
  - `Kook_千问写实_Kook_Qwen_V1稳定版.safetensors`
  - `Kook_千问写实_Kook_Qwen_V2美人版.safetensors`
- style LoRAs:
  - `qwen-image/qwen_image_gufeng.safetensors`
  - `qwen-image/illustration-1.0-qwen-image.safetensors`

No clearly named local `Anime Base` checkpoint was found during this audit.

Observed `Dasiwa` assets on this machine were not confirmed as Stage 05 txt2img keyframe models.

### Current conclusion

- `realistic`
  - model fit: `native-fit` or `adapted-fit`
  - comment: local Qwen 2512 stack is reasonable here
- `anime`
  - model fit: `adapted-fit`
  - comment: local Zimage stack is a defensible dedicated anime/illustration route, but current Stage 05 anime composition control should remain provisional
- `guofeng`
  - model fit: `adapted-fit`
  - comment: Qwen base plus local guofeng LoRA is now the approved Stage 05 guofeng route on this machine
- `stylized`
  - model fit: `adapted-fit`
  - comment: Qwen base plus local illustration LoRA is now the approved Stage 05 stylized route on this machine

## Official-model interpretation rule

If a model card describes a model as a general image generation foundation model with support for a wide range of styles, interpret that as broad capability, not as proof of deep specialization for a target route like `guofeng`.

Until a model card, fine-tune description, or local validation says otherwise, treat the model as general-purpose.

## Recommended future workflow policy

### `realistic`

Allow:

- strong general open image model
- realism-oriented LoRA

### `anime`

Prefer:

- anime-native checkpoint
- anime illustration LoRA on a compatible base

### `guofeng`

Prefer:

- Chinese painting or ink-wash tuned checkpoint
- guofeng illustration LoRA
- workflow that suppresses modern photographic priors

### `stylized`

Prefer:

- concept-art or painterly illustration checkpoint
- stylized illustration LoRA
- workflow that protects subject readability while enforcing painterly treatment

## What to record after every route change

Update the style profile registry with:

- selected workflow file
- selected model stack
- suitability class
- status
- smoke sample path
- review note
