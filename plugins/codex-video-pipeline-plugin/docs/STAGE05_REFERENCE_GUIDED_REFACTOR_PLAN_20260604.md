# Stage 05 参考图回填 + Reference-Guided 主线改造计划

更新日期：`2026-06-04`

## 1. 文档目的

这份文档用于明确 `Stage05` 的改造主线、职责边界、执行原则与建议落地方式。

它回答四个问题：

1. 这次 Stage05 到底改什么
2. 哪些职责属于 `Stage03 / Stage04 / Stage05 / Stage06`
3. `codex-first` 在这条主线里是什么意思
4. Python 脚本在这条主线里应该做什么，不应该做什么

本文件记录的是已确认改造方向和建议落地方式，不代表仓库当前实现已经全部完成。

## 2. 当前问题

当前仓库里，`Stage03` 只产出：

- 人物设定
- 人物 prompt
- 参考图计划
- 参考图目标槽位

但 `Stage03` 不稳定地产出人物真图。

这会导致 `Stage05` 的角色一致性链路不闭环：

1. `Stage03` 有人物设定，但没有稳定主参考图
2. `Stage05` 可以生成单张图，但跨场景人物一致性缺少统一锚点
3. `Stage06` 后续拿到的输入图包，无法默认假设已经具备强一致性人物锚

这次改造的目标，就是把这条链路补完整。

## 3. 已确认的职责边界

### 3.1 Stage03

`Stage03` 继续负责：

- 人物设定
- 人物 prompt
- 参考图计划
- 参考图目标路径定义

`Stage03` 不负责直接生成主角真图。

### 3.2 Stage04

`Stage04` 继续负责：

- 每个 shot 的分镜 prompt
- shot 级动作、机位、构图、表演语义
- 面向 Stage05 的镜头级提示词输出

`Stage04` 不负责真正生图。

### 3.3 Stage05

`Stage05` 升级为两段式：

1. `Stage05-A`：根据 `Stage03` 的人物 prompt 先生成“主要人物参考图”
2. `Stage05-B`：基于“主要人物参考图 + 各分镜 prompt”生成跨场景高一致性分镜图

### 3.4 Stage06

`Stage06` 不再默认直接消费普通 prompt-only 关键帧结果，而是优先消费 `Stage05-B` 产出的高一致性分镜图。

## 4. codex-first 原则

这条主线必须按 `codex-first` 理解和实现。

### 4.1 什么叫 codex-first

`Codex` 是这条主线的上层编排者和真相控制器，负责：

- 判定当前项目是否进入 `Stage05-A` 还是 `Stage05-B`
- 选择应该走哪条工作流主线
- 读取并理解 `Stage03 / Stage04` 语义产物
- 决定什么时候需要回填 `Stage03`
- 决定什么时候允许 `Stage06` 消费 `Stage05-B` 结果
- 产出、修正和收敛真正送进工作流的 prompt

也就是说：

- 路由是 `Codex` 控
- 语义是 `Codex` 控
- 参考图闭环是 `Codex` 控
- 脚本只做确定性辅助，不取代 `Codex` 的语义判断

### 4.2 什么不叫 codex-first

以下做法都不符合这次主线：

- 让 Python 脚本自己“拍脑袋”决定走哪条 Zimage workflow
- 让脚本绕开 `Stage03 / Stage04` 语义，直接拼一套临时 prompt
- 让脚本在没有 `Codex` 明确路由语义的前提下，自动混用 prompt-only 和 reference-guided 两条主线
- 把“人物一致性判断”完全丢给脚本或工作流黑盒

## 5. Python 脚本辅助原则

Python 脚本不是主脑，而是辅助层。

### 5.1 Python 脚本应该负责

- scaffold manifest
- 读写 JSON / md / review 文件
- 做路径解析和目录落盘
- 把 `Codex` 已确认的字段注入工作流
- 运行 ComfyUI provider
- 同步请求记录和输出证据
- 跑 deterministic validation
- 生成 creator-facing review / recovery 文件

### 5.2 Python 脚本不应该负责

- 擅自改写项目语义目标
- 脱离路由规则选工作流
- 自己决定参考图是否足够好
- 自己决定是否可以跳过 `Stage05-A`
- 自己构造脱离 `Stage03 / Stage04` 上下文的新叙事

### 5.3 建议理解方式

可以把这条主线理解成：

- `Codex` 负责“想清楚”
- Python 脚本负责“稳定执行”

## 6. 新的 Stage05 主线流程

### 6.1 Stage05-A: 主角参考图生成

目标：

- 从 `Stage03` 的人物设定出发，生成一张可作为全项目人物锚点的“主要人物参考图”

输入：

- `03_characters/character_bible.json`
- `03_characters/reference_image_plan.json`
- `03_characters/stage03_llm_output.json`
- 其中的人物 prompt / 人物设定字段

工作流策略：

- 先从三套已锁定的本地 `Zimage` workflow 中选择最合适的一套：
  - `amazing-z-photo_SAFETENSORS.json`
  - `amazing-z-image-a_SAFETENSORS.json`
  - `amazing-z-comics_SAFETENSORS.json`
- 选择原则由项目风格路线决定，不允许脱离 Stage00/Stage05 路由体系随意选图

输出：

- 候选主角参考图
- 最终选定主参考图

回填动作：

- 将最终选定图回填到：
  - `03_characters/reference_images/CHAR_001_primary.png`
- 必要时同时保留候选图到：
  - `03_characters/reference_images/_candidates/`

结果语义：

- 从这一刻开始，`Stage03` 的“参考图计划”升级为“参考图已就绪”

### 6.2 Stage05-B: Qwen NextScene 一致性分镜图生成

目标：

- 用同一张主角参考图驱动多个不同场景分镜，最大化角色脸、发型、服装轮廓和整体身份的一致性

工作流：

- `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`

输入：

- `03_characters/reference_images/CHAR_001_primary.png`
- `04_keyframes/keyframe_prompts.json`
- 每个 shot 的分镜 prompt

执行语义：

- 主要人物参考图作为统一人物锚点输入
- 各分镜 prompt 作为场景与镜头差异输入
- 输出应是“同一人物在不同场景中的分镜图”，而不是彼此无关的单张图

输出：

- 高人物一致性的多场景分镜图集合
- 这些图是后续 `Stage06` 的正式输入资产

## 7. 新的阶段输入输出关系

### Stage03 -> Stage05-A

`Stage03` 提供：

- 人物设定
- 人物 prompt
- 参考图目标槽位

### Stage05-A -> Stage03

`Stage05-A` 回填：

- `03_characters/reference_images/CHAR_001_primary.png`

### Stage05-A -> Stage05-B

`Stage05-B` 消费：

- 已回填的主角参考图

### Stage04 -> Stage05-B

`Stage04` 提供：

- 分镜 prompt
- shot 级镜头语义

### Stage05-B -> Stage06

`Stage06` 消费：

- 人物一致性较强的多场景分镜图

## 8. 建议落地结构

### 8.1 Codex 负责的主线动作

建议 `Codex` 在 Stage05 主线中显式完成这些动作：

1. 读取 `Stage03` 与 `Stage04` 产物
2. 判定当前项目是否缺失主参考图
3. 缺失则进入 `Stage05-A`
4. 基于 route / style family 选定合适的 Zimage workflow
5. 审核候选主参考图是否满足人物锚点要求
6. 选定最终图并回填 `Stage03`
7. 再进入 `Stage05-B`
8. 用统一参考图 + Stage04 shot prompts 组装 Qwen NextScene 执行输入
9. 审核输出是否满足“单人一致性分镜图”要求
10. 允许 `Stage06` 继续消费

### 8.2 Python 辅助脚本负责的落地动作

建议 Python 脚本只负责确定性工作：

1. 生成 / 更新 manifest
2. 复制或回填参考图
3. 将参考图路径、prompt、seed、output_prefix 等注入 workflow
4. 执行 provider runner
5. 同步 `comfyui_image_requests.json`
6. 同步 `keyframe_image_manifest.json`
7. 生成 review workbench / review markdown
8. 跑校验器

## 9. 当前可复用的脚本辅助入口

以下是和这次主线直接相关、建议复用或扩展的现有 Python 辅助脚本：

### 9.1 Stage05 manifest / job scaffold

- `skills/video-keyframe-images/scripts/new_keyframe_image_jobs.py`

用途：

- 生成 Stage05 image jobs
- 记录 route resolution
- 记录 reference-guided readiness

### 9.2 ComfyUI txt2img 执行入口

- `scripts/providers/run_comfyui_txt2img.py`

用途：

- 将 job 映射成具体 workflow 执行请求
- 注入 prompt / reference image / width / height / workflow widgets
- 同步请求记录和结果证据

### 9.3 Stage05-A 回填辅助

- `skills/video-keyframe-images/scripts/run_stage05_reference_bootstrap.py`

用途：

- 根据 `Stage03` 人物设定直接生成主角色参考图
- 将最终图回填到 `Stage03` 参考图槽位
- 回填后刷新 `Stage03 / Stage04 / Stage05-B` 状态

说明：

- 旧的“从已有 keyframe 反向拷回 Stage03”的桥接脚本已经移除
- 新主线只保留 `Stage05-A -> 回填 Stage03 -> Stage05-B` 这条正式闭环

### 9.4 Review / approval 辅助

- `skills/video-keyframe-images/scripts/serve_stage05_review_workbench.py`
- `skills/video-keyframe-images/scripts/approve_stage05_review_queue.py`

用途：

- 给 creator-facing 审图流程提供 workbench 与 approval 更新能力

### 9.5 Manifest / evidence sync

- `skills/video-keyframe-images/scripts/sync_keyframe_image_manifest.py`
- `skills/video-keyframe-images/scripts/validate_keyframe_image_manifest.py`

用途：

- 同步产物存在性、状态和最终验证结果

## 10. 建议新增或重构的 Stage05 代码块

为了让这条主线更干净，建议后续实现时按下面几个逻辑块拆：

### 10.1 Stage05-A orchestration

建议新增一个清晰的主角参考图生成入口，例如：

- `run_stage05_reference_bootstrap.py`
- 或在现有 `new_keyframe_image_jobs.py` / provider layer 中显式分出 `stage05_reference_bootstrap` 子流程

它负责：

- 读取 `Stage03`
- 选择 Zimage workflow
- 生成候选图
- 记录候选图与最终图
- 回填 `CHAR_001_primary.png`

### 10.2 Stage05-B reference-guided orchestration

当前主线应显式区分：

- `stage05_mode = reference_bootstrap`
- `stage05_mode = reference_guided_storyboard`

其中：

- `reference_bootstrap` 只用于 `Stage05-A`
- `reference_guided_storyboard` 才是 `Stage05-B` 正式交付给 `Stage06` 的模式

### 10.3 Stage03 回填状态同步

回填主参考图后，建议同步更新：

- `03_characters/character_bible.json`
- `03_characters/reference_image_status`
- `03_characters/self_check.reference_images_ready`
- creator-facing recovery / review 文件

### 10.4 Stage06 消费契约切换

建议明确 Stage06 优先消费：

- `Stage05-B` 的 reference-guided 一致性分镜图

而不是默认消费：

- prompt-only 的普通 keyframe

## 11. 这次改造带来的主线变化

这次改造后，`Stage05` 不再只有“按 prompt 生关键帧”这一层含义，而是明确拆成：

1. 先补人物锚图
2. 再做参考图驱动的分镜图生成

这意味着：

- `Stage03` 不需要直接负责生真图
- `Stage05` 成为“人物一致性闭环”的核心阶段
- `Stage06` 的输入质量将依赖 `Stage05-B` 的一致性结果，而不是单纯依赖 prompt-only 单帧图片

## 12. 当前已确认内容

截至 `2026-06-04`，以下内容已确认：

1. `Stage05` 拆分为 `Stage05-A / Stage05-B`
2. `Stage05-A` 的目标是先生成主角参考图
3. `Stage05-A` 的工作流来源固定在三套本地 `Zimage` workflow 中选择
4. `Stage05-A` 生成结果要回填到 `Stage03`
5. `Stage05-B` 固定走 `QwenEdit+NextScene` reference-guided 主线
6. `Stage05-B` 的核心输入是：
   - `03_characters/reference_images/CHAR_001_primary.png`
   - `04_keyframes/keyframe_prompts.json`
7. `Stage06` 后续优先消费 `Stage05-B` 的输出
8. 整条主线按 `codex-first` 实现
9. Python 脚本只做确定性辅助，不取代 `Codex` 的路由和语义判断

## 13. 当前仍待细化的实现细节

以下内容后续再单独细化：

1. 三套 `Zimage` workflow 与 Stage00/Stage05 route 的精确映射表
2. `Stage05-A` 生成主角参考图时的候选数、筛选规则、审图规则
3. 主角参考图回填后的 manifest 字段更新方式
4. `QwenEdit+NextScene` 工作流的全部参数绑定细节
5. `Stage05-B` 产物目录结构与命名规范
6. `Stage06` 应消费 `Stage05-B` 的哪一层产物
7. 老的 prompt-only Stage05 产物在新主线中的保留策略
8. `Stage05-A` 是否单独落成新脚本入口，还是挂在现有 Stage05 orchestration 中

## 14. 当前结论

自 `2026-06-04` 起，Stage05 改造主线按以下口径讨论与实现：

1. 先选合适的 `Zimage` workflow，根据 `Stage03` 人物 prompt 生成主要人物参考图
2. 将该参考图回填到 `Stage03`
3. 再调用 `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`
4. 将“主要人物参考图 + 各分镜 prompt”作为参数传入
5. 生成高人物一致性的多场景分镜图
6. 这些分镜图作为 `Stage06` 的后续输入
7. 整个主线由 `Codex` 负责编排和语义收敛，Python 脚本负责稳定执行和落盘辅助
