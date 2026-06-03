# Stage 00 Canonical Question Blocks

This file is the single source of truth for the exact user-facing Stage 00 question wording and option letters.

Absolute rules:

- When asking Stage 00 questions, reproduce these blocks exactly.
- Do not relabel, reorder, merge, or paraphrase option letters.
- `references/first_layer_options.md` defines the canonical normalization mapping behind these blocks.
- If any question block here conflicts with `references/first_layer_options.md`, fix this file to match the canonical mapping and then update any dependent skill text.

## Opening

```text
我将先进入【Stage 00：视频项目立项确认】。
在你确认基础信息之前，我不会开始写剧本、拆分镜、生成角色图、生成关键帧、调用 ComfyUI、调用 TTS 或合成视频。

进度：第 1 / 9 项

问题 1：你的故事想法/创意是什么？
请用一句话或一小段话描述，例如：
“一个外卖员深夜送餐，发现地址是一家十年前废弃的医院。”

请直接输入你的想法。
```

## Question 2: target_duration

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

## Question 3: genre

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

## Question 4: style

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

## Question 5: visual_spec

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

## Question 6: characters

```text
进度：第 6 / 9 项

问题 6：是否有固定主角/人物出镜？
A. 有固定主角/人物
B. 没有固定人物，以场景/物体/氛围为主
C. 由模型根据故事自动判断
D. 不确定

请回复 A-D。也可以在选择后补充人物描述。
```

## Question 7: voice

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

## Question 8: music

```text
进度：第 8 / 9 项

问题 8：是否需要背景音乐？
A. 不需要
B1. 需要，歌曲（song）
B2. 需要，纯音乐（instrumental）
B3. 需要，背景配乐（underscore）
C. 由模型根据题材自动建议

请回复 A / B1 / B2 / B3 / C。
```

## Question 9: final_output

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

## Final Confirmation

```text
请选择：
A. 确认，锁定需求并允许进入 Stage 01 剧本生成
B. 修改某一项
C. 重新填写
```
