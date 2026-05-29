# HeartMuLa 使用规范

来源文件：

`workflows/comfyui/HeartMuLa使用说明.txt`

本规范只提炼该文本中已经明确写出的 HeartMuLa 提示词要求，供后续大模型在调用 HeartMuLa 工作流 API 前统一遵守。

## 适用场景

当需要把以下任一输入转换成 HeartMuLa 工作流可直接使用的标准提示词时，使用本规范：

- `故事情节`
- `歌曲风格`
- `歌曲风格描述`
- `歌词`

输出目标固定为：

- `Global Tags`
- `Lyrics`

不要把普通的一句 `music_prompt` 直接原样喂给 HeartMuLa。

## 角色要求

HeartMuLa 提示词构造器有两种工作模式，均来自原文：

1. 故事转歌曲模式
   - 输入：`故事情节`，可结合 `歌曲风格`
   - 任务：自动决定风格标签并用中文写歌词

2. 歌词整理模式
   - 输入：`歌词` 和 `歌曲风格描述`
   - 任务：把用户已有歌词整理成符合 HeartMuLa 要求的标准 Prompt

无论哪种模式，输出都必须服从同一套格式规则。

## 严格输出规则

后续凡是为 HeartMuLa 构造输入，都必须遵守：

1. 禁止闲聊
   - 不要输出“好的”“这是为您生成的歌曲”“根据故事”等任何前言或后语

2. 禁止复述输入故事
   - 不要把用户给的故事情节原样解释一遍

3. 只输出两个部分
   - `Global Tags`
   - `Lyrics`

4. 结构与风格必须合并
   - 格式固定为：

```text
[Structure: Style description]
```

5. 冒号后的风格描述必须用英文

## Global Tags 规则

`Global Tags` 位于 Prompt 最前端，使用逗号分隔。

原文要求：

- 必须包含高优先级标签：
  - `Genre`
  - `Gender`
  - `Mood`

- 可选包含：
  - `Instrument`
  - `Scene`
  - `Topic`

- 标签语言通常为英文，例如：
  - `Pop`
  - `Rock`
  - `Female`
  - `Sad`

- 最末尾必须加 `/`

标准写法：

```text
Global Tags: Pop, Mandopop, Female, Sad, Emotional, Piano, Ballad, Longing/
```

## Lyrics 规则

歌词必须使用中文创作或整理。

歌词部分必须带结构标签，并把细粒度风格描述直接并入每个结构标签后。

原文要求的完整结构至少包括：

- `[Intro]`
- `[Verse]`
- `[Pre-Chorus]`
- `[Chorus]`
- `[Bridge]`
- `[Outro]`

在实际输出时，不要只写裸结构标签，要写成：

```text
[Intro: Instrumental, atmospheric build]
[Verse 1: Calm vocal, narrative tone]
[Pre-Chorus: Increasing tension, emotional lift]
[Chorus: High energy, emotional peak]
[Bridge: Dramatic tension, reflective vocal]
[Outro: Fading out]
```

如果用户歌词里没有这些结构标签，需要根据歌词长短、韵律、情绪起伏自动补齐。

## 细粒度风格标签规则

每个结构标签后都应补一段英文风格说明，用来描述该段的演唱和编曲状态。

原文给出的参考维度：

- 动力 `Dynamics`
  - `Moderate intensity`
  - `Explosive`
  - `Subtle pulse`

- 人声 `Vocal`
  - `Introspective vocal`
  - `Triumphant vocal`
  - `Whispering`

- 氛围 `Vibe`
  - `Atmospheric build`
  - `Narrative progression`

推荐把这些维度组合到同一个结构标签里，例如：

```text
[Verse 1: Introspective vocal, Soft intensity, Narrative progression]
[Chorus: Sorrowful vocal expression, High energy sustain, Emotional climax]
```

## 两种标准任务模板

### 模板 A：故事情节转歌曲

适用输入：

- `故事情节`
- 可选 `歌曲风格`

处理要求：

1. 根据故事情节和歌曲风格自动决定英文 `Global Tags`
2. 用中文写歌词
3. 保证完整结构：
   - `Intro`
   - `Verse`
   - `Pre-Chorus`
   - `Chorus`
   - `Bridge`
   - `Outro`

### 模板 B：已有歌词转标准 HeartMuLa Prompt

适用输入：

- `歌曲风格描述`
- `歌词`

处理要求：

1. 从风格描述里提取英文 `Global Tags`
2. 检查歌词是否已有结构标签
3. 若没有，则自动补齐结构
4. 每个结构标签后补英文细粒度风格描述
5. 输出为 `Global Tags` + `Lyrics` 两部分

## 强制输出格式

### 最小合法格式

```text
Global Tags: [Genre], [Gender], [Mood], [Instrument], [Tempo].../
Lyrics:
[Intro: Instrumental, atmospheric build]
...
[Verse 1: Calm vocal, narrative tone]
...
[Pre-Chorus: Increasing tension, emotional lift]
...
[Chorus: High energy, emotional peak]
...
[Bridge: Dramatic tension, reflective vocal]
...
[Outro: Fading out]
...
```

### 原文示例风格

```text
Global Tags: Pop, Mandopop, Female, Sad, Emotional, Piano, Ballad, Longing/
Lyrics:
[Intro: Melancholic piano solo, Rain sound texture]
(无歌词部分)
[Verse: Introspective vocal, Soft intensity, Narrative progression]
窗外的雨下个不停 ...
[Chorus: Sorrowful vocal expression, High energy sustain, Emotional climax]
我怎么能忘记你 ...
```

## 后续调用 HeartMuLa 时的执行规则

后续大模型凡是要调用 HeartMuLa 工作流 API，先按下面顺序处理：

1. 判断当前输入属于“故事转歌曲”还是“歌词整理”
2. 先生成 `Global Tags`
3. 再生成 `Lyrics`
4. 检查是否只输出这两个部分
5. 检查 `Global Tags` 是否为英文逗号分隔，且以 `/` 结尾
6. 检查 `Lyrics` 是否使用中文歌词
7. 检查每个段落是否采用 `[Structure: English style description]`
8. 检查是否包含完整结构：
   - `Intro`
   - `Verse`
   - `Pre-Chorus`
   - `Chorus`
   - `Bridge`
   - `Outro`

## 禁止误用

以下写法都不符合 HeartMuLa 使用说明：

- 输出“好的，我来为你生成”
- 输出故事复述或任务解释
- 只输出一段普通自然语言 `music_prompt`
- 不输出 `Global Tags`
- 不输出 `Lyrics`
- 把结构标签和风格说明拆开写
- 冒号后的风格说明写中文
- `Global Tags` 不用英文逗号标签串
- `Global Tags` 末尾不加 `/`
- 缺少 `Pre-Chorus`、`Bridge` 或 `Outro`
