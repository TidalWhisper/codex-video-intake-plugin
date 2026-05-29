---
name: video-audio
description: Stage 07 internal/recovery skill for generating voiceover/dialogue and background music assets after Stage 06 video clips are confirmed. Produces IndexTTS2 request manifests, music request manifests, audio evidence, and validation reports under 07_audio/.
---

# Stage 07: Voice and Background Music

## Role

You are the Stage 07 audio production controller for the Codex video pipeline.

This skill is normally called by `$video-production-pipeline` after the user confirms Stage 06. The user should not need to call this skill manually unless recovering or rerunning Stage 07.

## Inputs

Read only from the current project folder:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/01_script/script.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/03_characters/character_bible.json
<project_dir>/06_video_clips/video_clip_manifest.json
```

Do not invent a new creative direction. Use the locked brief, script, storyboard, character bible, and Stage 06 clip evidence as the source of truth.

## Outputs

Create all Stage 07 files under:

```text
<project_dir>/07_audio/
```

Required files:

```text
07_audio/audio_plan.md
07_audio/audio_jobs.json
07_audio/audio_manifest.json
07_audio/indextts2_requests.json
07_audio/music_requests.json
07_audio/audio_review.md
07_audio/voice/
07_audio/music/
```

Expected generated files:

```text
07_audio/voice/S001_voiceover.wav
07_audio/voice/S002_dialogue_001.wav
07_audio/music/BGM_MAIN.wav
```

Actual required files depend on Stage 00 voice/music selections and the storyboard/script content.

## Normal execution

1. Verify Stage 06 is confirmed or at least `video_clip_manifest.json` has validated clip evidence and is ready for audio.
2. Scaffold audio jobs:

```bash
python skills/video-audio/scripts/new_audio_jobs.py   <project_dir>/00_intake/project_brief.locked.json   <project_dir>/01_script/script.json   <project_dir>/02_storyboard/storyboard.json   <project_dir>/03_characters/character_bible.json   <project_dir>/06_video_clips/video_clip_manifest.json   <project_dir>/07_audio/audio_manifest.json
```

3. Write or refresh:

```text
07_audio/audio_plan.md
07_audio/audio_jobs.json
07_audio/indextts2_requests.json
07_audio/music_requests.json
07_audio/audio_review.md
```

4. Generate voice and music through configured providers.

Preferred provider order:

```text
Voice: IndexTTS2 via local ComfyUI / local IndexTTS2 API → manual placement
Music: AceStep via local ComfyUI → local library → manual placement
```

If the selected ComfyUI music workflow is `AceStep_Music_Workflow.json`, use `$acestep-prompt-builder` before preparing Stage 07 music inputs.

AceStep is not a plain one-line music prompt workflow. Before calling it:

- set Stage 07 `music_profile` first:
  - `song`: vocal song with lyrics
  - `instrumental`: pure music without vocals
  - `underscore`: background-first BGM, default for `BGM_MAIN`
- emit workflow-ready `tags`, `lyrics`, `bpm`, `language`, `keyscale`, and `timesignature`
- keep `tags` as caption-style control text with compact metadata tags
- keep lyrics under section tags such as `[intro]`, `[verse]`, `[pre-chorus]`, `[chorus]`, `[bridge]`, and `[outro]`
- for `instrumental` and `underscore`, keep those sections but write instrumental cue text instead of sung lines
- keep duration outside the prompt builder and continue to map duration from the Stage 07 job into the workflow `duration` field

If the selected ComfyUI music workflow is `HeartMuLa_workflow_fixed_importable.json`, use `$heartmula-prompt-builder` instead.

5. After audio files exist, sync evidence:

```bash
python skills/video-audio/scripts/sync_audio_manifest.py   <project_dir>/07_audio/audio_manifest.json
```

6. Validate final manifest:

```bash
python skills/video-audio/scripts/validate_audio_manifest.py --mode final   <project_dir>/07_audio/audio_manifest.json
```

7. If validation fails, fix missing voice files, missing music files, failed jobs, or bad manifest fields. Do not claim Stage 07 is complete until final validation passes.

## Test-only placeholder mode

For local pipeline testing only, this package includes:

```bash
python skills/video-audio/scripts/generate_placeholder_audio.py   <project_dir>/07_audio/audio_manifest.json
```

This creates small valid `.wav` files and marks jobs as `succeeded` with provider `placeholder_test_audio_generator`.

Do not present placeholder audio as production-quality generated voice or music.

## Confirmation gate

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

If user chooses A:

1. Set `audio_manifest.json.status` to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_07_AUDIO_CONFIRMED",
  "audio_confirmed": true,
  "allowed_next_stage": "STAGE_08_ASSEMBLY"
}
```

3. In v1.0.0, normal pipeline should automatically continue to Stage 08 through `$video-production-pipeline`. Do not ask the user to manually invoke `$video-assembly`.

## Hard rules

- Do not write Stage 07 outputs outside the project folder.
- Do not say voice/music was generated unless the corresponding audio files exist and have non-zero size.
- Do not call FFmpeg directly from Stage 07. Stage 08 owns FFmpeg rough-cut assembly.
- Do not modify Stage 00–06 source files unless the user explicitly asks for regeneration.
- Each voice job must preserve the source shot id and source text.
- Every required voice/music job must have file evidence before Stage 07 can be confirmed.
