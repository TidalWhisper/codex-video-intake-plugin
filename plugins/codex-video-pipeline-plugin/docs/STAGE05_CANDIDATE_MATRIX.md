# Stage 05 候选模型与 Workflow 矩阵

更新日期：`2026-05-30`

## 1. 目的

这份矩阵用于 Stage 05 本地 ComfyUI 生图的下一步选型与验证。

它服务于 4 类后续工作：

1. 下载和整理候选模型
2. 收集或改造对应 workflow
3. 做本地依赖审计
4. 做统一 smoke 测试

注意：

- 这里的候选不等于已经批准为默认生产路线
- 只有 smoke evidence 完整后，路线才可以从 `candidate` 升级为 `approved` 或 `provisional`
- 当前 matrix 只覆盖第一批重点路线和 `Dasiwa` 专项验证分支
- 从这一版开始，workflow 候选默认优先看社区已经优化过的版本；没有明确 community winner 时，才退回官方模板或仓库里的过渡 workflow

## 2.1 社区优先规则

本表里的 workflow 候选现在统一按 3 层理解：

1. `current_repo`
2. `official`
3. `community`

解释：

- `current_repo` 是仓库当前已经接上、可运行、但不一定代表最终最佳实践的过渡版
- `official` 是模型作者或 ComfyUI 官方提供的基础模板
- `community` 是社区用户针对真实使用场景整理过、增强过、组合过的 workflow / workflow pack / thread evidence

选择顺序：

1. 优先 `community`
2. 没有稳定的 community artifact 时，退回 `official`
3. `current_repo` 只作为桥接，不再默认视为终版

## 2. 当前 Stage 00 风格入口与第一批 Route

本轮先处理 5 条主路线：

1. `realistic_cinematic`
2. `anime_jp`
3. `anime_cn_newguofeng`
4. `guofeng_ink`
5. `stylized_concept`

对应 Stage 00 风格入口：

- `写实电影感`
- `短剧爽感`
- `日系动画风（日本动漫感）`
- `国漫动画风（中国动画/新国风）`
- `国风水墨/古风`
- `赛博朋克`
- `暗黑惊悚`
- `广告高级感`
- `低饱和现实主义`
- `高饱和潮流感`

## 3. Route Matrix

### 3.1 realistic_cinematic

适配的 Stage 00 风格：

- `写实电影感`
- `广告高级感`
- `温暖治愈`（写实分支）

主候选：

1. `Qwen/Qwen-Image-2512`
2. `Tongyi-MAI/Z-Image`
3. `HiDream-ai/HiDream-I1`

候选理由：

- `Qwen-Image-2512`
  - 开源基础模型
  - 官方强调人像 realism、自然细节、文本布局能力
  - 适合人物、场景、商业写实图作为主基线
- `Z-Image`
  - 适合作为写实与高质量通用路线备选
  - 后续还可向 `stylized_concept` 和 `game_cg` 延展
- `HiDream-I1`
  - 更偏高质量商业视觉和宣传图候选
  - 可作为高质感 route 的增强路线

workflow 起点：

- 官方 Qwen ComfyUI 模板：
  - [Comfy-Org/workflow_templates: image_qwen_Image_2512.json](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_Image_2512.json)
- HiDream ComfyUI 包：
  - [Comfy-Org/HiDream-I1_ComfyUI](https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI)
- Z-Image 基础路线：
  - 社区 workflow pack：
    - [AmazingZImageWorkflow](https://github.com/martin-rizzo/AmazingZImageWorkflow)
    - [Z-Image-Turbo-Lora-Stack-V4](https://github.com/aistudynow/Z-Image-Turbo-Lora-Stack-V4)
  - 当前更具体的首选入口：
    - [amazing-z-photo_SAFETENSORS.json](https://github.com/martin-rizzo/AmazingZImageWorkflow/blob/master/amazing-z-photo_SAFETENSORS.json)
  - 仓库内已补的第一条 bridge：
    - `workflows/comfyui/txt2img_keyframe_realistic_zimage_photo_bridge.workflow_api.json`
  - 仓库内现有 `txt2img_keyframe_realistic` 仅保留为过渡桥接

需要验证的点：

- 人脸稳定性
- 镜头感与广告感
- 高光、肤质、服装细节
- 不要太“AI 味”

当前建议状态：

- `Qwen-Image-2512`: `priority_a`
- `Z-Image`: `priority_a`
- `HiDream-I1`: `priority_b`

当前结论：

- `realistic_cinematic` 这条线，社区优先候选先看 `Z-Image` 一侧的成熟 pack，而不是继续把仓库内通用 Qwen workflow 当终版
- `Qwen-Image-2512` 仍然是稳定底线，但目前没有看到明显胜出的“短视频 keyframe 向社区增强版”
- 仓库现在已经落下一条第一版 `Z-Image photo bridge`，并在 `2026-05-30` 拿到本地 Stage 05 executor smoke 证据，已替换 `realistic_cinematic` 的默认 ComfyUI fallback 执行路线

### 3.2 anime_jp

适配的 Stage 00 风格：

- `日系动画风（日本动漫感）`
- `温暖治愈`（动画分支）

主候选：

1. `circlestone-labs/Anima`
2. `xuedi7/Z-Anime`
3. `neta-art/Neta-Lumina`
4. `Dasiwa`（专项分支，不直接默认）

候选理由：

- `Anima`
  - 2B anime-focused T2I 模型
  - 官方明确说更适合 anime/illustration，不适合 realism
- `Z-Anime`
  - 基于 Z-Image 的完整 anime fine-tune
  - 不是简单 LoRA merge
- `Neta-Lumina`
  - 官方明确面向 anime-style、storyboards、character design
  - 适合角色图、故事分镜、海报向画面
- `Dasiwa`
  - 社区关注度存在，但当前更像需要专项验证的候选，不应直接当默认主线

workflow 起点：

- `Anima`
  - 使用其模型卡中附带的 `anima_comparison.json` 作为原始图
- `Z-Anime`
  - 直接使用模型仓自带的 `Z-Anime-Workflow-v1.json`
- `Neta-Lumina`
  - 官方 workflow：
    - [neta-art/Neta-Lumina](https://huggingface.co/neta-art/Neta-Lumina)
    - [lumina_workflow.json](https://huggingface.co/neta-art/Neta-Lumina/blob/main/lumina_workflow.json)

需要验证的点：

- 角色脸型稳定性
- 眼睛与线稿质量
- 构图是否更像宣传 key visual，而不是泛二次元插图
- 场景镜头可读性

当前建议状态：

- `Anima`: `priority_a`
- `Z-Anime`: `priority_a`
- `Neta-Lumina`: `priority_b`
- `Dasiwa`: `special_validation`

当前结论：

- `anime_jp` 不应该长期停留在 repo 里的 generic anime compat workflow
- 第一优先替换对象应是 `Anima` 原生图或 `Z-Anime` 原生图
- `Dasiwa` 目前不适合作为这条静态 T2I 路线的默认答案

### 3.3 anime_cn_newguofeng

适配的 Stage 00 风格：

- `国漫动画风（中国动画/新国风）`

主候选：

1. `neta-art/Neta-Lumina`
2. `xuedi7/Z-Anime`
3. `Dasiwa`（专项分支）

候选理由：

- 这条路线既不能完全等于 `anime_jp`，也不能完全等于 `guofeng_ink`
- `Neta-Lumina` 更接近“动画感 + 东方风格语言”的中间地带
- `Z-Anime` 可作为备选，观察其是否能承载国漫式视觉表达
- `Dasiwa` 需要重点看是否更适合这条路线，而不是纯日漫线

workflow 起点：

- 以 `Neta-Lumina` 官方 workflow 为主
- 以现有 anime workflow 做辅助对照

需要验证的点：

- 是否保留动画角色感
- 是否具备东方美术语言
- 是否会退化为普通 anime 或普通古风插画

当前建议状态：

- `Neta-Lumina`: `priority_a`
- `Z-Anime`: `priority_b`
- `Dasiwa`: `special_validation`

当前结论：

- 这条路线已经切出了独立 repo workflow 文件，但它仍然只是 `Lumina` 栈的桥接落地
- 到目前为止，还没有找到比 `Neta-Lumina` 更有把握的“社区优化版国漫 / 新国风动画”现成 workflow
- 真实策略应该是继续把 `Neta-Lumina` 当主候选，同时持续补 community source，而不是假装已经有终版

### 3.4 guofeng_ink

适配的 Stage 00 风格：

- `国风水墨/古风`

主候选：

1. `valiantcat/Qwen-Image-Gufeng-LoRA`
2. `neta-art/Neta-Lumina`
3. 继续补充更专用的 guofeng / ink-wash 开源模型

候选理由：

- `Qwen-Image-Gufeng-LoRA`
  - 明确面向古风/东方人物插画
  - 仓库内直接附带 ComfyUI workflow 文件
- `Neta-Lumina`
  - 虽不是纯水墨专用，但有成为“国漫动画风/东方插画风”共用候选的价值

workflow 起点：

- 官方/模型仓 workflow：
  - [valiantcat/Qwen-Image-Gufeng-LoRA](https://huggingface.co/valiantcat/Qwen-Image-Gufeng-LoRA)
  - [Workflow-Qwen-Image-LORA.json](https://huggingface.co/valiantcat/Qwen-Image-Gufeng-LoRA/tree/main)
- `Neta-Lumina` 官方 workflow 作为旁路对照

需要验证的点：

- 是否压制现代摄影感
- 墨韵、服饰、发型、饰品是否成立
- 是否能明显区别于 `realistic_cinematic`

当前建议状态：

- `Qwen-Image-Gufeng-LoRA`: `priority_a`
- `Neta-Lumina`: `priority_b`

当前结论：

- `guofeng_ink` 的模型方向仍然优先 `Qwen-Image-Gufeng-LoRA`
- 但在 `2026-05-30` 核验中，抓下来的 `Workflow-Qwen-Image-LORA.json` 实际挂到了无关的 `liuyifei` LoRA，不能直接当作可信导入源
- 因此当前 repo 内的 `txt2img_keyframe_guofeng_ink` 继续保留为主执行实现；这条路线的真实状态应视为 `workflow source gap`，不是“只差 API 转换”

### 3.5 stylized_concept

适配的 Stage 00 风格：

- `赛博朋克`
- `暗黑惊悚`
- `高饱和潮流感`

主候选：

1. `HiDream-ai/HiDream-I1`
2. `Tongyi-MAI/Z-Image`
3. `AmazingZImageWorkflow`（作为 workflow 套件候选）

候选理由：

- `HiDream-I1`
  - 适合高质感概念图、视觉宣传图、强设计感路线
- `Z-Image`
  - 作为通用强底座，可向概念、插画、潮流方向拉伸
- `AmazingZImageWorkflow`
  - 社区现成 workflow 套件
  - 有 illustration / comics / photo 等多组可分拆结构
  - 适合拿来做 stylized 的 workflow 参考母版

workflow 起点：

- [HiDream-ai/HiDream-I1](https://github.com/HiDream-ai/HiDream-I1)
- [Comfy-Org/HiDream-I1_ComfyUI](https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI)
- [AmazingZImageWorkflow](https://github.com/martin-rizzo/AmazingZImageWorkflow)
- [amazing-z-image-b_SAFETENSORS.json](https://github.com/martin-rizzo/AmazingZImageWorkflow/blob/master/amazing-z-image-b_SAFETENSORS.json)
- [Community workflow: HiDream-I1-Dev + FaceDetailer](https://www.reddit.com/r/comfyui/comments/1kk78l9)

需要验证的点：

- 强色彩和强轮廓是否稳定
- 画面是否保留主体可读性
- 是否能形成真正的概念艺术气质
- 是否和 `realistic_cinematic` 拉开明显差异

当前建议状态：

- `HiDream-I1`: `priority_a`
- `Z-Image`: `priority_a`
- `AmazingZImageWorkflow`: `workflow_reference`

当前结论：

- `stylized_concept` 目前最强的“可直接迁移”的社区资产，仍然是 `AmazingZImageWorkflow` 里的 `amazing-z-image-b_SAFETENSORS.json`
- 仓库内现在已经有第一版 `repo bridge`，把它裁成了 Stage 05 可 patch 的 API workflow，并将其提升为当前默认本地 ComfyUI fallback
- `HiDream` 仍然保留为有价值的比较候选，但当前定位更适合做对照路线，而不是继续占用默认执行位

## 4. Dasiwa 专项验证矩阵

### 4.1 当前证据结论

`Dasiwa` 当前公开证据更偏：

- `Wan 2.2`
- `I2V / 视频`
- 社区 merge / workflow 路线

当前最明确的公开页之一：

- [TakeuchiX/Wan2.2-DaSiWa](https://huggingface.co/TakeuchiX/Wan2.2-DaSiWa)
- [NickPwned/comfyui-dasiwa-wan-2-2-i2v-fastfidelity-c-aio-77](https://github.com/NickPwned/comfyui-dasiwa-wan-2-2-i2v-fastfidelity-c-aio-77)
- [matusadamovic/dasiwa-wan-2.2-i2v-fastfidelity-c-aio-31.json](https://github.com/matusadamovic/dasiwa-wan-2.2-i2v-fastfidelity-c-aio-31.json)

从已公开可直接验证的内容看，它暂时不像 `Anima`、`Z-Anime`、`Neta-Lumina` 这样，是一个边界清晰的 Stage 05 静态 T2I 默认主线候选。

### 4.2 在本项目中的定位

当前建议：

- 将 `Dasiwa` 放入 `anime_jp` 候选池
- 放入 `anime_cn_newguofeng` 候选池
- 不直接设为 Stage 05 默认路线

### 4.3 专项验证任务

必须单独回答以下问题：

1. 是否存在稳定的静态 `txt2img` 路线
2. 是否更适合作为 `首帧/尾帧` 或 `Stage 06` 资产候选
3. 是否依赖特殊私有 workflow 或社区未稳定节点
4. 是否能留下可复现的本地 smoke evidence

### 4.4 允许的结论

后续只允许得出这三种结论之一：

- `approved_for_stage05`
- `provisional_for_stage05`
- `better_fit_for_stage06`

## 5. 本地准备清单

在真正开始导入模型和 workflow 前，先准备这些资产：

1. `route registry`
2. `candidate download manifest`
3. `workflow dependency audit report`
4. `smoke prompt pack`

建议新增文件：

- `config/stage05_route_registry.example.yaml`
- `docs/STAGE05_SMOKE_TEST_SPEC.md`
- `temp/stage05-candidate-downloads.md` 或同类本地记录

## 6. 先做哪几个

执行优先顺序建议：

1. `realistic_cinematic`
2. `anime_jp`
3. `guofeng_ink`
4. `stylized_concept`
5. `anime_cn_newguofeng`
6. `Dasiwa` 专项分支

理由：

- 能最快把“写实 / 日漫 / 国风 / 强风格”四个最常用大类打穿
- `anime_cn_newguofeng` 和 `Dasiwa` 都更适合放到对照验证阶段，而不是一开始就强塞成默认

## 7. 推荐下一步动作

下一步不改主逻辑，先做：

1. 为每条 route 建立 `候选下载清单`
2. 为每条 route 指定 `首选 workflow 起点`
3. 跑一轮本地 `workflow audit`
4. 定义统一 smoke prompt 集

只有这 4 步完成后，才开始改：

- `config/stage05_style_profiles.example.yaml`
- `config/workflow_node_mapping.example.yaml`
- `new_keyframe_image_jobs.py`
- `run_comfyui_txt2img.py`
