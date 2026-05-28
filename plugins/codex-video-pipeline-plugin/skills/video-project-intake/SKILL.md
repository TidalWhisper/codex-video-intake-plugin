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

After the brief is locked, Stage 01 is allowed. In the normal user flow, `$video-production-pipeline` must automatically continue to Stage 01 in the same conversation. This individual skill is now a recovery/debug entry point and must not tell the user to manually invoke the next stage during normal pipeline mode.

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
8. `music`: whether background music is needed. Required.
9. `final_output`: final desired output form. Required.

Use the option list from `references/first_layer_options.md`.

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
- After question 9 is answered, create the project folder and draft brief, then show a final summary and ask for confirmation.

## Required opening behavior

If the user invokes this skill without an active intake state, respond only with Question 1.

Do not print the complete 9-item form.

Use this exact style:

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

Ask:

```text
进度：第 2 / 9 项

问题 2：目标视频时长是多少？
A. 15秒
B. 30秒
C. 60秒
D. 90秒
E. 120秒
F. 180秒
G. 300秒
H. 自定义

请回复 A-H，或直接写具体时长。
```

If H or custom is chosen but no time is given, ask: `请告诉我具体时长，例如 45秒、2分钟、3分30秒。`

### Question 3: genre

Ask:

```text
进度：第 3 / 9 项

问题 3：视频题材是什么？
A. 剧情短片
B. 悬疑
C. 恐怖惊悚
D. 科幻
E. 爱情
F. 搞笑
G. 治愈
H. 励志
I. 广告宣传
J. 产品展示
K. 纪录片
L. 教育科普
M. 国风/古风
N. 奇幻
O. 动漫短片
P. 音乐MV
Q. 自定义

请回复 A-Q，或直接写自定义题材。
```

Note: `动漫短片` and `音乐MV` must stay separate. Do not merge them into one option.

### Question 4: style

Ask:

```text
进度：第 4 / 9 项

问题 4：视频风格是什么？
A. 写实电影感
B. 短剧爽感
C. 日系动画风（日本动漫感）
D. 国漫动画风（中国动画/新国风）
E. 美式动画/卡通风（欧美动画感）
F. 国风水墨/古风
G. 赛博朋克
H. 暗黑惊悚
I. 温暖治愈
J. 纪录片质感
K. 广告高级感
L. 游戏CG感
M. 低饱和现实主义
N. 高饱和潮流感
O. 自定义

请回复 A-O，或直接写自定义风格。
```

Note: Do not use vague `动漫二次元`. If the user wants animation, ask them to choose or specify 日系动画、国漫动画、美式动画/卡通, or a custom animation style.

### Question 5: visual_spec

Ask:

```text
进度：第 5 / 9 项

问题 5：画面规格是什么？
请同时选择【画面比例】和【输出画质】。

画面比例：
A. 9:16 竖屏
B. 16:9 横屏
C. 1:1 方屏
D. 4:5 竖图信息流
E. 21:9 宽银幕
F. 自定义比例

输出画质：
1. 720P
2. 1080P
3. 2K
4. 4K
5. 自定义画质

请按“比例字母 + 画质数字”回复，例如：A2 表示 9:16 竖屏 + 1080P。
也可以直接写：9:16 + 1080P。
```

If the user provides only an aspect ratio, ask one short follow-up for resolution.
If the user provides only a resolution, ask one short follow-up for aspect ratio.
If F or 5/custom is chosen but no custom value is given, ask for the missing custom value.
Default recommendation, when user explicitly says “默认” or “你来推荐”: `9:16 竖屏 + 1080P`.

### Question 6: characters

Ask:

```text
进度：第 6 / 9 项

问题 6：是否有固定主角/人物出镜？
A. 有固定主角/人物
B. 没有固定人物，以场景/物体/氛围为主
C. 由模型根据故事自动判断
D. 不确定

请回复 A-D。也可以在选择后补充人物描述。
```

If A is chosen with a character description, preserve it in `user_answers.characters_note`. If A is chosen without a description, do not block intake; character details can be collected in a later stage.

### Question 7: voice

Ask:

```text
进度：第 7 / 9 项

问题 7：是否需要配音？
A. 不需要配音
B. 只需要旁白
C. 只需要角色对白
D. 旁白 + 角色对白都需要
E. 不确定，先由模型建议

请回复 A-E。
```

### Question 8: music

Ask:

```text
进度：第 8 / 9 项

问题 8：是否需要背景音乐？
A. 不需要
B. 需要
C. 由模型根据题材自动建议

请回复 A-C。
```

### Question 9: final_output

Ask:

```text
进度：第 9 / 9 项

问题 9：最终希望输出什么？
A. 只要剧本
B. 剧本 + 分镜脚本
C. 剧本 + 分镜 + 关键帧提示词
D. 生成关键帧图片素材包
E. 生成视频片段素材包
F. 合成粗剪成片
G. 输出完整素材工程包，方便人工剪辑

请回复 A-G。
```

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
9. 最终输出：...

请选择：
A. 确认，锁定需求并允许进入 Stage 01 剧本生成
B. 修改某一项
C. 重新填写
```

8. Only after explicit user confirmation, lock the brief:

```bash
python skills/video-project-intake/scripts/lock_project_brief.py <project_dir>/00_intake/project_brief.draft.json <project_dir>/00_intake/project_brief.locked.json
```

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
3. Update the draft brief.
4. Re-run validation.
5. Show the confirmation summary again.

If the user chooses `C. 重新填写`, restart from Question 1 and create a new project folder after all 9 answers are collected again.

## Important boundary

Even when the user confirms, this skill must not itself perform Stage 01. In normal usage, `$video-production-pipeline` will continue Stage 01 automatically. Do not force the user to manually call `$video-script-generation` unless this skill was invoked as a standalone recovery action.
