# Stage 05 执行清单（候选下载 / Workflow 起点 / 审计顺序）

更新日期：`2026-05-29`

## 1. 目的

这份清单把前面的候选矩阵进一步压实成可执行 backlog。

每条 route 都明确：

1. 第一优先模型
2. 第二优先模型
3. 第一优先 workflow 起点
4. 预期依赖
5. 审计顺序
6. smoke 顺序

## 2. 总体执行原则

先做：

1. 下载候选模型或确认本机是否已有
2. 获取 workflow 原始文件
3. 跑 workflow 依赖审计
4. 再跑 smoke

不要先改插件主逻辑。

## 3. Route-by-route Backlog

### 3.1 realistic_cinematic

第一优先模型：

- `Qwen/Qwen-Image-2512`

第二优先模型：

- `Tongyi-MAI/Z-Image`

第三优先模型：

- `HiDream-ai/HiDream-I1-Full` 或 `HiDream-ai/HiDream-I1-Dev`

第一优先 workflow 起点：

- Qwen 官方模板：
  - [image_qwen_Image_2512.json](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_Image_2512.json)

第二优先 workflow 起点：

- 现有仓库 `txt2img_keyframe_realistic.workflow_api.json`

第三优先 workflow 起点：

- [Comfy-Org/HiDream-I1_ComfyUI](https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI)

预期依赖：

- Qwen / Z-Image / HiDream 对应 diffusion model
- text encoder
- vae
- 可能的 sampler / loader 自定义节点

审计顺序：

1. Qwen workflow
2. Z-Image realistic workflow
3. HiDream workflow

smoke 优先级：

1. 人像近景
2. 室内剧情镜头
3. 广告构图镜头

### 3.2 anime_jp

第一优先模型：

- `circlestone-labs/Anima`

第二优先模型：

- `xuedi7/Z-Anime`

第三优先模型：

- `neta-art/Neta-Lumina`

专项旁路：

- `Dasiwa`

第一优先 workflow 起点：

- `Anima` 自带 ComfyUI workflow：
  - [circlestone-labs/Anima](https://huggingface.co/circlestone-labs/Anima)

第二优先 workflow 起点：

- `Z-Anime` 官方 workflow：
  - [workflows/Z-Anime-Workflow-v1.json](https://huggingface.co/SeeSee21/Z-Anime/blob/main/workflows/Z-Anime-Workflow-v1.json)

第三优先 workflow 起点：

- `Neta-Lumina` 官方 workflow：
  - [lumina_workflow.json](https://huggingface.co/neta-art/Neta-Lumina/blob/main/lumina_workflow.json)

预期依赖：

- anime 专用 checkpoint / base model
- text encoder
- vae
- 可能的 model switch / GGUF loader / LoRA loader

审计顺序：

1. Z-Anime
2. Anima
3. Neta-Lumina
4. Dasiwa（若找到静态 T2I workflow）

smoke 优先级：

1. 单人角色 key visual
2. 双人互动
3. 强表情近景

### 3.3 anime_cn_newguofeng

第一优先模型：

- `neta-art/Neta-Lumina`

第二优先模型：

- `xuedi7/Z-Anime`

专项旁路：

- `Dasiwa`

第一优先 workflow 起点：

- [lumina_workflow.json](https://huggingface.co/neta-art/Neta-Lumina/blob/main/lumina_workflow.json)

第二优先 workflow 起点：

- `Z-Anime` workflow 作为对照改造母版

预期依赖：

- Lumina 体系模型文件
- Gemma 文本编码器
- 可能的特定 loader 节点

审计顺序：

1. Neta-Lumina
2. Z-Anime 变体路线
3. Dasiwa

smoke 优先级：

1. 国漫角色设定图
2. 东方建筑场景
3. 新国风剧情镜头

### 3.4 guofeng_ink

第一优先模型：

- `valiantcat/Qwen-Image-Gufeng-LoRA`

第二优先模型：

- `neta-art/Neta-Lumina`

第一优先 workflow 起点：

- [Workflow-Qwen-Image-LORA.json](https://huggingface.co/valiantcat/Qwen-Image-Gufeng-LoRA/blob/main/Workflow-Qwen-Image-LORA.json)

第二优先 workflow 起点：

- `Neta-Lumina` 官方 workflow

预期依赖：

- Qwen-Image base
- guofeng LoRA
- Qwen 对应 text encoder / vae
- 可能的 aspect ratio / utility 节点

审计顺序：

1. Qwen-Image-Gufeng-LoRA workflow
2. Neta-Lumina workflow

smoke 优先级：

1. 单人古风半身像
2. 宽景山水/建筑
3. 水墨气质人物剧情镜头

### 3.5 stylized_concept

第一优先模型：

- `HiDream-ai/HiDream-I1`

第二优先模型：

- `Tongyi-MAI/Z-Image`

workflow 套件优先参考：

- [AmazingZImageWorkflow](https://github.com/martin-rizzo/AmazingZImageWorkflow)

第一优先 workflow 起点：

- `HiDream-I1_ComfyUI`

第二优先 workflow 起点：

- `AmazingZImageWorkflow`
  - `amazing-z-comics`
  - `amazing-z-image-a`
  - `amazing-z-image-b`

预期依赖：

- HiDream 模型本体
- Z-Image 模型本体
- 可能的 `rgthree-comfy`
- 可能的 `ComfyUI-GGUF`
- upscaler / refiner 依赖

审计顺序：

1. HiDream-I1 workflow
2. Amazing Z-Image Workflow
3. 仓库现有 stylized route

smoke 优先级：

1. 赛博朋克街景
2. 暗黑人物概念图
3. 海报感高饱和构图

## 4. Dasiwa 专项执行清单

目标：

- 判断 `Dasiwa` 更适合 Stage 05 还是 Stage 06

当前已知公开入口：

- [TakeuchiX/Wan2.2-DaSiWa](https://huggingface.co/TakeuchiX/Wan2.2-DaSiWa)

专项步骤：

1. 确认是否存在可公开获取的静态 T2I ComfyUI workflow
2. 若只有 I2V / Wan 路线，则标记为 `better_fit_for_stage06`
3. 若能找到稳定单帧图 workflow，则纳入 anime 路线对照 smoke

专项输出：

- `Dasiwa evidence note`
- `Dasiwa workflow source list`
- `Stage05 or Stage06` 结论

## 5. 下载与审计的建议顺序

建议按下面顺序推进，不要同时开太多路线：

1. `Qwen/Qwen-Image-2512`
2. `xuedi7/Z-Anime`
3. `valiantcat/Qwen-Image-Gufeng-LoRA`
4. `HiDream-ai/HiDream-I1`
5. `neta-art/Neta-Lumina`
6. `Tongyi-MAI/Z-Image`
7. `Dasiwa` 专项验证

理由：

- 能先把最关键的写实 / 动画 / 国风主干拉起来
- `HiDream`、`Neta-Lumina`、`Z-Image` 再作为高质量扩展和风格强化

## 6. 建议新增的本地记录文件

建议后续新增：

- `docs/STAGE05_WORKFLOW_AUDIT_LOG.md`
- `docs/STAGE05_SMOKE_TEST_SPEC.md`
- `config/stage05_route_registry.example.yaml`

## 7. 完成 Phase 2 的标准

Phase 2 算完成，至少要满足：

1. 第一批 5 条 route 都有主候选模型
2. 每条 route 都有 workflow 起点
3. 每条 route 都有明确审计顺序
4. `Dasiwa` 被明确纳入专项验证而不是继续悬空

