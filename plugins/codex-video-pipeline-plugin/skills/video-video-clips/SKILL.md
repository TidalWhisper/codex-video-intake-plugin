---
name: video-video-clips
description: Stage 06 internal/recovery skill for generating short video clips from Stage 05 keyframe images and Stage 04 motion prompts. Use after keyframe images are confirmed. Produces clip jobs, ComfyUI LTX I2V request manifests, clip evidence, and validation reports under 06_video_clips/.
---

# Stage 06: Video Clip Generation

## Role

You are the Stage 06 video clip production controller for the Codex video pipeline.

This skill is normally called by `$video-production-pipeline` after the user confirms Stage 05. The user should not need to call this skill manually unless recovering or rerunning Stage 06.

## Inputs

Read only from the current project folder:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/04_keyframes/keyframe_prompts.json
<project_dir>/05_images/keyframe_image_manifest.json
```

Do not invent new creative direction. Use the locked brief, storyboard, Stage 04 motion prompts, and Stage 05 keyframe evidence as the source of truth.

## Outputs

Create all Stage 06 files under:

```text
<project_dir>/06_video_clips/
```

Required files:

```text
06_video_clips/video_clip_generation_plan.md
06_video_clips/video_clip_jobs.json
06_video_clips/video_clip_manifest.json
06_video_clips/comfyui_ltx_i2v_requests.json
06_video_clips/manual_video_requests.json
06_video_clips/clip_review.md
06_video_clips/clips/
```

Expected generated clip files:

```text
06_video_clips/clips/S001.mp4
06_video_clips/clips/S002.mp4
06_video_clips/clips/S003.mp4
...
```

## Normal execution

1. Verify Stage 05 is confirmed and all keyframe images exist.
2. Scaffold video clip jobs:

```bash
python skills/video-video-clips/scripts/new_video_clip_jobs.py \
  <project_dir>/00_intake/project_brief.locked.json \
  <project_dir>/02_storyboard/storyboard.json \
  <project_dir>/04_keyframes/keyframe_prompts.json \
  <project_dir>/05_images/keyframe_image_manifest.json \
  <project_dir>/06_video_clips/video_clip_manifest.json
```

3. Write or refresh:

```text
06_video_clips/video_clip_generation_plan.md
06_video_clips/video_clip_jobs.json
06_video_clips/comfyui_ltx_i2v_requests.json
06_video_clips/manual_video_requests.json
06_video_clips/clip_review.md
```

4. Generate video clips through the configured provider.

Preferred production provider order:

```text
1. Local ComfyUI LTX I2V workflow, when configured and available
2. Manual placement of externally generated clips into 06_video_clips/clips/
```

5. After clip files exist, sync evidence:

```bash
python skills/video-video-clips/scripts/sync_video_clip_manifest.py \
  <project_dir>/06_video_clips/video_clip_manifest.json
```

6. Validate final manifest:

```bash
python skills/video-video-clips/scripts/validate_video_clip_manifest.py --mode final \
  <project_dir>/06_video_clips/video_clip_manifest.json
```

7. If validation fails, fix missing clips, missing source keyframes, failed jobs, or bad manifest fields. Do not claim Stage 06 is complete until final validation passes.

## Test-only placeholder mode

For local pipeline testing only, this package includes:

```bash
python skills/video-video-clips/scripts/generate_placeholder_video_clips.py \
  <project_dir>/06_video_clips/video_clip_manifest.json
```

This creates small placeholder `.mp4` files and marks jobs as `succeeded` with provider `placeholder_test_video_generator`.

Do not present placeholder clips as production-quality generated video.

## Confirmation gate

After Stage 06 succeeds, ask:

```text
Stage 06 视频片段包已生成。

请确认：
A. 视频片段可以，后续进入 Stage 07 配音与音乐
B. 重生成某个镜头的视频片段
C. 调整某个镜头的动作幅度
D. 调整人物一致性 / 场景一致性
E. 改用 ComfyUI / 手动视频重新生成
F. 重新生成 Stage 06 视频片段包
```

If user chooses A:

1. Set `video_clip_manifest.json.status` to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_06_VIDEO_CLIPS_CONFIRMED",
  "video_clips_confirmed": true,
  "allowed_next_stage": "STAGE_07_AUDIO"
}
```

3. In v0.7.0, stop here. Do not continue to Stage 07 yet.

## Hard rules

- Do not write Stage 06 outputs outside the project folder.
- Do not skip source keyframe evidence.
- Do not say video clips were generated unless the corresponding clip files exist and have non-zero size.
- Do not continue to Stage 07 in v0.7.0.
- Do not modify Stage 00–05 source files unless the user explicitly asks for regeneration.
- A generated clip should correspond to exactly one storyboard shot.
- Each clip job must reference start and end keyframe images from Stage 05.
