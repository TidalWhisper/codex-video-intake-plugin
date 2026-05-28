---
name: video-storyboard-generation
description: Generate Stage 02 storyboard assets from a confirmed Stage 01 script inside a Codex video project. Creates storyboard.md, storyboard.json, and storyboard_review.md. Normal users should not call this manually; the master $video-production-pipeline should enter this stage automatically after script confirmation.
---

# Video Storyboard Generation Skill

## Purpose

This skill performs **Stage 02：分镜脚本生成**.

It is primarily an internal/recovery skill. In normal usage, the user should call only:

```text
$video-production-pipeline
```

The pipeline will enter Stage 02 automatically after the user confirms the Stage 01 script.

## Required input

```text
video_projects/<project_id>/00_intake/project_brief.locked.json
video_projects/<project_id>/01_script/script.json
```

The script must be confirmed by the user, or the project manifest must contain:

```json
{
  "script_confirmed": true,
  "allowed_next_stage": "STAGE_02_STORYBOARD"
}
```

## Required output

```text
video_projects/<project_id>/02_storyboard/
├─ storyboard.md
├─ storyboard.json
└─ storyboard_review.md
```

## Absolute rules

1. Do not run Stage 02 if `project_brief.locked.json` is missing.
2. Do not run Stage 02 if `script.json` is missing.
3. Do not rewrite the locked brief.
4. Do not rewrite the Stage 01 script unless the user explicitly asks to return to Stage 01.
5. Do not generate character portraits.
6. Do not generate keyframe prompts yet.
7. Do not call image-generation tools, ComfyUI, TTS, music-generation tools, or FFmpeg.
8. Write all Stage 02 outputs inside `<project_dir>/02_storyboard/`.
9. Validate `storyboard.json` before reporting success.
10. Ask the user to confirm the storyboard before allowing Stage 03.

## Storyboard content requirements

Generate a director-level shot list based on the locked brief and confirmed script.

Each shot in `storyboard.json` must include:

```json
{
  "shot_id": "S001",
  "start": "00:00",
  "end": "00:05",
  "duration_sec": 5,
  "scene": "落日海滩",
  "camera": "wide shot / medium shot / close-up / tracking shot etc.",
  "composition": "画面构图说明",
  "action": "人物或主体动作",
  "emotion": "情绪",
  "dialogue": "角色对白，没有则为空字符串",
  "voiceover": "旁白，没有则为空字符串",
  "sound_music": "环境声或音乐提示",
  "transition_to_next": "转场方式",
  "production_note": "给后续关键帧/视频生成阶段的注意事项"
}
```

Shot count guidance:

```text
15秒：3-5 个镜头
30秒：5-8 个镜头
60秒：8-12 个镜头
90秒：12-16 个镜头
120秒：16-22 个镜头
180秒：22-32 个镜头
300秒：35-55 个镜头
```

The total duration should approximately match the locked target duration. Minor rounding differences are acceptable.

## Required JSON shape

`storyboard.json` must use this shape:

```json
{
  "schema_version": "0.3.0",
  "stage": "STAGE_02_STORYBOARD_GENERATION",
  "status": "draft",
  "project_id": "video_xxx",
  "source_brief": "video_projects/.../00_intake/project_brief.locked.json",
  "source_script": "video_projects/.../01_script/script.json",
  "target_duration_sec": 30,
  "shot_count": 6,
  "shots": [],
  "self_check": {
    "matches_locked_brief": true,
    "matches_script": true,
    "duration_fits": true,
    "ready_for_character_stage": true,
    "notes": []
  },
  "allowed_next_stage": null
}
```

## Required validation

After writing `storyboard.json`, run:

```bash
python skills/video-storyboard-generation/scripts/validate_storyboard.py --mode final <project_dir>/02_storyboard/storyboard.json
```

If running from inside the plugin directory:

```bash
python skills/video-storyboard-generation/scripts/validate_storyboard.py --mode final <project_dir>/02_storyboard/storyboard.json
```

If validation fails, fix the JSON and validate again.

## Required final response

After Stage 02 files are written and validated, respond with:

```text
Stage 02 分镜脚本已生成：
- <project_dir>/02_storyboard/storyboard.md
- <project_dir>/02_storyboard/storyboard.json
- <project_dir>/02_storyboard/storyboard_review.md

请确认：
A. 分镜可以，后续进入 Stage 03 人物画像
B. 修改镜头节奏
C. 修改镜头数量
D. 修改某个镜头
E. 重新生成分镜
```

If the user chooses A, update `<project_dir>/project_manifest.json`:

```json
{
  "current_stage": "STAGE_02_STORYBOARD_CONFIRMED",
  "storyboard_confirmed": true,
  "allowed_next_stage": "STAGE_03_CHARACTER_BIBLE"
}
```

In v0.5.0, after the user confirms A in the normal pipeline, immediately continue to Stage 03 character-bible generation. When using this skill standalone for recovery, stop after updating the manifest.
