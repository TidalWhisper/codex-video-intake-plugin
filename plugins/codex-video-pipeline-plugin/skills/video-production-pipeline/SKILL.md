---
name: video-production-pipeline
description: Master entry point for the Codex video-production plugin. Starts once, asks Stage 00 intake questions one by one, locks the project brief after user confirmation, automatically continues to Stage 01 script generation, Stage 02 storyboard generation, Stage 03 character-bible generation, Stage 04 keyframe/motion prompt generation, and Stage 05 keyframe image generation, Stage 06 video clip generation, and Stage 07 voice/music generation, Stage 08 rough-cut assembly, and Stage 09 QA/delivery. Use this instead of manually invoking the individual stage skills.
---

# Video Production Pipeline Skill

## Purpose

This is the **recommended user-facing entry point** for the Codex video-production plugin.

The user should start the workflow once with:

```text
$video-production-pipeline
```

Do **not** make the user manually call:

```text
$video-project-intake
$video-script-generation
$video-storyboard-generation
$video-character-bible
$video-keyframe-prompts
$video-keyframe-images
$video-video-clips
$video-audio
$video-assembly
$video-qa-delivery
```

Those stage skills are internal/recovery skills. They exist for debugging, reruns, and manual repair when a stage fails.

## Normal pipeline

The normal flow is:

```text
Stage 00-A：逐项收集 9 个基础需求
↓
Stage 00-B：汇总 Brief，用户确认后锁定 project_brief.locked.json
↓
自动进入 Stage 01：剧本生成
↓
用户确认剧本
↓
自动进入 Stage 02：分镜脚本生成
↓
用户确认分镜
↓
自动进入 Stage 03：人物画像 / Character Bible
↓
用户确认人物设定
↓
自动进入 Stage 04：关键帧提示词 + 过渡动作提示词
↓
用户确认提示词包
↓
自动进入 Stage 05：关键帧图片生成
↓
用户确认关键帧图片
↓
自动进入 Stage 06：视频片段生成
↓
用户确认视频片段
↓
自动进入 Stage 07：配音与背景音乐
↓
用户确认音频包
↓
自动进入 Stage 08：粗剪合成 / FFmpeg 自动合成
↓
用户确认粗剪成片
↓
自动进入 Stage 09：质量检查与交付
↓
用户确认交付完成
```

## Absolute rules

1. Ask only one Stage 00 intake question per assistant turn.
2. Never print all 9 intake questions at once.
3. Do not ask the user to manually invoke the next skill during normal pipeline execution.
4. After `project_brief.locked.json` is created, automatically continue to Stage 01 in the same conversation.
5. After the user confirms the script, automatically continue to Stage 02 in the same conversation.
6. After the user confirms the storyboard, automatically continue to Stage 03 in the same conversation.
7. After the user confirms the character bible, automatically continue to Stage 04 in the same conversation.
8. After the user confirms keyframe/motion prompts, automatically continue to Stage 05 in the same conversation.
9. After the user confirms keyframe images, automatically continue to Stage 06 in the same conversation.
10. After the user confirms video clips, automatically continue to Stage 07 in the same conversation.
11. After the user confirms audio, automatically continue to Stage 08 in the same conversation.
12. After the user confirms assembly, automatically continue to Stage 09 in the same conversation.
13. Only stop for user confirmation at formal gates:
   - Brief confirmation gate
   - Script confirmation gate
   - Storyboard confirmation gate
   - Character-bible confirmation gate
   - Keyframe/motion prompt confirmation gate
   - Keyframe image confirmation gate
   - Video clip confirmation gate
   - Audio confirmation gate
   - Assembly confirmation gate
   - QA/delivery confirmation gate
14. Stage 05 may generate keyframe image files or image-generation request manifests, but must never claim image generation succeeded without file evidence.
15. Stage 06 may generate video clip files or video-generation request manifests, but must never claim clip generation succeeded without file evidence.
16. Stage 07 may generate voice/music files or audio-generation request manifests, but must never claim audio generation succeeded without file evidence.
17. Stage 08 may generate rough-cut video files through FFmpeg or manual/placeholder test mode, but must never claim assembly succeeded without file evidence.
18. Stage 09 may generate QA/delivery files, but must never claim delivery succeeded without final_delivery evidence and qa_manifest final validation.
19. Every project must live under `video_projects/<project_id>/`.
20. Every stage must write files into the current project folder, not scattered global files.
21. Never claim a stage is complete unless its expected files exist and validator scripts pass.
22. When showing current status, prefer the creator-facing entry files over raw manifests:
   - `creator_home.html`
   - `03_characters/reference_image_start_here.md`
   - `05_images/stage05_review_workbench.html`
23. If Stage 03/04 already know reference images are missing, do not only repeat technical fields. Surface the explicit recovery entry and tell the user to start there.
24. If Stage 05 requires human review, default to the workbench view first. Do not make the normal user start from `approve_stage05_review_queue.py` or `serve_stage05_review_workbench.py` unless they ask for low-level recovery commands.

## Stage state machine

Use `project_manifest.json` as the state record.

Expected states:

```text
STAGE_00_INTAKE
STAGE_00_BRIEF_LOCKED
STAGE_01_SCRIPT_GENERATION
STAGE_01_SCRIPT_REVIEW
STAGE_01_SCRIPT_CONFIRMED
STAGE_02_STORYBOARD_GENERATION
STAGE_02_STORYBOARD_REVIEW
STAGE_02_STORYBOARD_CONFIRMED
STAGE_03_CHARACTER_BIBLE_GENERATION
STAGE_03_CHARACTER_BIBLE_REVIEW
STAGE_03_CHARACTER_BIBLE_CONFIRMED
STAGE_04_KEYFRAME_PROMPTS_GENERATION
STAGE_04_KEYFRAME_PROMPTS_REVIEW
STAGE_04_KEYFRAME_PROMPTS_CONFIRMED
STAGE_05_KEYFRAME_IMAGES_GENERATION
STAGE_05_KEYFRAME_IMAGES_REVIEW
STAGE_05_KEYFRAME_IMAGES_CONFIRMED
STAGE_06_VIDEO_CLIPS_GENERATION
STAGE_06_VIDEO_CLIPS_REVIEW
STAGE_06_VIDEO_CLIPS_CONFIRMED
STAGE_07_AUDIO_GENERATION
STAGE_07_AUDIO_REVIEW
STAGE_07_AUDIO_CONFIRMED
STAGE_08_ASSEMBLY_GENERATION
STAGE_08_ASSEMBLY_REVIEW
STAGE_08_ASSEMBLY_CONFIRMED
STAGE_09_QA_GENERATION
STAGE_09_QA_REVIEW
STAGE_09_QA_CONFIRMED
PROJECT_DELIVERED
```

If a user says “继续”, inspect the latest project under `video_projects/`, read its `project_manifest.json`, and resume from the first incomplete stage.

Before summarizing a resumed project, prefer:

```bash
python skills/video-production-pipeline/scripts/show_creator_home.py
```

Use that result as the default creator-facing status view, then continue the pipeline from the first incomplete gate.

If there are multiple possible latest projects and the target is ambiguous, ask the user to choose a project directory.

## Stage 00-A: one-question intake

Follow the same one-question wizard defined by `$video-project-intake`.

Question 1: story idea.
Question 2: target duration.
Question 3: video genre.
Question 4: video style.
Question 5: visual spec: aspect ratio + resolution.
Question 6: fixed characters.
Question 7: voice.
Question 8: background music, including `song` / `instrumental` / `underscore` when music is needed.
Question 9: final output.

Do not show future questions unless the user asks for the full list.

## Stage 00-B: brief creation and locking

After all 9 answers are collected:

1. Create the independent project folder:

```bash
python skills/video-project-intake/scripts/create_project_folder.py --root video_projects --title "<short idea>"
```

2. Write:

```text
<project_dir>/00_intake/intake_state.json
<project_dir>/00_intake/project_brief.draft.json
```

3. Validate:

```bash
python skills/video-project-intake/scripts/validate_project_structure.py <project_dir>
python skills/video-project-intake/scripts/validate_project_brief.py <project_dir>/00_intake/project_brief.draft.json
```

4. Show the brief summary and ask:

```text
请选择：
A. 确认，锁定需求并自动进入 Stage 01 剧本生成
B. 修改某一项
C. 重新填写
```

5. If user confirms A, lock the brief:

```bash
python skills/video-project-intake/scripts/lock_project_brief.py <project_dir>/00_intake/project_brief.draft.json <project_dir>/00_intake/project_brief.locked.json
```

6. Update manifest to:

```json
{
  "current_stage": "STAGE_00_BRIEF_LOCKED",
  "brief_locked": true,
  "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION"
}
```

7. Immediately continue to Stage 01. Do not say “please call $video-script-generation”.

## Stage 01: script generation

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
```

Create:

```text
<project_dir>/01_script/story_direction.md
<project_dir>/01_script/story_direction.json
<project_dir>/01_script/plot_structure.md
<project_dir>/01_script/plot_structure.json
<project_dir>/01_script/script.md
<project_dir>/01_script/script.json
<project_dir>/01_script/script_review.md
```

Follow the creative rules from `$video-script-generation`.

Validate:

```bash
python skills/video-script-generation/scripts/validate_script.py --mode final <project_dir>/01_script/script.json
```

If validation fails, fix `script.json` and run validation again.

After Stage 01 succeeds, ask:

```text
Stage 01 剧本包已生成。

请确认：
A. 剧本可以，自动进入 Stage 02 分镜拆解
B. 修改故事走向
C. 修改人物设定
D. 修改旁白/对白
E. 修改视频节奏
F. 重新生成剧本
```

If the user chooses A:

1. Update `script.json` status to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_01_SCRIPT_CONFIRMED",
  "script_confirmed": true,
  "allowed_next_stage": "STAGE_02_STORYBOARD"
}
```

3. Immediately continue to Stage 02. Do not ask the user to call another skill.

## Stage 02: storyboard generation

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/01_script/script.json
```

Create:

```text
<project_dir>/02_storyboard/storyboard.md
<project_dir>/02_storyboard/storyboard.json
<project_dir>/02_storyboard/storyboard_review.md
```

Validate:

```bash
python skills/video-storyboard-generation/scripts/validate_storyboard.py --mode final <project_dir>/02_storyboard/storyboard.json
```

If validation fails, fix `storyboard.json` and validate again.

After Stage 02 succeeds, ask:

```text
Stage 02 分镜脚本已生成。

请确认：
A. 分镜可以，自动进入 Stage 03 人物画像
B. 修改镜头节奏
C. 修改镜头数量
D. 修改某个镜头
E. 重新生成分镜
```

If the user chooses A:

1. Update `storyboard.json` status to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_02_STORYBOARD_CONFIRMED",
  "storyboard_confirmed": true,
  "allowed_next_stage": "STAGE_03_CHARACTER_BIBLE"
}
```

3. Immediately continue to Stage 03. Do not ask the user to call another skill.

## Stage 03: character-bible generation

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/01_script/script.json
<project_dir>/02_storyboard/storyboard.json
```

Create:

```text
<project_dir>/03_characters/character_bible.md
<project_dir>/03_characters/character_bible.json
<project_dir>/03_characters/character_review.md
<project_dir>/03_characters/reference_image_plan.json
```

The character bible must:

1. Identify all primary recurring characters, and optionally important supporting characters.
2. For each major character, lock identity, appearance, clothing, emotional arc, and voice suggestions.
3. Provide a `visual_consistency_prompt` and a `negative_consistency_prompt`.
4. Mark whether reference-image generation will be needed in later stages.

Validate:

```bash
python skills/video-character-bible/scripts/validate_character_bible.py --mode final <project_dir>/03_characters/character_bible.json
```

If validation fails, fix `character_bible.json` and validate again.

After Stage 03 succeeds, ask:

```text
Stage 03 人物画像包已生成。

请确认：
A. 人物设定可以，后续进入 Stage 04 关键帧提示词
B. 修改人物外貌
C. 修改人物服装
D. 修改人物年龄/气质
E. 修改人物声音设定
F. 重新生成人物画像
```

If `reference_image_status.all_present = false`, also surface:

```text
先看：
<project_dir>/03_characters/reference_image_start_here.md
```

This is the default creator-facing recovery entry. Do not only quote JSON fields like `reference_images_ready=false`.

If the user chooses A:

1. Update `character_bible.json` status to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_03_CHARACTER_BIBLE_CONFIRMED",
  "character_bible_confirmed": true,
  "allowed_next_stage": "STAGE_04_KEYFRAME_PROMPTS"
}
```

3. Immediately continue to Stage 04. Do not ask the user to call another skill.

## Stage 04: keyframe prompts and transition-motion prompts

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/01_script/script.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/03_characters/character_bible.json
```

Create:

```text
<project_dir>/04_keyframes/keyframe_prompts.md
<project_dir>/04_keyframes/keyframe_prompts.json
<project_dir>/04_keyframes/motion_prompts.json
<project_dir>/04_keyframes/prompt_review.md
```

The prompt package must:

1. Create one prompt record for every storyboard shot.
2. Provide start keyframe prompt, end keyframe prompt, and motion prompt for each shot.
3. Provide camera, lighting, style, consistency, and negative prompts for each shot.
4. Preserve character consistency using `character_bible.json`.
5. Create transition-motion prompts between adjacent shots where useful.
6. Prepare for Stage 05 image generation without actually generating images.

Validate:

```bash
python skills/video-keyframe-prompts/scripts/validate_keyframe_prompts.py --mode final <project_dir>/04_keyframes/keyframe_prompts.json
```

If validation fails, fix `keyframe_prompts.json` and validate again.

After Stage 04 succeeds, ask:

```text
Stage 04 关键帧提示词包已生成。

请确认：
A. 提示词可以，后续进入 Stage 05 关键帧图片生成
B. 修改某个镜头的关键帧提示词
C. 修改过渡动作提示词
D. 修改角色一致性提示词
E. 修改负面提示词
F. 重新生成 Stage 04 提示词包
```

If `stage05_execution_readiness.safe_to_auto_generate = false`, explicitly tell the user to open:

```text
<project_dir>/04_keyframes/stage05_start_here.md
```

That file should be treated as the normal next step before Stage 05, not as a debug artifact.

If the user chooses A:

1. Update `keyframe_prompts.json` status to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_04_KEYFRAME_PROMPTS_CONFIRMED",
  "keyframe_prompts_confirmed": true,
  "allowed_next_stage": "STAGE_05_KEYFRAME_IMAGES"
}
```

3. Immediately continue to Stage 05. Do not ask the user to call another skill.

## Stage 05: keyframe image generation

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/04_keyframes/keyframe_prompts.json
```

Create:

```text
<project_dir>/05_images/image_generation_plan.md
<project_dir>/05_images/image_generation_jobs.json
<project_dir>/05_images/keyframe_image_manifest.json
<project_dir>/05_images/openai_image_requests.json
<project_dir>/05_images/comfyui_image_requests.json
<project_dir>/05_images/image_review.md
<project_dir>/05_images/keyframes/*.png
```

The image package must:

1. Create start and end keyframe image jobs for every storyboard shot represented in `keyframe_prompts.json`.
2. Preserve aspect ratio, resolution, style, camera, and character consistency prompts.
3. Prefer OpenAI image generation when available, then local ComfyUI, then manual placement.
4. Record file evidence in `keyframe_image_manifest.json` for every required image.
5. Never claim an image is generated unless its file exists and has non-zero size.

For the local ComfyUI txt2img path, Stage 05 now uses a minimal style-family router:

- `realistic`
- `anime`
- `guofeng`
- `stylized`

When the workflow name is left at the default `txt2img_keyframe`, the runner should auto-route each job through the mapped style-family workflow recorded in `keyframe_image_manifest.json`.

Scaffold jobs:

```bash
python skills/video-keyframe-images/scripts/new_keyframe_image_jobs.py <project_dir>/00_intake/project_brief.locked.json <project_dir>/04_keyframes/keyframe_prompts.json <project_dir>/05_images/keyframe_image_manifest.json
```

After real image generation or manual placement, sync evidence:

```bash
python skills/video-keyframe-images/scripts/sync_keyframe_image_manifest.py <project_dir>/05_images/keyframe_image_manifest.json
```

Validate:

```bash
python skills/video-keyframe-images/scripts/validate_keyframe_image_manifest.py --mode final <project_dir>/05_images/keyframe_image_manifest.json
```

For local flow testing only, placeholder images may be created with:

```bash
python skills/video-keyframe-images/scripts/generate_placeholder_keyframe_images.py <project_dir>/05_images/keyframe_image_manifest.json
```

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

When Stage 05 still requires human review, the default user-facing entry is:

```text
<project_dir>/05_images/stage05_review_workbench.html
```

Surface that first. Only mention `serve_stage05_review_workbench.py` or `approve_stage05_review_queue.py` as advanced recovery commands.

If the user chooses A:

1. Update `keyframe_image_manifest.json` status to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_05_KEYFRAME_IMAGES_CONFIRMED",
  "keyframe_images_confirmed": true,
  "allowed_next_stage": "STAGE_06_VIDEO_CLIPS"
}
```

3. Immediately continue to Stage 06. Do not ask the user to call another skill.

## Stage 06: video clip generation

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/04_keyframes/keyframe_prompts.json
<project_dir>/05_images/keyframe_image_manifest.json
```

Create:

```text
<project_dir>/06_video_clips/video_clip_generation_plan.md
<project_dir>/06_video_clips/video_clip_jobs.json
<project_dir>/06_video_clips/video_clip_manifest.json
<project_dir>/06_video_clips/comfyui_ltx_i2v_requests.json
<project_dir>/06_video_clips/manual_video_requests.json
<project_dir>/06_video_clips/clip_review.md
<project_dir>/06_video_clips/clips/*.mp4
```

The video clip package must:

1. Create one I2V video clip job for every storyboard shot represented in `keyframe_prompts.json`.
2. Use the Stage 05 start/end keyframe images as source evidence.
3. Use Stage 04 `motion_prompt`, camera, style, and consistency prompts as source of truth.
4. Prefer local ComfyUI LTX I2V, then manual placement.
5. Record file evidence in `video_clip_manifest.json` for every required clip.
6. Never claim a clip is generated unless its file exists and has non-zero size.

Scaffold jobs:

```bash
python skills/video-video-clips/scripts/new_video_clip_jobs.py <project_dir>/00_intake/project_brief.locked.json <project_dir>/02_storyboard/storyboard.json <project_dir>/04_keyframes/keyframe_prompts.json <project_dir>/05_images/keyframe_image_manifest.json <project_dir>/06_video_clips/video_clip_manifest.json
```

After real video generation or manual placement, sync evidence:

```bash
python skills/video-video-clips/scripts/sync_video_clip_manifest.py <project_dir>/06_video_clips/video_clip_manifest.json
```

Validate:

```bash
python skills/video-video-clips/scripts/validate_video_clip_manifest.py --mode final <project_dir>/06_video_clips/video_clip_manifest.json
```

For local flow testing only, placeholder clips may be created with:

```bash
python skills/video-video-clips/scripts/generate_placeholder_video_clips.py <project_dir>/06_video_clips/video_clip_manifest.json
```

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

If the user chooses A:

1. Update `video_clip_manifest.json` status to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_06_VIDEO_CLIPS_CONFIRMED",
  "video_clips_confirmed": true,
  "allowed_next_stage": "STAGE_07_AUDIO"
}
```

3. Immediately continue to Stage 07. Do not ask the user to call another skill.

## Stage 07: voice and background music

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/01_script/script.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/03_characters/character_bible.json
<project_dir>/06_video_clips/video_clip_manifest.json
```

Create:

```text
<project_dir>/07_audio/audio_plan.md
<project_dir>/07_audio/audio_jobs.json
<project_dir>/07_audio/audio_manifest.json
<project_dir>/07_audio/indextts2_requests.json
<project_dir>/07_audio/music_requests.json
<project_dir>/07_audio/audio_review.md
<project_dir>/07_audio/voice/*.wav
<project_dir>/07_audio/music/*.wav
```

The audio package must:

1. Create voiceover/dialogue jobs according to `project_brief.locked.json` and storyboard/script text.
2. Create background music jobs when Stage 00 says music is required.
3. Prefer IndexTTS2 for voice, and prefer AceStep via local ComfyUI for music, then `local_music_library`, then manual placement.
4. Record file evidence in `audio_manifest.json` for every required voice/music file.
5. Never claim audio is generated unless files exist and have non-zero size.

When Stage 07 music uses the default AceStep workflow:

1. Call `$acestep-prompt-builder` first.
2. Set `music_profile` before prompt construction:
   - `song` for lyric-led vocal tracks
   - `instrumental` for pure music with no vocals
   - `underscore` for background BGM, and treat this as the Stage 07 default
3. Produce workflow-ready `tags`, `lyrics`, `bpm`, `language`, `keyscale`, and `timesignature`.
4. Feed those fields into `AceStep_Music_Workflow.json` through `run_comfyui_music.py`.
5. Keep duration outside the prompt-builder output; continue to map duration from the Stage 07 music job into the workflow `duration` and latent `seconds`.

If Stage 07 explicitly switches to `HeartMuLa_workflow_fixed_importable.json`, call `$heartmula-prompt-builder` instead before constructing the workflow payload.

Scaffold jobs:

```bash
python skills/video-audio/scripts/new_audio_jobs.py <project_dir>/00_intake/project_brief.locked.json <project_dir>/01_script/script.json <project_dir>/02_storyboard/storyboard.json <project_dir>/03_characters/character_bible.json <project_dir>/06_video_clips/video_clip_manifest.json <project_dir>/07_audio/audio_manifest.json
```

After real audio generation or manual placement, sync evidence:

```bash
python skills/video-audio/scripts/sync_audio_manifest.py <project_dir>/07_audio/audio_manifest.json
```

Validate:

```bash
python skills/video-audio/scripts/validate_audio_manifest.py --mode final <project_dir>/07_audio/audio_manifest.json
```

For local flow testing only, placeholder audio may be created with:

```bash
python skills/video-audio/scripts/generate_placeholder_audio.py <project_dir>/07_audio/audio_manifest.json
```

After Stage 07 succeeds, ask:

```text
Stage 07 配音与背景音乐包已生成。

请确认：
A. 音频可以，后续进入 Stage 08 粗剪合成
B. 重生成某一句旁白/对白
C. 调整某个角色的音色/情绪
D. 调整背景音乐模式（song / instrumental / underscore）或风格/节奏/音量
E. 改用 IndexTTS2 / ComfyUI / 本地音乐库 / 手动音频重新生成
F. 重新生成 Stage 07 音频包
```

If the user chooses A:

1. Update `audio_manifest.json` status to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_07_AUDIO_CONFIRMED",
  "audio_confirmed": true,
  "allowed_next_stage": "STAGE_08_ASSEMBLY"
}
```

3. In v1.0.0, automatically continue to Stage 08. Do not ask the user to manually invoke `$video-assembly`.


## Stage 08: rough-cut assembly

After Stage 07 is confirmed, automatically continue to Stage 08. Do not ask the user to manually call `$video-assembly`.

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/06_video_clips/video_clip_manifest.json
<project_dir>/07_audio/audio_manifest.json
```

Create:

```text
<project_dir>/08_assembly/assembly_plan.md
<project_dir>/08_assembly/assembly_manifest.json
<project_dir>/08_assembly/edit_decision_list.json
<project_dir>/08_assembly/ffmpeg_concat_list.txt
<project_dir>/08_assembly/audio_mix_plan.json
<project_dir>/08_assembly/subtitles.srt
<project_dir>/08_assembly/assembly_review.md
<project_dir>/08_assembly/rough_cut/rough_cut.mp4
```

Run validation before claiming success:

```bash
python skills/video-assembly/scripts/validate_assembly_manifest.py --mode final <project_dir>/08_assembly/assembly_manifest.json
```

Confirmation gate:

```text
Stage 08 粗剪成片已生成。

请确认：
A. 粗剪可以，后续进入 Stage 09 质量检查与交付
B. 调整某个镜头顺序
C. 替换某个视频片段
D. 调整配音/背景音乐音量
E. 修改字幕
F. 重新合成粗剪
```

If user chooses A, update manifest to `STAGE_08_ASSEMBLY_CONFIRMED`, set `assembly_confirmed=true`, set `allowed_next_stage=STAGE_09_QA`, and automatically continue to Stage 09. Do not ask the user to manually invoke `$video-qa-delivery`.

## Stage 09: QA and delivery

After Stage 08 is confirmed, automatically continue to Stage 09. Do not ask the user to manually call `$video-qa-delivery`.

Read:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/08_assembly/assembly_manifest.json
```

Create:

```text
<project_dir>/09_qa/qa_plan.md
<project_dir>/09_qa/qa_manifest.json
<project_dir>/09_qa/qa_checklist.json
<project_dir>/09_qa/issue_report.md
<project_dir>/09_qa/delivery_report.md
<project_dir>/09_qa/delivery_manifest.json
<project_dir>/09_qa/asset_index.json
<project_dir>/09_qa/qa_review.md
<project_dir>/09_qa/final_delivery/rough_cut.mp4
<project_dir>/09_qa/final_delivery/README_DELIVERY.md
<project_dir>/09_qa/final_delivery/delivery_report.md
<project_dir>/09_qa/final_delivery/asset_index.json
```

Scaffold QA manifest:

```bash
python skills/video-qa-delivery/scripts/new_qa_manifest.py <project_dir>/00_intake/project_brief.locked.json <project_dir>/08_assembly/assembly_manifest.json <project_dir>/09_qa/qa_manifest.json
```

Create delivery package and sync evidence:

```bash
python skills/video-qa-delivery/scripts/package_delivery.py <project_dir>/09_qa/qa_manifest.json
```

Validate before claiming delivery success:

```bash
python skills/video-qa-delivery/scripts/validate_qa_manifest.py --mode final <project_dir>/09_qa/qa_manifest.json
```

Confirmation gate:

```text
Stage 09 质量检查与交付包已生成。

请确认：
A. 确认交付完成，项目结束
B. 返回 Stage 08 重新合成粗剪
C. 返回 Stage 07 调整配音/音乐
D. 返回 Stage 06 替换视频片段
E. 返回 Stage 05 替换关键帧图片
F. 导出问题清单，暂不结束项目
```

If user chooses A, update manifest to `STAGE_09_QA_CONFIRMED`, set `qa_confirmed=true`, set `delivery_complete=true`, set `allowed_next_stage=PROJECT_DELIVERED`, and stop. The project is now delivered.
