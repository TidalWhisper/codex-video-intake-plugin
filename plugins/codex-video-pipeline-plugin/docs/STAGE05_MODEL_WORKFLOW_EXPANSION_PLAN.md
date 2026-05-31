# Stage 05 模型与工作流扩容计划

更新日期：`2026-05-30`

## 1. 背景

当前 Stage 05 本地 ComfyUI 生图只保留了 4 条最小风格路线：

- `realistic`
- `anime`
- `guofeng`
- `stylized`

这套最小架构已经不足以覆盖 Stage 00 立项阶段提供的风格入口，也不适合作为长期生产设计。

当前主要问题：

1. Stage 00 风格选项明显多于 Stage 05 可用路线。
2. `guofeng`、`stylized` 等路线不能再默认依赖同一底模加少量 LoRA 来“伪装成独立路线”。
3. `anime` 也不应长期停留在单一路线的简化方案上。
4. 当前路由设计没有把“风格入口”和“模型/工作流能力边界”分层。

## 2. 本次计划的核心共识

### 2.1 Provider 顺序

Stage 05 provider 顺序固定为：

1. `OpenAI GPT Image 2`
2. `ComfyUI`
3. `manual`

这条顺序不再受 style family 影响。

### 2.2 ComfyUI 路由设计原则

ComfyUI 不再只保留 4 个风格名作为最终设计，而是升级为：

`Stage 00 用户风格 -> Stage 05 路由族 -> 模型 + workflow`

### 2.3 模型选择原则

必须坚持：

1. 先选模型，再做 workflow。
2. 风格路线必须有真实模型身份，不接受仅靠 prompt 改写的伪路线。
3. `guofeng`、`stylized`、`game_cg` 这类路线默认要求风格专用模型、专用 LoRA、或明显不同的 workflow 结构。
4. 每条路线都必须有本地 smoke evidence 后才能进入生产候选。
5. 能找到成熟 community workflow 的路线，优先导入 community 版本；仓库自写 workflow 只作为过渡桥接。

## 3. Stage 00 到 Stage 05 的建议映射

### 3.1 新的 Stage 05 路由族

建议先扩成 8 条路线：

1. `realistic_cinematic`
2. `shortdrama_realistic`
3. `anime_jp`
4. `anime_cn_newguofeng`
5. `western_cartoon`
6. `guofeng_ink`
7. `stylized_concept`
8. `game_cg`

### 3.2 Stage 00 风格映射建议

| Stage 00 风格 | 建议映射到 Stage 05 路由 |
|---|---|
| 写实电影感 | `realistic_cinematic` |
| 短剧爽感 | `shortdrama_realistic` |
| 日系动画风（日本动漫感） | `anime_jp` |
| 国漫动画风（中国动画/新国风） | `anime_cn_newguofeng` |
| 美式动画/卡通风（欧美动画感） | `western_cartoon` |
| 国风水墨/古风 | `guofeng_ink` |
| 赛博朋克 | `stylized_concept` |
| 暗黑惊悚 | `stylized_concept` |
| 温暖治愈 | `realistic_cinematic` 或 `anime_jp` |
| 纪录片质感 | `shortdrama_realistic` |
| 广告高级感 | `realistic_cinematic` |
| 游戏CG感 | `game_cg` |
| 低饱和现实主义 | `shortdrama_realistic` |
| 高饱和潮流感 | `stylized_concept` |

说明：

- `温暖治愈` 本身不是模型路线，而是内容和气质方向，后续应依赖二级判定决定走写实还是动画。
- `赛博朋克`、`暗黑惊悚` 更适合放到 `stylized_concept` 这类强风格路线，而不是直接映射为单一模型名。

## 4. 候选模型与 workflow 池

以下是当前建议的 Stage 05 候选池。这里的“候选”不等于“已批准生产默认”。

补充约束：

- `preferred candidate` 指社区或模型仓里最值得迁移的版本
- `current repo route` 指当前仓库已经落地、但未必是终版的桥接实现
- 如果只有 `official` 没有 `community`，必须显式标注该路线仍存在社区空缺

### 4.1 realistic_cinematic

主候选：

- `Qwen-Image-2512`
- `Z-Image`
- `HiDream-I1`

适配说明：

- `Qwen-Image-2512` 适合通用高质量写实与商业图路线
- `Z-Image` 可作为通用高质量替代路线
- `HiDream-I1` 适合作为更偏商业质感、概念宣传、广告向写实候选

### 4.2 shortdrama_realistic

主候选：

- `Qwen-Image-2512`
- `Z-Image`
- 写实增强 LoRA 路线

适配说明：

- 目标不是“纯摄影棚写实”，而是面向短剧人物、剧情、镜头可读性的写实输出
- 更强调角色脸部稳定、光影戏剧性、镜头感，而不是单纯高精细

### 4.3 anime_jp

主候选：

- `Anima`
- `Z-Anime`
- `Neta-Lumina`
- `Dasiwa`（专项验证分支）

适配说明：

- `anime_jp` 必须优先使用 anime-native 或 anime-first 模型
- 不再把通用底模 + prompt-only 方案当成默认主线

### 4.4 anime_cn_newguofeng

主候选：

- `Neta-Lumina`
- `Z-Anime`
- `Dasiwa`（专项验证分支）

适配说明：

- 这条路线需要兼顾动画感与东方视觉语言
- 不能简单等同于 `anime_jp` 或 `guofeng_ink`

### 4.5 western_cartoon

主候选：

- 待从开源社区继续补充专用 cartoon 模型
- 若短期没有足够成熟候选，可先列为 `provisional`

适配说明：

- 这类路线不建议直接复用 `anime_jp`
- 需要确认线条、脸型、色彩和夸张比例是否符合欧美卡通审美

### 4.6 guofeng_ink

主候选：

- `Neta-Lumina`
- `Qwen-Image-Gufeng-LoRA`
- 其他明确国风/水墨方向的开源模型与 workflow

适配说明：

- `guofeng` 是重点禁止 prompt-only 的路线
- 必须要求模型或 LoRA 明确压制现代摄影倾向
- `Qwen-Image-Gufeng-LoRA` 的模型方向成立，但外部 workflow 源本身仍要做真实性核验，不能因为文件名正确就直接导入

### 4.7 stylized_concept

主候选：

- `HiDream-I1`
- `Z-Image`
- 其他概念艺术、插画、强造型路线的社区 workflow

适配说明：

- 这条路线要面向概念图、海报感、设定图、气氛图
- 不能再默认等价于“Qwen 通用底模 + illustration LoRA”

### 4.8 game_cg

主候选：

- 待补充更明确的游戏 CG / 宣传图向模型与 workflow
- 可以从写实高质量模型和概念艺术模型两侧分别筛选

适配说明：

- `game_cg` 不应混同于普通 realistic
- 需要更强的角色宣传图质感、光效、材质感和构图控制

## 5. Dasiwa 专项验证分支

`Dasiwa` 需要单独作为专项验证分支处理，不直接预设为 Stage 05 默认路线。

### 5.1 当前判断

当前公开证据中，`Dasiwa` 更清晰地出现在：

- `Wan 2.2`
- `I2V / 视频`
- 社区 workflow 套件
- GitHub Dockerized workflow 包

它是否适合直接成为 Stage 05 静态关键帧默认 `txt2img` 路线，当前证据仍不充分。

### 5.2 处理策略

`Dasiwa` 纳入以下候选池：

- `anime_jp`
- `anime_cn_newguofeng`

但必须先完成专项验证：

1. 确认是否存在可靠的静态单帧 T2I 工作流
2. 确认是否更偏向 I2V / 视频首尾帧体系
3. 确认是否适合作为 Stage 05 主线，而不是 Stage 06 候选
4. 留下本地 smoke sample 和 request evidence

### 5.3 可能结论

专项验证后，只允许进入三种结论之一：

- `approved_for_stage05`
- `provisional_for_stage05`
- `better_fit_for_stage06`

## 6. 需要新增的配置与登记物

建议新增一份新的路由登记表，例如：

```text
config/stage05_route_registry.example.yaml
```

建议字段：

- `route_key`
- `supported_stage00_styles`
- `status`
- `workflow_name`
- `workflow_file`
- `model_stack`
- `candidate_models`
- `suitability_class`
- `smoke_sample`
- `review_note`

当前已有的：

- `config/stage05_style_profiles.example.yaml`

后续应升级为“真实路由登记表”，而不是只保留 4 个风格 profile。

## 7. 分阶段执行计划

### Phase 1: 路由设计重构

目标：

- 把 Stage 00 风格入口映射到新的 Stage 05 路由族
- 先完成设计，不急着改默认 workflow

交付物：

- 新的 route registry 设计
- Stage 00 -> Stage 05 映射表

### Phase 2: 候选池建档

目标：

- 为每条 route 建立 2-3 个候选模型与候选 workflow
- 记录来源、许可证、ComfyUI 依赖、推荐用途

交付物：

- 候选矩阵
- 来源清单
- 许可证风险备注

### Phase 3: 本地依赖审计

目标：

- 审计每个 workflow 的节点依赖、模型依赖、显存需求

交付物：

- workflow audit 报告
- dependency manifest
- repair suggestions

### Phase 4: 最小可跑 workflow 固化

目标：

- 每个 route 固化 1 条最小可跑 workflow
- 明确其模型栈

交付物：

- `workflows/comfyui/` 下新的 route workflow
- 配套 mapping

### Phase 5: Smoke 验证

目标：

- 使用统一 shot 集对每条 route 进行本地 smoke

每条 route 至少留下：

- `05_images/keyframes/*.png`
- `05_images/comfyui_image_requests.json`
- workflow 名
- 模型名
- review note

### Phase 6: 回写插件逻辑

目标：

- 只有 smoke 完成后，才修改 Stage 05 主逻辑

涉及文件：

- `scripts/pipeline_core/requirement_compiler.py`
- `skills/video-keyframe-images/scripts/new_keyframe_image_jobs.py`
- `scripts/providers/run_comfyui_txt2img.py`
- `config/workflow_node_mapping.example.yaml`
- `config/stage05_style_profiles.example.yaml`
- Stage 05 相关测试与文档

## 8. 第一批优先落地范围

建议第一批优先做 5 条：

1. `realistic_cinematic`
2. `anime_jp`
3. `anime_cn_newguofeng`
4. `guofeng_ink`
5. `stylized_concept`

理由：

- 这 5 条对当前 Stage 00 风格覆盖提升最大
- 当前公开候选更容易找到相对明确的模型与 workflow
- 能最快把“只有四种最小风格”的问题打穿

第二批再补：

1. `western_cartoon`
2. `game_cg`
3. `Dasiwa` 是否进入 Stage 05 主线的最终结论

## 9. 通过标准

这项工作不以“workflow 文件数量增加”为完成标准，而以以下标准为准：

1. Stage 00 风格映射明确
2. 每条 route 的模型身份明确
3. 每条 route 至少有一条真实不同的 workflow
4. 每条 route 有 smoke sample
5. `guofeng`、`stylized`、`game_cg` 不再依赖 prompt-only 假装独立
6. Dasiwa 是否适合 Stage 05 有明确结论

## 10. 当前不应做的事

当前阶段禁止：

1. 直接把更多风格名硬塞进现有 4 路结构里
2. 还没做 smoke 就宣布某路线生产可用
3. 用同一底模复制多个 workflow 文件，只改 prompt 文本
4. 把 `Dasiwa` 在没有静态 T2I 证据前直接设成 Stage 05 默认路线
