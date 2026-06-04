---
name: video-project-intake
description: Start a video-production project in Codex CLI with a mandatory first-layer intake gate. Ask the 9 required questions one by one, create one independent project folder per video project, generate project_brief.draft.json after all answers are collected, and lock project_brief.locked.json only after explicit user confirmation. Use before any scriptwriting, storyboard, image, ComfyUI, TTS, music, or FFmpeg work.
---

# Codex Video Project Intake Skill

## Purpose

This skill is Stage 00 of the Codex video-production plugin.

It prevents Codex from immediately writing scripts, storyboards, character sheets, image prompts, ComfyUI tasks, TTS tasks, music prompts, or FFmpeg commands before the user has confirmed the first-layer project information.

Current scope:

- Stage 00-A: collect the 9 first-layer required fields, one question at a time.
- Stage 00-B: summarize the answers, create an independent project folder, write `project_brief.draft.json`, validate it, ask the user to confirm, then write `project_brief.locked.json`.
- Final confirmation loop: route `A. 确认 / B. 修改某一项 / C. 重新填写` through one pipeline-owned controller.

After the brief is locked, Stage 01 is allowed. In the normal user flow, `$video-production-pipeline` must automatically continue to Stage 01 in the same conversation. This individual skill is now a recovery/debug entry point and must not tell the user to manually invoke the next stage during normal pipeline mode.

## Official runtime entry

Normal Stage 00 execution must go through:

```bash
python skills/video-production-pipeline/scripts/run_stage00_controller.py
```

This controller is the only official Stage 00 entry for normal pipeline usage.
It internally orchestrates:

- `run_stage00_intake_turn.py` for Stage 00-A one-question intake
- `run_stage00_brief_from_intake.py` for Stage 00-B draft brief generation
- `run_stage00_lock_and_continue.py` for `A. 确认` lock-and-continue handoff

Do not describe `lock_project_brief.py` or `new_project_brief_template.py` as the normal user path.
`new_project_brief_template.py` is legacy/debug-only.

## Absolute Rules

When this skill is active, follow these rules strictly:

1. Do not write a script.
2. Do not create a storyboard.
3. Do not create character portraits.
4. Do not create image prompts.
5. Do not call image-generation tools.
6. Do not call ComfyUI.
7. Do not call TTS.
8. Do not prepare music-generation tasks.
9. Do not run video assembly or FFmpeg.
10. Only ask, normalize, validate, summarize, confirm, and lock first-layer intake information.
11. Ask only one intake question per assistant turn.
12. Never print all 9 questions at once.
13. Never advance to the next question until the current question has a usable answer.
14. Do not mark a project as confirmed unless the user explicitly says confirm/确认/同意/进入下一步/开始剧本生成 or chooses the confirmation option.
15. If the user says “默认”, use the default value only for fields that allow a default.
16. The `idea` field must never be invented. If the user did not provide a story idea, ask for it.
17. Every video project must be stored in its own project folder under `video_projects/<project_id>/`.
18. Do not write final project files directly into `.video_project/` unless the user explicitly asks for legacy mode.

## Required project folder layout

When all 9 answers are collected, create an independent folder for this project:

```text
video_projects/<project_id>/
├─ project_manifest.json
├─ 00_intake/
│  ├─ intake_state.json
│  ├─ project_brief.draft.json
│  └─ project_brief.locked.json
├─ 01_script/
├─ 02_storyboard/
├─ 03_characters/
├─ 04_keyframes/
├─ 05_images/
├─ 06_video_clips/
├─ 07_audio/
│  ├─ voice/
│  └─ music/
├─ 08_assembly/
├─ 09_qa/
└─ logs/
```

Use `references/project_folder_structure.md` as the source of truth.

Preferred creation command:

```bash
python skills/video-project-intake/scripts/create_project_folder.py --root video_projects --title "<short title or idea>"
```

If running from inside the plugin directory:

```bash
python skills/video-project-intake/scripts/create_project_folder.py --root video_projects --title "<short title or idea>"
```

On Windows, if `python` does not work, use `py`.

## First-layer required fields

The first-layer required fields are:

1. `idea`: user's story idea or concept. Free text. Required. No default.
2. `target_duration`: video length. Required.
3. `genre`: video topic/category. Required.
4. `style`: visual and narrative style. Required.
5. `visual_spec`: output aspect ratio and basic resolution. Required.
6. `characters`: whether fixed characters appear. Required.
7. `voice`: whether voiceover/dialogue is needed. Required.
8. `music`: whether background music is needed, and if needed whether it should be `song`, `instrumental`, or `underscore`. Required.
9. `final_output`: final desired output form. Required.

Use the option list from `references/first_layer_options.md`.

The exact user-facing Stage 00 question wording and option letters must follow:

- `references/stage00_question_blocks.md`

Treat `first_layer_options.md` as the canonical normalization source, and
`stage00_question_blocks.md` as the canonical user-visible prompt source.
Do not relabel, reorder, merge, or paraphrase option letters in the live intake dialogue.

## Required interaction style: one question at a time

The intake must feel like a guided wizard, not a long form.

Every intake prompt must be short and follow this shape:

```text
【Stage 00：视频项目立项确认】
进度：第 X / 9 项

问题：...
选项：...

请回复选项字母，或直接写自定义内容。
```

Rules:

- Ask exactly one numbered item per assistant turn.
- Do not show future questions unless the user asks for the full list.
- Do not repeat already answered questions unless the user wants to modify them.
- If the user chooses `自定义`, ask one short follow-up to collect the custom value.
- If the answer is unclear, ask the same question again with a short explanation.
- After a valid answer, move to the next question.
- After question 9 is answered, create the project folder and draft brief, then show a final summary and ask for confirmation through the official Stage 00 controller.

## Required opening behavior

If the user invokes this skill without an active intake state, respond only with Question 1.

Do not print the complete 9-item form.

Use the exact opening block from `references/stage00_question_blocks.md`:

```text
我将先进入【Stage 00：视频项目立项确认】。
在你确认基础信息之前，我不会开始写剧本、拆分镜、生成角色图、生成关键帧、调用 ComfyUI、调用 TTS 或合成视频。

进度：第 1 / 9 项

问题 1：你的故事想法/创意是什么？
请用一句话或一小段话描述，例如：
“一个外卖员深夜送餐，发现地址是一家十年前废弃的医院。”

请直接输入你的想法。
```

## Sequential question list

### Question 1: idea

Ask:

```text
进度：第 1 / 9 项

问题 1：你的故事想法/创意是什么？
请用一句话或一小段话描述。
```

No default is allowed. If empty or unusable, ask again.

### Question 2: target_duration

Ask using the exact `Question 2: target_duration` block from `references/stage00_question_blocks.md`.

If H or custom is chosen but no time is given, ask: `请告诉我具体时长，例如 45秒、2分钟、3分30秒。`

### Question 3: genre

Ask using the exact `Question 3: genre` block from `references/stage00_question_blocks.md`.

Note: `动漫短片` and `音乐MV` must stay separate. Do not merge them into one option.

### Question 4: style

Ask using the exact `Question 4: style` block from `references/stage00_question_blocks.md`.

Note: Do not use vague `动漫二次元`. If the user wants animation, ask them to choose or specify 日系动画、国漫动画、美式动画/卡通, or a custom animation style.

### Question 5: visual_spec

Ask using the exact `Question 5: visual_spec` block from `references/stage00_question_blocks.md`.

If the user provides only an aspect ratio, ask one short follow-up for resolution.
If the user provides only a resolution, ask one short follow-up for aspect ratio.
If F or 5/custom is chosen but no custom value is given, ask for the missing custom value.
Default recommendation, when user explicitly says “默认” or “你来推荐”: `9:16 竖屏 + 1080P`.

### Question 6: characters

Ask using the exact `Question 6: characters` block from `references/stage00_question_blocks.md`.

If A is chosen with a character description, preserve it in `user_answers.characters_note`. If A is chosen without a description, do not block intake; character details can be collected in a later stage.

### Question 7: voice

Ask using the exact `Question 7: voice` block from `references/stage00_question_blocks.md`.

### Question 8: music

Ask using the exact `Question 8: music` block from `references/stage00_question_blocks.md`.

### Question 9: final_output

Ask using the exact `Question 9: final_output` block from `references/stage00_question_blocks.md`.

## Stage 00-B: after all 9 answers are collected

After question 9 is answered, do not jump into script generation.

Perform these actions:

1. Normalize choices into canonical values according to `references/first_layer_options.md`.
2. Create an independent project folder under `video_projects/<project_id>/`.
3. Save optional state to `<project_dir>/00_intake/intake_state.json`.
4. Create `<project_dir>/00_intake/project_brief.draft.json` using the schema in `references/project_brief.schema.json`.
5. Run project structure validation:

```bash
python skills/video-project-intake/scripts/validate_project_structure.py <project_dir>
```

6. Run brief validation:

```bash
python skills/video-project-intake/scripts/validate_project_brief.py <project_dir>/00_intake/project_brief.draft.json
```

7. Show a concise confirmation summary:

```text
9 项信息已收集完成，项目文件夹已创建：<project_dir>

请确认项目 Brief：
1. 故事想法：...
2. 目标视频时长：...
3. 视频题材：...
4. 视频风格：...
5. 画面规格：...
6. 固定主角/人物：...
7. 配音：...
8. 背景音乐：...
   如果选择需要，必须明确是 `song` / `instrumental` / `underscore` 中哪一种。
9. 最终输出：...

请选择：
A. 确认，锁定需求并允许进入 Stage 01 剧本生成
B. 修改某一项
C. 重新填写
```

The option letters in the confirmation gate must also stay aligned with
`references/stage00_question_blocks.md`.

8. Only after explicit user confirmation, lock the brief.

In normal pipeline usage, this step must be triggered via the pipeline-owned wrapper:

```bash
python skills/video-production-pipeline/scripts/run_stage00_lock_and_continue.py <project_dir>
```

`lock_project_brief.py` remains an internal low-level script, not the official user-facing confirmation entry.

9. Update `<project_dir>/project_manifest.json` to:

```json
{
  "current_stage": "STAGE_00_BRIEF_LOCKED",
  "brief_locked": true,
  "allowed_next_stage": "STAGE_01_SCRIPT_GENERATION"
}
```

10. Report only:

```text
需求已锁定：<project_dir>/00_intake/project_brief.locked.json
项目文件夹：<project_dir>
下一阶段：自动进入 Stage 01 剧本生成。

如果当前不是 `$video-production-pipeline` 总控流程，而是用户手动调用了本 skill，则提示用户推荐回到 `$video-production-pipeline` 继续。
```

## Draft JSON requirements

The draft must contain:

- `schema_version`: current plugin schema version.
- `project_id`: project folder id.
- `project_dir`: relative project folder path.
- `stage`: `"STAGE_00_INTAKE"`
- `status`: `"draft"`
- `confirmed_by_user`: `false`
- `required_fields_complete`: true or false
- `missing_required_fields`: list
- `source`: explanation that the brief was created from user-supplied answers
- `user_answers`: original user answers if available
- `normalized`: normalized canonical values
- `allowed_next_stage`: `null` until confirmed

## Locked JSON requirements

The locked file must contain:

- `status`: `"locked"`
- `confirmed_by_user`: `true`
- `allowed_next_stage`: `"STAGE_01_SCRIPT_GENERATION"`
- `locked_at`: ISO timestamp

## Handling modifications

If the user chooses `B. 修改某一项` in the final confirmation:

1. Ask which item to modify, using item number 1-9.
2. Ask only that single question again.
3. Rewind `intake_state.json` to that question and clear downstream Stage 00 brief artifacts.
4. Re-collect from that point onward.
5. Re-run Stage 00-B draft generation and validation.
6. Show the confirmation summary again.

If the user chooses `C. 重新填写`, reset `intake_state.json` to Question 1, clear downstream Stage 00 draft/locked artifacts, and restart from Question 1 through the same controller.

## Important boundary

Even when the user confirms, this skill must not itself perform Stage 01. In normal usage, `$video-production-pipeline` and `run_stage00_lock_and_continue.py` will continue Stage 01 automatically. Do not force the user to manually call `$video-script-generation` unless this skill was invoked as a standalone recovery action.
