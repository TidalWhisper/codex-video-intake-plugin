---
name: video-keyframe-images
description: Stage 05 internal/recovery skill for generating keyframe images from Stage 04 keyframe prompts. Use after keyframe_prompts.json is confirmed. Produces image jobs, provider request manifests, generated image evidence, and validation reports under 05_images/.
---

# Stage 05: Keyframe Image Generation

## Role

You are the Stage 05 keyframe image production controller for the Codex video pipeline.

This skill is normally called by `$video-production-pipeline` after the user confirms Stage 04. The user should not need to call this skill manually unless recovering or rerunning Stage 05.

Before changing any Stage 05 ComfyUI style route, use `$video-keyframe-style-selection` and read `config/stage05_style_profiles.example.yaml`.
If the route touches one of the original local Zimage UI workflows, also read `skills/video-keyframe-style-selection/references/zimage-style-switch-unified-spec.md` before loading the workflow-specific supplement.
If the route touches the original local `amazing-z-photo_SAFETENSORS.json` workflow, also load `$video-keyframe-amazing-z-photo-style-switch` before changing mappings, prompts, or style-switch logic.
If the route touches the original local `amazing-z-comics_SAFETENSORS.json` workflow, also load `$video-keyframe-amazing-z-comics-style-switch` before changing mappings, prompts, or style-switch logic.
If the route touches the original local `amazing-z-image-a_SAFETENSORS.json` workflow, also load `$video-keyframe-amazing-z-image-a-style-switch` before changing mappings, prompts, or style-switch logic.
If the task is explicitly about `Qwen-Image-Edit` local reference-guided Stage 05 continuity, or touches `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`, first load `$video-keyframe-qwen-nextscene-reference-guided`.

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
05_images/comfyui_image_requests.json
```

4. 根据主角色参考图状态选择主线：

- 如果 `03_characters/reference_images/CHAR_001_primary.png` 缺失，先执行 `Stage05-A`：

```bash
python skills/video-keyframe-images/scripts/run_stage05_reference_bootstrap.py \
  <project_dir>/05_images/keyframe_image_manifest.json
```

- `Stage05-A` 会根据 `Stage03` 人物设定和当前风格路由，选择三条锁定 Zimage workflow 之一生成主角色参考图，并回填 `Stage03`。
- 回填完成后，它会自动刷新 `03_characters/character_bible.json`、`04_keyframes/keyframe_prompts.json`、以及 `05_images/keyframe_image_manifest.json`。

5. 生成 `Stage05-B` 一致性分镜图。

Preferred production provider order:

```text
1. Local ComfyUI txt2img workflow on the locked Stage05 mainline
2. Manual placement of externally generated images into `05_images/keyframes/`
```

ComfyUI txt2img mainline entrypoint:

```bash
python scripts/providers/run_comfyui_txt2img.py \
  <project_dir>/05_images/keyframe_image_manifest.json
```

This runner reads `config/workflow_node_mapping.yaml`, loads the mapped `txt2img_keyframe.workflow_api.json`, injects prompt and image-size fields, submits the ComfyUI workflow, copies the resulting image files into `05_images/keyframes/`, and updates `keyframe_image_manifest.json`.

Stage05 当前分成两段：

```text
Stage05-A: Zimage bootstrap
Stage05-B: Qwen NextScene reference-guided storyboard
```

Stage 05 ComfyUI txt2img still uses a minimal 4-route split for `Stage05-A` workflow selection:

```text
realistic
anime
guofeng
stylized
```

Current execution semantics:

- Provider priority is fixed: `ComfyUI txt2img -> manual`
- `stage05_route_key` is the primary routing field recorded in `keyframe_image_manifest.json`
- `comfyui_workflow_mapping_key` is the primary execution key used to resolve `config/workflow_node_mapping.yaml`
- `style_family` remains a compatibility field for existing Stage 05 validation and runner logic
- `style_family` only decides the internal ComfyUI route family, not provider order

Current default route families now map onto the three locked local Zimage UI workflows, but only for `Stage05-A`:

- `realistic_cinematic` → `stage05_realistic_cinematic_amazing_z_photo_original` → `amazing_z_photo_safetensors`
- `shortdrama_realistic` → `stage05_realistic_cinematic_amazing_z_photo_original` → `amazing_z_photo_safetensors`
- `anime_jp` → `stage05_anime_jp` → `amazing_z_image_a_safetensors`
- `anime_cn_newguofeng` → `stage05_anime_jp` → `amazing_z_image_a_safetensors`
- `guofeng_ink` → `stage05_anime_jp` → `amazing_z_image_a_safetensors`
- `western_cartoon` → `stage05_western_cartoon` → `amazing_z_comics_safetensors`
- `stylized_concept` → `stage05_western_cartoon` → `amazing_z_comics_safetensors`
- `game_cg` → `stage05_western_cartoon` → `amazing_z_comics_safetensors`

Stage 05 default mainline rules:

- The three locked local Zimage UI workflows are now only the `Stage05-A` primary-reference bootstrap targets.
- `Stage05-B` mainline is fixed to `stage05_realistic_cinematic_qwen_edit_nextscene_local`.
- Route variation for `Stage05-A` must happen through `style_selector` and route preset metadata.
- `Stage05-B` must follow [references/stage05-qwen-reference-guided-workflow-rules.md](./references/stage05-qwen-reference-guided-workflow-rules.md) and the Qwen NextScene prompt convergence rules.
- Do not mix prompt-only Zimage shot generation and reference-guided Qwen storyboard generation inside the same Stage05-B shot bundle.

The generated `keyframe_image_manifest.json` now records `stage05_mode`, `primary_reference_image_path`, `reference_bootstrap`, `stage05_route_key`, `style_family`, `comfyui_workflow_mapping_key`, `comfyui_workflow_name`, `comfyui_model_id`, and `route_resolution`.

Do not treat deleted bridge or fallback routes as candidates to keep "just in case". Route changes should go through the real Stage 05 registry and the three active Zimage workflows only.

If you must force a single workflow for all jobs, pass it explicitly:

```bash
python scripts/providers/run_comfyui_txt2img.py \
  <project_dir>/05_images/keyframe_image_manifest.json \
  --workflow-name stage05_anime_jp
```

6. After image files exist, sync evidence:

```bash
python skills/video-keyframe-images/scripts/sync_keyframe_image_manifest.py \
  <project_dir>/05_images/keyframe_image_manifest.json
```

If Stage 05 generated successfully but risky frames still need human sign-off, approve the current review queue directly instead of hand-editing the manifest:

```bash
python skills/video-keyframe-images/scripts/approve_stage05_review_queue.py \
  <project_dir>/05_images/keyframe_image_manifest.json \
  --top 3 \
  --content-aligned --content-alignment-note "confirmed content matches shot description"
```

You can also approve a specific frame:

```bash
python skills/video-keyframe-images/scripts/approve_stage05_review_queue.py \
  <project_dir>/05_images/keyframe_image_manifest.json \
  --image-id IMG_S001_START \
  --content-aligned --content-alignment-note "confirmed content matches shot description"
```

7. Validate final manifest:

```bash
python skills/video-keyframe-images/scripts/validate_keyframe_image_manifest.py --mode final \
  <project_dir>/05_images/keyframe_image_manifest.json
```

8. If validation fails, fix missing images or failed jobs. Do not claim Stage 05 is complete until final validation passes.

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
- For the original Amazing Z-Photo workflow, treat `#57` as the only main prompt field and `#88 STYLE SELECTOR` as the real style switch. Do not replace real style switching with manual text copying between internal style nodes.
- For the original Amazing Z-Comics workflow, treat `#57` as the only main prompt field and `#88 STYLE SELECTOR` as the real style switch. Do not replace real style switching with manual text copying between internal style nodes.
- For the original Amazing Z-Image-A workflow, treat `#57` as the only main prompt field and `#88 STYLE SELECTOR` as the real style switch. Do not replace real style switching with manual text copying between internal style nodes.
- Do not say images were generated unless the corresponding files exist.
- In v0.7.0, Stage 05 confirmation should continue to Stage 06 automatically in the normal pipeline.
- Do not modify Stage 00–04 source files unless the user explicitly asks for regeneration.
