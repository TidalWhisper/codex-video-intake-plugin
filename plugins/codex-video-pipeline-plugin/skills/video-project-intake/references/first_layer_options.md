# First-layer required intake options

This file defines canonical option mappings for Stage 00 intake.

## 1. idea

Free text. No default. Must be supplied by the user.

Canonical key: `idea`

## 2. target_duration

| Choice | Canonical value | Seconds |
|---|---|---:|
| A | 15秒 | 15 |
| B | 30秒 | 30 |
| C | 60秒 | 60 |
| D | 90秒 | 90 |
| E | 120秒 | 120 |
| F | 180秒 | 180 |
| G | 300秒 | 300 |
| H | 自定义 | custom |

Canonical keys:

- `target_duration_label`
- `target_duration_sec`

If user chooses custom, extract seconds if possible. If not possible, ask a follow-up.

## 3. genre

`动漫短片` and `音乐MV` must stay separate. Do not merge them.

| Choice | Canonical value |
|---|---|
| A | 剧情短片 |
| B | 悬疑 |
| C | 恐怖惊悚 |
| D | 科幻 |
| E | 爱情 |
| F | 搞笑 |
| G | 治愈 |
| H | 励志 |
| I | 广告宣传 |
| J | 产品展示 |
| K | 纪录片 |
| L | 教育科普 |
| M | 国风/古风 |
| N | 奇幻 |
| O | 动漫短片 |
| P | 音乐MV |
| Q | 自定义 |

Canonical key: `genre`

## 4. style

Animation style must be explicit. Do not use the vague option `动漫二次元`.

| Choice | Canonical value |
|---|---|
| A | 写实电影感 |
| B | 短剧爽感 |
| C | 日系动画风（日本动漫感） |
| D | 国漫动画风（中国动画/新国风） |
| E | 美式动画/卡通风（欧美动画感） |
| F | 国风水墨/古风 |
| G | 赛博朋克 |
| H | 暗黑惊悚 |
| I | 温暖治愈 |
| J | 纪录片质感 |
| K | 广告高级感 |
| L | 游戏CG感 |
| M | 低饱和现实主义 |
| N | 高饱和潮流感 |
| O | 自定义 |

Canonical key: `style`

## 5. visual_spec

Question 5 collects both aspect ratio and basic output resolution. Keep them in one item so the Stage 00 flow remains 9 items.

### 5.1 aspect_ratio

| Choice | Canonical value | Width:Height |
|---|---|---|
| A | 9:16 竖屏 | 9:16 |
| B | 16:9 横屏 | 16:9 |
| C | 1:1 方屏 | 1:1 |
| D | 4:5 竖图信息流 | 4:5 |
| E | 21:9 宽银幕 | 21:9 |
| F | 自定义比例 | custom |

Canonical keys:

- `aspect_ratio_label`
- `aspect_ratio`

### 5.2 resolution

| Choice | Canonical value | Notes |
|---|---|---|
| 1 | 720P | Low-cost preview / weak hardware |
| 2 | 1080P | Recommended default |
| 3 | 2K | Higher quality, heavier generation |
| 4 | 4K | Final upscaling / very heavy generation |
| 5 | 自定义画质 | custom |

Canonical keys:

- `resolution_label`
- `resolution`

Recommended default, when user explicitly says “默认” or “你来推荐”:

- `aspect_ratio`: 9:16
- `aspect_ratio_label`: 9:16 竖屏
- `resolution`: 1080P
- `resolution_label`: 1080P

## 6. characters

| Choice | Canonical value |
|---|---|
| A | 有固定主角/人物 |
| B | 没有固定人物，以场景/物体/氛围为主 |
| C | 由模型根据故事自动判断 |
| D | 不确定 |

Canonical keys:

- `characters_mode`
- `characters_required`

Mapping:

- A => `characters_required: true`
- B => `characters_required: false`
- C => `characters_required: "auto"`
- D => `characters_required: "unknown"`

If A, ask for optional character description if not already provided, but do not block the intake lock in this initial version.

## 7. voice

| Choice | Canonical value |
|---|---|
| A | 不需要配音 |
| B | 只需要旁白 |
| C | 只需要角色对白 |
| D | 旁白 + 角色对白都需要 |
| E | 不确定，先由模型建议 |

Canonical keys:

- `voice_mode`
- `voice_required`

Mapping:

- A => `voice_required: false`
- B/C/D => `voice_required: true`
- E => `voice_required: "recommend"`

## 8. music

| Choice | Canonical value |
|---|---|
| A | 不需要 |
| B | 需要 |
| C | 由模型根据题材自动建议 |

Canonical keys:

- `music_mode`
- `music_required`

Mapping:

- A => `music_required: false`
- B => `music_required: true`
- C => `music_required: "recommend"`

## 9. final_output

| Choice | Canonical value |
|---|---|
| A | 只要剧本 |
| B | 剧本 + 分镜脚本 |
| C | 剧本 + 分镜 + 关键帧提示词 |
| D | 生成关键帧图片素材包 |
| E | 生成视频片段素材包 |
| F | 合成粗剪成片 |
| G | 输出完整素材工程包，方便人工剪辑 |

Canonical key: `final_output`

## Default policy

In this initial version:

- No default is allowed for `idea`.
- Defaults may be suggested only after user says “默认” or “你来推荐”.
- Recommended defaults:
  - `target_duration_sec`: 60
  - `genre`: 剧情短片
  - `style`: 写实电影感
  - `aspect_ratio`: 9:16
  - `resolution`: 1080P
  - `characters_required`: auto
  - `voice_required`: recommend
  - `music_required`: recommend
  - `final_output`: 剧本 + 分镜脚本
