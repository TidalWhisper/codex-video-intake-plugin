# Stage 05 Qwen 参考图一致性工作流规则

配套运行原理图谱：

- [stage05-qwen-workflow-runtime-map.md](./stage05-qwen-workflow-runtime-map.md)
- [stage05-qwen-quality-gate-rules.md](./stage05-qwen-quality-gate-rules.md)
- [stage05-qwen-nextscene-prompt-convergence-rules.md](./stage05-qwen-nextscene-prompt-convergence-rules.md)

## 适用目标

当 Stage 05 的真实目标是：

- `根据 Stage 03 主人物参考图`
- `按 Stage 04 已确认分镜逐镜生成关键帧`
- `单主角跨场景保持脸 / 发型 / 服装主轮廓一致`
- `输出可直接衔接 Stage 06 的 start / end 单帧`

才使用本规则。

不要把“能批量出很多图”当成 Stage 05 主流程成立。Stage 05 的判断标准始终是：

- 每次只服务一个明确镜头帧
- 输出单张关键帧
- 镜头文本来自 `04_keyframes/keyframe_prompts.json`
- 结果可回填到 `05_images/keyframes/Sxxx_start.png|Sxxx_end.png`

正式调用前，先阅读：

- [stage05-qwen-workflow-runtime-map.md](./stage05-qwen-workflow-runtime-map.md)
- [stage05-qwen-quality-gate-rules.md](./stage05-qwen-quality-gate-rules.md)
- [stage05-qwen-nextscene-prompt-convergence-rules.md](./stage05-qwen-nextscene-prompt-convergence-rules.md)

它负责解释两条本地 Qwen 工作流的实际主干、危险分支、Stage 05 注入位和 Stage 06 衔接边界。

## 两个本地工作流的结论

### 结论

在下面两个本地工作流里：

- `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`
- `Qwen-Edit-2511-一键多角度，多场景分镜.json`

更适合作为 **Stage 05 主流程基底** 的是：

- `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`

但必须按本文件定义的 **单镜头执行模式** 使用，不能按“16宫格批量自动分镜演示流”原样使用。

### 为什么不是 `Qwen-Edit-2511-一键多角度，多场景分镜`

这个工作流有两条不同用途的分支：

1. `1.单图出分镜图编辑1`
2. `2.单图出多角度图编辑1`

它的问题不是不能出图，而是 **太容易被错用**：

- 上半分支带有 `Qwen3_VQA -> Prompt_Edit -> easy promptLine` 的自动提示词生成链
- 该链默认根据参考图里的 **人物和环境** 自动扩写 `Next Scene`
- 其中系统提示明确要求“根据参考图片构架在同一场景中”
- 下半分支又明确偏向“多角度 / 机位变换 / camera move”

这和 Stage 05 主流程冲突：

- Stage 05 的镜头来源必须是 Stage 04，而不是工作流自己写剧情
- Stage 05 需要跨镜头 / 跨场景，而不是强绑定“同一场景”
- Stage 06 需要逐镜 start/end 关键帧，不是相机试角度素材包

因此：

- `Qwen-Edit-2511-一键多角度，多场景分镜.json`
  - 可用于 **镜头试验 / 同场景多角度 repair / 预演**
  - 不可作为 Stage 05 主流程默认执行器

## 选中的工作流

### 文件

- `F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`

### 选择原因

这条流虽然名字里有“16宫格 / 自动分镜”，但它的主干更适合 Stage 05 的一个关键要求：

- `easy promptLine` 节点的 `Next Scene` 文本是 **手动可控输入**
- 没有把 Stage 04 prompt 来源偷偷交给别的自动写词链
- 单张参考图直接进入 `TextEncodeQwenImageEditPlusAdvance_lrzjason`
- 模型路径固定，适合做“参考图 + 明确 shot prompt”执行

换句话说：

- 它更像 `参考图驱动的 shot prompt 执行器`
- 而不是 `自动写剧情再出图的工作流`

这更符合 Stage 05 的主流程职责。

### 当前主流程映射键

当前 repo 里与这条流对应的映射键是：

- `stage05_realistic_cinematic_qwen_edit_nextscene_local`

已约束的最小注入位：

- `positive_prompt -> #123`
- `reference_image_path -> #13`
- `seed -> #10`
- `output_prefix -> #89`

这不是鼓励随意扩展参数，而是明确 Stage 05 主流程目前只开放这四个必要控制点。

## 这条流在 Stage 05 的正确用法

### 总原则

**一条 Stage 05 job = 一次工作流执行 = 一条明确的 shot frame prompt = 一张关键帧。**

不要在主流程里一次塞 16 条、8 条、4 条 prompt 让它批量吐图，再靠运气挑。

### 并发执行规则

同一个 `keyframe_image_manifest.json` 不要并行真实执行多个 `image_id`。

原因不是 ComfyUI 不能同时出图，而是当前 repo 这层 runner 会回写：

- `keyframe_image_manifest.json`
- `comfyui_image_requests.json`

如果同一个 manifest 被并行回写，容易出现：

- 图片已经出图成功
- 但 manifest 某一条 job 状态被后一次写回覆盖成旧状态

因此当前硬规则是：

1. 同一个 smoke manifest 下的真实执行按串行跑
2. 如果要并行，必须先拆成多个独立 manifest
3. 发现“文件已存在但 manifest 仍 pending”时，优先按串行补跑修正账面状态

### 输入规则

1. 只允许使用一个主角参考图：
   - `03_characters/reference_images/CHAR_001_primary.png`

2. 参考图必须满足：
   - 单人
   - 衣服清楚
   - 脸清楚
   - 不要有强环境叙事干扰
   - 尽量提前裁成与目标镜头一致的主导比例

3. `Next Scene` 文本必须直接来自 Stage 04 语义，不允许工作流自己发散剧情。

4. 每次只写一条完整 `Next Scene` 文本，不要让工作流在主流程里做多行批量分镜。

### Prompt 写法

传给该流的文本必须已经是 **成品级 shot prompt**，至少包含：

- 人物身份锁定
- 场景地点
- 当前动作
- 镜头景别 / 机位
- 光线
- 情绪

推荐顺序：

`同一主角约束 + 场景 + 动作 + 镜头 + 光线 + 情绪推进`

如果任务已经进入真实 Stage 05 smoke 或主流程执行，不够只写到“有镜头”。

还必须按：

- [stage05-qwen-nextscene-prompt-convergence-rules.md](./stage05-qwen-nextscene-prompt-convergence-rules.md)

把这些字段收紧：

- 视角
- 景别
- 人物占比
- 相邻镜头差异点
- 背影视角时的 `full-frame / no black bars / no embedded border`

### 禁止事项

主流程里禁止：

- 让这条流自动写 16 条剧情分镜
- 把它当 contact sheet / 宫格图生成器使用
- 混入多人
- 混入换装
- 混入“只改风格不改镜头意图”的抽卡式 prompt
- 用它替代 Stage 04

### 固定工作流栈

保持该流内部现有栈不乱切：

- `Qwen\\Qwen-Rapid-AIO-NSFW-v18.safetensors`
- `Qwen\\next-scene_lora_v1-3000.safetensors`
- `Qwen\\WangMoon.v5美女.safetensors`
- `Qwen\\Kook_Qwen_V3极致真实.safetensors`

不要在 Stage 05 主流程里临时增删 LoRA、改成别的随机美学组合。

## Stage 06 衔接规则

要进入 Stage 06，这条流的输出必须满足：

1. 输出是单张关键帧，不是宫格拼图
2. 文件能稳定落到：
   - `05_images/keyframes/S001_start.png`
   - `05_images/keyframes/S001_end.png`
   - `...`
3. 单主角明确、无遮挡、无多人误入
4. 构图清晰，适合作为 LTX 首尾帧
5. 相邻镜头之间允许场景变化，但不能人物换脸、换发型、换服装主结构

此外，必须满足：

- [stage05-qwen-quality-gate-rules.md](./stage05-qwen-quality-gate-rules.md)

里的最小放行标准，尤其不能带着下面这些问题直接进入 Stage 06：

- 黑边
- 宫格/拼贴
- 相邻镜头构图近似重复
- 身份锚点弱到无法稳定锁人

这条 Qwen 流只适合：

- `stage06_route_hint = single_subject_motion`

不适合默认直接喂给：

- 多人互动
- 强交接动作
- 必须补 mid guide 的复杂镜头

这类镜头需要拆 shot 或改别的 Stage 05 路线。

## 实际选择规则

当任务是：

- 单女主
- 参考图锁人
- 根据 Stage 04 明确 shot prompt 逐镜出图
- 结果要进入 Stage 06

则：

1. **优先** 使用 `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版`
2. 但必须按 **单镜头执行模式** 调用
3. 不允许一次多行批量当主流程

当任务是：

- 想看同场景多个机位
- 想试镜头角度
- 想做 repair / angle variation

才允许使用：

- `Qwen-Edit-2511-一键多角度，多场景分镜.json`

而且只把它当 **辅助工作流**，不要让它替代 Stage 05 主流程。
