---
name: video-keyframe-images
description: Stage 05 internal/recovery skill for generating keyframe images from Stage 04 keyframe prompts. Use after keyframe_prompts.json is confirmed. Produces image jobs, provider request manifests, generated image evidence, and validation reports under 05_images/.
---

# Stage 05: Keyframe Image Generation

## Role

You are the Stage 05 keyframe image production controller for the Codex video pipeline.

This skill is normally called by `$video-production-pipeline` after the user confirms Stage 04. The user should not need to call this skill manually unless recovering or rerunning Stage 05.

Before changing any Stage 05 ComfyUI style route, use `$video-keyframe-style-selection` and read `config/stage05_style_profiles.example.yaml`.

## Inputs

Read only from the current project folder:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/03_characters/character_bible.json
<project_dir>/04_keyframes/keyframe_prompts.json
```

Do not invent new creative direction. Use the locked brief, storyboard, character bible, and Stage 04 prompts as the source of truth.

## Outputs

Create all Stage 05 files under:

```text
<project_dir>/05_images/
```

Required files:

```text
05_images/image_generation_plan.md
05_images/image_generation_jobs.json
05_images/keyframe_image_manifest.json
05_images/openai_image_requests.json
05_images/comfyui_image_requests.json
05_images/image_review.md
05_images/keyframes/
```

Expected generated image files:

```text
05_images/keyframes/S001_start.png
05_images/keyframes/S001_end.png
05_images/keyframes/S002_start.png
05_images/keyframes/S002_end.png
...
```

## Normal execution

1. Verify Stage 04 is confirmed.
2. Scaffold the image generation manifest:

```bash
python skills/video-keyframe-images/scripts/new_keyframe_image_jobs.py \
  <project_dir>/00_intake/project_brief.locked.json \
  <project_dir>/04_keyframes/keyframe_prompts.json \
  <project_dir>/05_images/keyframe_image_manifest.json
```

3. Write or refresh:

```text
05_images/image_generation_plan.md
05_images/image_generation_jobs.json
05_images/openai_image_requests.json
05_images/comfyui_image_requests.json
```

4. Generate images through the configured provider.

Preferred production provider order:

```text
1. OpenAI image generation, when configured and available
2. Local ComfyUI txt2img/img2img workflow, when configured and available
3. Manual placement of externally generated images into 05_images/keyframes/
```

OpenAI production entrypoint:

```bash
python scripts/providers/run_openai_gpt_image2.py \
  <project_dir>/05_images/keyframe_image_manifest.json
```

This runner refreshes `05_images/openai_image_requests.json`, calls the OpenAI Images API with the configured model, writes files into `05_images/keyframes/`, and updates `keyframe_image_manifest.json`.

ComfyUI txt2img fallback entrypoint:

```bash
python scripts/providers/run_comfyui_txt2img.py \
  <project_dir>/05_images/keyframe_image_manifest.json
```

This runner reads `config/workflow_node_mapping.yaml`, loads the mapped `txt2img_keyframe.workflow_api.json`, injects prompt and image-size fields, submits the ComfyUI workflow, copies the resulting image files into `05_images/keyframes/`, and updates `keyframe_image_manifest.json`.

Stage 05 ComfyUI txt2img now supports a minimal 4-route workflow split:

```text
realistic
anime
guofeng
stylized
```

Current validated local stacks:

- `realistic` → `Qwen 2512`
- `anime` → `Zimage`
- `guofeng` → `Qwen 2512 + qwen_image_gufeng LoRA`
- `stylized` → `Qwen 2512 + illustration-1.0-qwen-image LoRA`

Default behavior is auto-routing from the locked brief style plus Stage 04 prompt hints:

- `realistic` → `txt2img_keyframe_realistic`
- `anime` → `txt2img_keyframe_anime`
- `guofeng` → `txt2img_keyframe_guofeng`
- `stylized` → `txt2img_keyframe_stylized`

The generated `keyframe_image_manifest.json` records both `style_family` and `comfyui_workflow_name` for every job.

Do not assume these four routes are production-ready only because four workflow files exist. The route is only acceptable when the selected model stack is actually appropriate for that style family and a real smoke render exists.

If you must force a single workflow for all jobs, pass it explicitly:

```bash
python scripts/providers/run_comfyui_txt2img.py \
  <project_dir>/05_images/keyframe_image_manifest.json \
  --workflow-name txt2img_keyframe_anime
```

5. After image files exist, sync evidence:

```bash
python skills/video-keyframe-images/scripts/sync_keyframe_image_manifest.py \
  <project_dir>/05_images/keyframe_image_manifest.json
```

6. Validate final manifest:

```bash
python skills/video-keyframe-images/scripts/validate_keyframe_image_manifest.py --mode final \
  <project_dir>/05_images/keyframe_image_manifest.json
```

7. If validation fails, fix missing images or failed jobs. Do not claim Stage 05 is complete until final validation passes.

## Test-only placeholder mode

For local pipeline testing only, this package includes:

```bash
python skills/video-keyframe-images/scripts/generate_placeholder_keyframe_images.py \
  <project_dir>/05_images/keyframe_image_manifest.json
```

This creates simple placeholder PNG files and marks jobs as `succeeded` with provider `placeholder_test_generator`.

Do not present placeholder images as production-quality generated images.

## Confirmation gate

After Stage 05 succeeds, ask:

```text
Stage 05 关键帧图片包已生成。

请确认：
A. 关键帧图片可以，后续进入 Stage 06 视频片段生成
B. 替换某个镜头的 start keyframe
C. 替换某个镜头的 end keyframe
D. 调整图片风格一致性
E. 改用 ComfyUI / OpenAI / 手动图片重新生成
F. 重新生成 Stage 05 图片包
```

If user chooses A:

1. Set `keyframe_image_manifest.json.status` to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
  "keyframe_images_confirmed": true,
  "allowed_next_stage": "STAGE_06_VIDEO_CLIPS"
}
```

3. Immediately continue to Stage 06 in the same conversation. Do not ask the user to call another skill.

## Hard rules

- Do not write Stage 05 outputs outside the project folder.
- Do not skip image evidence.
- Do not say images were generated unless the corresponding files exist.
- In v0.7.0, Stage 05 confirmation should continue to Stage 06 automatically in the normal pipeline.
- Do not modify Stage 00–04 source files unless the user explicitly asks for regeneration.
