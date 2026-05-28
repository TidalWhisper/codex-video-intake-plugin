---
name: video-character-bible
description: Generate Stage 03 character-bible assets from a confirmed Stage 02 storyboard inside a Codex video project. Creates character_bible.md, character_bible.json, character_review.md, and reference_image_plan.json. Normal users should not call this manually; the master $video-production-pipeline should enter this stage automatically after storyboard confirmation.
---

# Video Character Bible Skill

## Purpose

This skill performs **Stage 03：人物画像 / Character Bible**.

It is primarily an internal/recovery skill. In normal usage, the user should call only:

```text
$video-production-pipeline
```

The pipeline will enter Stage 03 automatically after the user confirms the Stage 02 storyboard.

## Required input

```text
video_projects/<project_id>/00_intake/project_brief.locked.json
video_projects/<project_id>/01_script/script.json
video_projects/<project_id>/02_storyboard/storyboard.json
```

The storyboard must be confirmed by the user, or the project manifest must contain:

```json
{
  "storyboard_confirmed": true,
  "allowed_next_stage": "STAGE_03_CHARACTER_BIBLE"
}
```

## Required output

```text
video_projects/<project_id>/03_characters/
├─ character_bible.md
├─ character_bible.json
├─ character_review.md
└─ reference_image_plan.json
```

## Absolute rules

1. Do not run Stage 03 if `project_brief.locked.json` is missing.
2. Do not run Stage 03 if `script.json` is missing.
3. Do not run Stage 03 if `storyboard.json` is missing.
4. Do not rewrite the locked brief.
5. Do not rewrite the Stage 01 script unless the user explicitly asks to return to Stage 01.
6. Do not rewrite the Stage 02 storyboard unless the user explicitly asks to return to Stage 02.
7. Do not generate actual character images in v0.5.0.
8. Do not call image-generation tools, ComfyUI, TTS, music-generation tools, or FFmpeg.
9. In the normal pipeline, Stage 04 keyframe/motion prompts are generated only after the user confirms this character bible.
10. Write all Stage 03 outputs inside `<project_dir>/03_characters/`.
11. Validate `character_bible.json` before reporting success.
12. Ask the user to confirm the character bible before allowing Stage 04.

## Character-bible content requirements

### Required JSON structure

`character_bible.json` must contain at least:

```json
{
  "schema_version": "0.4.0",
  "stage": "STAGE_03_CHARACTER_BIBLE",
  "status": "draft",
  "project_id": "video_xxx",
  "source_brief": "video_projects/.../00_intake/project_brief.locked.json",
  "source_script": "video_projects/.../01_script/script.json",
  "source_storyboard": "video_projects/.../02_storyboard/storyboard.json",
  "characters": [],
  "reference_image_required": true,
  "self_check": {
    "matches_locked_brief": true,
    "matches_script": true,
    "matches_storyboard": true,
    "ready_for_keyframe_stage": true,
    "notes": []
  },
  "allowed_next_stage": null
}
```

Each character entry should include:

- `character_id` (for example `CHAR_001`)
- `name`
- `role` (main / supporting / cameo)
- `age`
- `gender_presentation`
- `appearance.face`
- `appearance.hair`
- `appearance.body`
- `appearance.clothing`
- `appearance.accessories`
- `personality`
- `emotional_arc` (list)
- `voice_profile.needed`
- `voice_profile.suggested_voice`
- `visual_consistency_prompt`
- `negative_consistency_prompt`

### Required validation

After writing `character_bible.json`, run:

```bash
python skills/video-character-bible/scripts/validate_character_bible.py --mode final <project_dir>/03_characters/character_bible.json
```

If running from inside the plugin directory:

```bash
python skills/video-character-bible/scripts/validate_character_bible.py --mode final <project_dir>/03_characters/character_bible.json
```

If validation fails, fix the JSON and validate again.

## Required final response

After Stage 03 files are written and validated, respond with:

```text
Stage 03 人物画像包已生成：
- <project_dir>/03_characters/character_bible.md
- <project_dir>/03_characters/character_bible.json
- <project_dir>/03_characters/character_review.md
- <project_dir>/03_characters/reference_image_plan.json

请确认：
A. 人物设定可以，后续进入 Stage 04 关键帧提示词
B. 修改人物外貌
C. 修改人物服装
D. 修改人物年龄/气质
E. 修改人物声音设定
F. 重新生成人物画像
```

If the user chooses A, update `<project_dir>/project_manifest.json`:

```json
{
  "current_stage": "STAGE_03_CHARACTER_BIBLE_CONFIRMED",
  "character_bible_confirmed": true,
  "allowed_next_stage": "STAGE_04_KEYFRAME_PROMPTS"
}
```

In v0.5.0, the normal `$video-production-pipeline` continues to Stage 04 after the user confirms A. When this skill is used standalone for recovery, stop after updating the manifest and let the pipeline resume.
