---
name: video-script-generation
description: Generate Stage 01 script assets for a Codex video project from a locked project_brief.locked.json. Creates story_direction, plot_structure, script, and script_review files inside the independent project folder. Must not create storyboard, image prompts, ComfyUI tasks, TTS, music, or video assembly.
---

# Video Script Generation Skill

## Purpose

This skill performs Stage 01 of the Codex video-production pipeline.

It is primarily an internal/recovery skill. In normal usage, the user should start only `$video-production-pipeline`; the pipeline enters Stage 01 automatically after the Stage 00 brief is locked.

It reads a locked Stage 00 project brief from an independent project folder and generates the script package required before storyboard creation.

Required input:

```text
video_projects/<project_id>/00_intake/project_brief.locked.json
```

Required output:

```text
video_projects/<project_id>/01_script/
├─ story_direction.md
├─ story_direction.json
├─ plot_structure.md
├─ plot_structure.json
├─ script.md
├─ script.json
└─ script_review.md
```

## Absolute Rules

1. Do not run this skill if `project_brief.locked.json` does not exist.
2. Do not run this skill if the locked brief does not contain `confirmed_by_user: true`.
3. Do not invent a different project direction than the locked brief.
4. Do not change video duration, genre, style, aspect ratio, resolution, voice mode, music mode, or final output unless the user explicitly asks to return to Stage 00 and revise the brief.
5. Do not generate a storyboard. Stage 02 handles storyboard.
6. Do not generate character image prompts. Stage 03/04 handles character and keyframe prompts.
7. Do not call image tools, ComfyUI, TTS, music generation, or FFmpeg.
8. Write all Stage 01 outputs inside `<project_dir>/01_script/`.
9. After writing the script package, ask the user for script confirmation before allowing Stage 02.

## How to find the project folder

If the user gives a path, use it.

If the user only says “继续” or “进入剧本生成”, look for the latest project under:

```text
video_projects/
```

If multiple project folders exist and the latest cannot be determined safely, ask the user to choose the project folder.

## Required pre-check

Before writing the script, inspect:

```text
<project_dir>/00_intake/project_brief.locked.json
```

The locked brief must have:

```json
{
  "status": "locked",
  "confirmed_by_user": true,
  "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION"
}
```

If not, stop and tell the user to complete `$video-project-intake` first.

## Stage 01-A: Story direction expansion

Create:

```text
<project_dir>/01_script/story_direction.md
<project_dir>/01_script/story_direction.json
```

Content must include:

- story title candidates
- core theme
- protagonist state
- emotional arc
- narrative conflict or movement
- ending direction
- how it satisfies the locked genre and style
- what should not be included

For example, if the locked idea is “一位20岁出头的女孩在落日余辉的海滩边散步”, do not immediately make it a sci-fi or horror story unless the locked genre says so. Expand within the chosen genre/style.

## Stage 01-B: Plot structure

Create:

```text
<project_dir>/01_script/plot_structure.md
<project_dir>/01_script/plot_structure.json
```

The structure must be time-coded according to the locked duration.

Guidelines:

```text
15秒：3 个节拍
30秒：4-5 个节拍
60秒：5-7 个节拍
90秒：6-9 个节拍
120秒：8-10 个节拍
180秒：10-14 个节拍
300秒：14-20 个节拍
```

Each beat should contain:

- start time
- end time
- story action
- emotional state
- visual emphasis
- voiceover/dialogue requirement if any
- music or ambience cue if needed

Do not create shot-level camera instructions yet. That belongs to Stage 02.

## Stage 01-C: Full script generation

Create:

```text
<project_dir>/01_script/script.md
<project_dir>/01_script/script.json
```

The script must include:

- title
- logline
- theme
- characters used in script
- scene/setting list
- complete time-based script
- voiceover/dialogue lines according to locked voice mode
- music/ambience notes according to locked music mode
- duration plan

If the locked brief says no voice, do not create narration or dialogue.

If the locked brief says only narration, do not create character dialogue unless it is explicitly necessary and flagged as optional.

If the locked brief says only character dialogue, do not add a narrator.

## Stage 01-D: Script self-check

Create:

```text
<project_dir>/01_script/script_review.md
```

The self-check must explicitly verify:

```text
1. 是否严格遵守 locked brief
2. 是否符合目标时长
3. 是否符合题材
4. 是否符合风格
5. 是否符合画面规格
6. 是否符合人物/主角要求
7. 是否符合配音要求
8. 是否符合背景音乐要求
9. 是否可以进入 Stage 02 分镜拆解
```

Also update `script.json.self_check`.

## Required JSON validation

Normal Stage 01 runtime must use the Codex-first hard chain:

```text
project_brief.locked.json
-> build_stage01_prompt_packet.py
-> stage01_prompt_packet.json
-> Codex generates stage01_llm_output.json
-> new_script_template.py writes official Stage 01 files
-> validate_script.py --mode final
-> if needed, build_stage01_repair_packet.py + Codex repair retry
```

Do not require the user to manually fill `stage01_llm_output.json` during normal `$video-production-pipeline` execution.

After writing `script.json`, run:

```bash
python skills/video-script-generation/scripts/validate_script.py --mode final <project_dir>/01_script/script.json
```

If running from inside the plugin directory:

```bash
python skills/video-script-generation/scripts/validate_script.py --mode final <project_dir>/01_script/script.json
```

If the validator fails, fix the JSON and run validation again before reporting success.


### Recovery-only draft validation

Only when debugging `new_script_template.py` in isolation, validate draft shape with:

```bash
python skills/video-script-generation/scripts/validate_script.py --mode draft <project_dir>/01_script/script.json
```

Draft mode confirms the JSON shape and locked-brief linkage. Final mode is required after the actual script content has been written.

## Required final response after Stage 01 files are created

After all Stage 01 files are written and validated, show only a concise summary plus confirmation menu:

```text
Stage 01 剧本包已生成：
- <project_dir>/01_script/story_direction.md
- <project_dir>/01_script/plot_structure.md
- <project_dir>/01_script/script.md
- <project_dir>/01_script/script.json
- <project_dir>/01_script/script_review.md

请确认：
A. 剧本可以，自动进入 Stage 02 分镜拆解
B. 修改故事走向
C. 修改人物设定
D. 修改旁白/对白
E. 修改视频节奏
F. 重新生成剧本
```

If this skill is being used by `$video-production-pipeline` and the user chooses A, continue directly into Stage 02 in the same conversation. Do not ask the user to manually call `$video-storyboard-generation`.

If this skill was invoked as a standalone recovery action and the user chooses A, update `<project_dir>/project_manifest.json`:

```json
{
  "current_stage": "STAGE_01_SCRIPT_CONFIRMED",
  "script_confirmed": true,
  "allowed_next_stage": "STAGE_02_STORYBOARD"
}
```

Do not perform Stage 02 in this skill. Only state:

```text
剧本已确认。下一阶段允许进入：Stage 02 分镜拆解。
```

## Output style

Be concise in terminal output. Write detailed content into files, not into the chat.

Do not dump the full script into the chat unless the user explicitly asks to view it.
