# Stage 05 Realistic Community Audit

更新日期：`2026-06-02`

## 1. 当前主线

- 当前主线路线：`realistic_cinematic`
- 当前处理镜头：`S001_start / S001_end`
- 当前验收项：
  - 建立镜头必须成立
  - 单主体人数必须正确
  - 画面必须符合文字描述
  - 不能出现片场/棚拍污染
  - 不能出现多手多脚、错误道具、错误主体关系
- 本轮是否触碰非主线：`否`

## 2. 本轮核查的社区/官方来源

### 2.1 社区优先来源

1. `AmazingZImageWorkflow`
   - `amazing-z-photo_SAFETENSORS.json`
   - 来源：<https://github.com/martin-rizzo/AmazingZImageWorkflow>
2. `Z-Image-Turbo-Lora-Stack-V4`
   - 来源：<https://github.com/aistudynow/Z-Image-Turbo-Lora-Stack-V4>
3. 本机已收集的社区 Qwen 2512 写实工作流
   - `F:/ComfyUI/ComfyUI/user/default/workflows/B站像素幻想/千问-2512-数字人生成.json`
   - `F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-人物形象生成-千问2512.json`

### 2.2 官方基础模板

1. Qwen 官方模板
   - `image_qwen_Image_2512.json`
   - 来源：<https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_Image_2512.json>
2. HiDream 官方 ComfyUI 包
   - 来源：<https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI>

## 3. 本机环境核查结果

### 3.1 已确认存在的社区原版依赖

- `F:/ComfyUI/ComfyUI/custom_nodes/rgthree-comfy`
- `F:/ComfyUI/ComfyUI/models/diffusion_models/Zimage/z_image_turbo_bf16.safetensors`
- `F:/ComfyUI/ComfyUI/models/clip/Zimage/qwen_3_4b.safetensors`
- `F:/ComfyUI/ComfyUI/models/vae/Zimage/ae.safetensors`
- `F:/ComfyUI/ComfyUI/models/upscale_models/Zimage/4x_foolhardy_Remacri.safetensors`
- `F:/ComfyUI/ComfyUI/models/diffusion_models/Qwen/qwen_image_2512_fp8_e4m3fn.safetensors`
- `F:/ComfyUI/ComfyUI/models/clip/Qwen2.5/qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `F:/ComfyUI/ComfyUI/models/vae/Qwen/qwen_image_vae.safetensors`
- `F:/ComfyUI/ComfyUI/models/loras/Qwen_2512/Kook_千问写实_Kook_Qwen_V1稳定版.safetensors`
- `F:/ComfyUI/ComfyUI/models/loras/Qwen_2512/Kook_千问写实_Kook_Qwen_V2美人版.safetensors`
- `F:/ComfyUI/ComfyUI/models/loras/Qwen_2512/Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors`

### 3.2 已确认存在的本地社区工作流文件

- `F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json`
- `F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/image_qwen_Image_2512.json`
- `F:/ComfyUI/ComfyUI/user/default/workflows/B站像素幻想/千问-2512-数字人生成.json`
- `F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-人物形象生成-千问2512.json`

### 3.3 服务器状态

- `cmd /c F:\ComfyUI\Codex\comfy-python.cmd F:\ComfyUI\Codex\comfyui_api.py check` 已成功
- 说明：本机当前不是“缺模型/缺节点导致社区方案完全无法落地”，而是“社区原版工作流形态与当前 Stage 05 执行器能力不一致”

## 4. 这次核查得出的关键结论

### 4.1 Amazing Z-Photo 原版并不是缺资源

`Amazing Z-Photo` 原版的核心依赖本机已经基本齐备，不能再把它简单归因成“资源不够所以只能阉割”。

### 4.2 当前真正 blocker 在执行链形态

当前仓库里的 Stage 05 执行链有两个硬限制：

1. `run_comfyui_txt2img.py` 只接受 API workflow JSON
2. `workflow_node_mapping.yaml` 只支持“按 node_id + input_name 补丁式写值”

而 `Amazing Z-Photo` 原版是一个重度 `rgthree` 的 ComfyUI UI graph：

- 顶层是 UI graph，不是 API workflow 导出
- 大量使用 `Any Switch (rgthree)`、`Node Collector (rgthree)`、`Mute / Bypass Repeater (rgthree)`、`Power Lora Loader (rgthree)` 等前端图内路由
- 其“真正可执行 prompt”依赖 ComfyUI 前端的 `graphToPrompt` 转换阶段

### 4.3 当前没有发现可直接复用的后端转换入口

本轮在本机 ComfyUI 代码和仓库执行器里，没有发现一个已接入的、可直接在 CLI / Python runner 中把 UI graph 原样转换成 API prompt 的现成后端入口。

这意味着：

- `Amazing Z-Photo` 原版可以在 ComfyUI 前端作为社区工作流运行
- 但它还不能直接被当前插件的 Stage 05 批处理执行器“原样吃进去”

### 4.4 当前 realistic 主线不应再把“瘦身 bridge 能跑”误报成“社区原版已落地”

仓库已有：

- `workflows/comfyui/txt2img_keyframe_realistic_zimage_photo_bridge.workflow_api.json`

它只是吸收了 `Amazing Z-Photo` 的部分模型栈和一部分 prompt anchor 经验，不等于“社区原版完整接入”。

## 5. realistic 主线的当前可执行策略

在不撒谎、不伪装“原版已落地”的前提下，当前 realistic 主线只能分成两层：

### 5.1 当前可直接批量执行的路线

1. `Qwen 2512` 原生 prompt-only 路线
2. 仓库内已有的 `Z-Image photo bridge`
3. 本机现成的社区 Qwen 2512 写实工作流，可继续抽取其 LoRA 组合、采样参数和 prompt 结构经验

### 5.2 仍未完成的原版落地项

1. 为 Stage 05 增加一条“面向 ComfyUI 原版 UI workflow”的执行路径
2. 或者先通过 ComfyUI 前端把社区原版工作流导成稳定的 API workflow，再纳入插件执行器

在这一步做完之前，不允许把 `Amazing Z-Photo` 原版描述成“已完整落地”。

## 6. 本轮新增的 realistic-only 扩展测试范围

本轮已把 realistic-only 扩展测试案例落进仓库脚本，新增 3 组 pack，全部仍路由到 `realistic_cinematic`：

1. `realistic_establishing_expanded_pack`
   - `写实电影感`
   - 海滩黄昏、港口清晨、夜雨街景
2. `realistic_healing_expanded_pack`
   - `温暖治愈`
   - 咖啡馆晨光、山路蓝调时刻、屋顶花园日落
3. `realistic_editorial_expanded_pack`
   - `广告高级感`
   - 酒店大堂、沙漠公路汽车广告、城市楼顶高端写实

这些 pack 的共同约束是：

- 单主体
- 宽景/建立镜头优先
- 更看环境成立而不是怼脸肖像
- 用来专门筛查 `realistic_cinematic` 是否再次退化成片场图、棚拍图或时尚人像图

## 7. 当前最务实的下一步

严格按主线推进时，下一步优先级应是：

1. 用新增 realistic-only 测试 pack 继续做真实 smoke
2. 人工语义复核 `S001_start / S001_end` 以及新的建立镜头样本
3. 如果 `Qwen 2512` 仍然不稳定，再从本机社区 Qwen 2512 写实流里继续抽取更成熟的 LoRA 叠法、采样设置和 prompt 结构
4. 单独立项做“社区原版 UI workflow 执行路径”前，不再把任何瘦身 bridge 说成“原版已完成”
