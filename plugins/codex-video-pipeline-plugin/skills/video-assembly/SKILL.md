---
name: video-assembly
description: Stage 08 internal/recovery skill for rough-cut assembly after Stage 07 audio is confirmed. Produces FFmpeg concat lists, audio mix plan, subtitle file, edit decision list, rough cut output, and assembly evidence validation under 08_assembly/.
---

# Stage 08: Rough Cut Assembly / FFmpeg Auto Assembly

## Role

You are the Stage 08 assembly controller for the Codex video pipeline.

This skill is normally called by `$video-production-pipeline` after the user confirms Stage 07. The user should not need to call this skill manually unless recovering or rerunning Stage 08.

## Inputs

Read only from the current project folder:

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/06_video_clips/video_clip_manifest.json
<project_dir>/07_audio/audio_manifest.json
```

Do not invent a new creative direction. Use Stage 00–07 outputs as the source of truth.

## Outputs

Create all Stage 08 files under:

```text
<project_dir>/08_assembly/
```

Required files:

```text
08_assembly/assembly_plan.md
08_assembly/assembly_manifest.json
08_assembly/edit_decision_list.json
08_assembly/ffmpeg_concat_list.txt
08_assembly/audio_mix_plan.json
08_assembly/subtitles.srt
08_assembly/assembly_review.md
08_assembly/rough_cut/rough_cut.mp4
08_assembly/temp/
```

## Normal execution

1. Verify Stage 06 clip evidence and Stage 07 audio evidence are final-valid.
2. Scaffold assembly manifest:

```bash
python skills/video-assembly/scripts/new_assembly_manifest.py \
  <project_dir>/00_intake/project_brief.locked.json \
  <project_dir>/02_storyboard/storyboard.json \
  <project_dir>/06_video_clips/video_clip_manifest.json \
  <project_dir>/07_audio/audio_manifest.json \
  <project_dir>/08_assembly/assembly_manifest.json
```

3. Generate the rough cut with FFmpeg:

```bash
python skills/video-assembly/scripts/assemble_with_ffmpeg.py \
  <project_dir>/08_assembly/assembly_manifest.json
```

4. Sync output evidence:

```bash
python skills/video-assembly/scripts/sync_assembly_manifest.py \
  <project_dir>/08_assembly/assembly_manifest.json
```

5. Validate final manifest:

```bash
python skills/video-assembly/scripts/validate_assembly_manifest.py --mode final \
  <project_dir>/08_assembly/assembly_manifest.json
```

Do not claim Stage 08 is complete until final validation passes.

## Test-only placeholder mode

For local pipeline testing only, this package supports:

```bash
python skills/video-assembly/scripts/assemble_with_ffmpeg.py \
  <project_dir>/08_assembly/assembly_manifest.json \
  --placeholder-test
```

This writes a non-empty placeholder `rough_cut.mp4` and marks the provider as `placeholder_test_assembly_generator`. Do not present placeholder assembly as production-quality video.

## Confirmation gate

After Stage 08 succeeds, ask:

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

If user chooses A:

1. Set `assembly_manifest.json.status` to `confirmed` if needed.
2. Update `project_manifest.json`:

```json
{
  "current_stage": "STAGE_08_ASSEMBLY_CONFIRMED",
  "assembly_confirmed": true,
  "allowed_next_stage": "STAGE_09_QA"
}
```

3. In v1.0.0, normal pipeline should automatically continue to Stage 09 through `$video-production-pipeline`. Do not ask the user to manually invoke `$video-qa-delivery`.

## Hard rules

- Do not write Stage 08 outputs outside the project folder.
- Do not say rough cut/final video was generated unless the final output file exists and has non-zero size.
- Do not modify Stage 00–07 source files unless the user explicitly asks for regeneration.
- If FFmpeg fails, record the error in `assembly_manifest.json.errors` and ask for repair; do not pretend success.
- Preserve source clip order from storyboard unless the user explicitly asks to reorder.
- Output a rough cut and a handoff package; professional fine-editing can still be done manually.
