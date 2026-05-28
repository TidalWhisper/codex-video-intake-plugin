---
name: video-keyframe-prompts
description: Stage 04 of the Codex video-production pipeline. Generate keyframe prompts and transition-motion prompts from the locked brief, confirmed script, confirmed storyboard, and confirmed character bible. Normally invoked automatically by $video-production-pipeline after Stage 03 confirmation.
---

# Stage 04：关键帧提示词 + 过渡动作提示词

## Purpose

This skill generates the **production prompt package** needed before actual image/video rendering.

It does **not** generate images. It does **not** call GPT Image, ComfyUI, LTX, IndexTTS2, music tools, FFmpeg, or any renderer.

It only creates structured prompt assets for the next stage.

## Required input

```text
video_projects/<project_id>/00_intake/project_brief.locked.json
video_projects/<project_id>/01_script/script.json
video_projects/<project_id>/02_storyboard/storyboard.json
video_projects/<project_id>/03_characters/character_bible.json
```

The character bible must be confirmed, or the project manifest must contain:

```json
{
  "character_bible_confirmed": true,
  "allowed_next_stage": "STAGE_04_KEYFRAME_PROMPTS"
}
```

## Required output

```text
video_projects/<project_id>/04_keyframes/
├─ keyframe_prompts.md
├─ keyframe_prompts.json
├─ motion_prompts.json
└─ prompt_review.md
```

## Absolute rules

1. Do not run Stage 04 if `project_brief.locked.json` is missing.
2. Do not run Stage 04 if `script.json` is missing.
3. Do not run Stage 04 if `storyboard.json` is missing.
4. Do not run Stage 04 if `character_bible.json` is missing.
5. Do not rewrite the locked brief, script, storyboard, or character bible.
6. Do not generate actual images.
7. Do not call GPT Image, ComfyUI, LTX, TTS, music tools, FFmpeg, browser automation, or any renderer.
8. Create one prompt record for every storyboard shot.
9. Create transition-motion prompts between adjacent shots where useful.
10. Preserve character consistency by inheriting each character's `visual_consistency_prompt` and `negative_consistency_prompt`.
11. Write all Stage 04 outputs inside `<project_dir>/04_keyframes/`.
12. Validate `keyframe_prompts.json` before reporting success.
13. Ask the user to confirm the prompt package before allowing Stage 05 image generation.

## Prompt package requirements

`keyframe_prompts.json` must contain:

```json
{
  "schema_version": "0.5.0",
  "stage": "STAGE_04_KEYFRAME_PROMPTS",
  "status": "draft",
  "project_id": "video_xxx",
  "source_brief": "video_projects/.../00_intake/project_brief.locked.json",
  "source_script": "video_projects/.../01_script/script.json",
  "source_storyboard": "video_projects/.../02_storyboard/storyboard.json",
  "source_character_bible": "video_projects/.../03_characters/character_bible.json",
  "shot_prompts": [],
  "transition_prompts": [],
  "global_negative_prompt": "",
  "self_check": {
    "matches_locked_brief": true,
    "matches_script": true,
    "matches_storyboard": true,
    "uses_character_consistency": true,
    "covers_all_storyboard_shots": true,
    "ready_for_image_generation": true,
    "notes": []
  },
  "allowed_next_stage": null
}
```

Each `shot_prompts[]` entry should include:

- `shot_id`
- `duration_sec`
- `characters`
- `scene_summary`
- `start_keyframe_prompt`
- `end_keyframe_prompt`
- `motion_prompt`
- `camera_prompt`
- `lighting_prompt`
- `style_prompt`
- `consistency_prompt`
- `negative_prompt`
- `image_generation_notes`
- `video_generation_notes`
- `dependencies.reference_images`
- `dependencies.previous_shot_id`
- `dependencies.next_shot_id`

Each `transition_prompts[]` entry should include:

- `transition_id`
- `from_shot_id`
- `to_shot_id`
- `transition_type`
- `transition_motion_prompt`
- `continuity_requirements`

## Required validation

After writing `keyframe_prompts.json`, run:

```bash
python skills/video-keyframe-prompts/scripts/validate_keyframe_prompts.py --mode final <project_dir>/04_keyframes/keyframe_prompts.json
```

If running from inside the plugin directory:

```bash
python skills/video-keyframe-prompts/scripts/validate_keyframe_prompts.py --mode final <project_dir>/04_keyframes/keyframe_prompts.json
```

If validation fails, fix the JSON and validate again.

## Required final response

After Stage 04 files are written and validated, respond with:

```text
Stage 04 关键帧提示词包已生成：
- <project_dir>/04_keyframes/keyframe_prompts.md
- <project_dir>/04_keyframes/keyframe_prompts.json
- <project_dir>/04_keyframes/motion_prompts.json
- <project_dir>/04_keyframes/prompt_review.md

请确认：
A. 提示词可以，后续进入 Stage 05 关键帧图片生成
B. 修改某个镜头的关键帧提示词
C. 修改过渡动作提示词
D. 修改角色一致性提示词
E. 修改负面提示词
F. 重新生成 Stage 04 提示词包
```

If the user chooses A, update `<project_dir>/project_manifest.json`:

```json
{
  "current_stage": "STAGE_04_KEYFRAME_PROMPTS_CONFIRMED",
  "keyframe_prompts_confirmed": true,
  "allowed_next_stage": "STAGE_05_KEYFRAME_IMAGES"
}
```

In v0.5.0, stop after Stage 04 confirmation. Do not continue to Stage 05 yet.
