# 后续真实 Provider 接入详细开发计划

包内版本：1.1.2

目标：在现有 Stage 00-09 闭环和已接入 provider runner 的基础上，完成本机真实环境验证、失败恢复强化和端到端稳定化。

## 一、当前基线

当前已完成：

- Stage 00：基础需求确认与 Brief 锁定
- Stage 01：剧本生成
- Stage 02：分镜脚本生成
- Stage 03：人物画像 / Character Bible
- Stage 04：关键帧提示词 + 过渡动作提示词
- Stage 05：关键帧图片生成框架与 manifest 校验
- Stage 06：视频片段生成框架与 manifest 校验
- Stage 07：配音与背景音乐框架与 manifest 校验
- Stage 08：粗剪合成 / FFmpeg 自动合成框架
- Stage 09：质量检查与交付框架
- provider 配置读取与健康检查
- OpenAI GPT Image 2 图片生成 runner
- ComfyUI txt2img / LTX I2V / IndexTTS2 / Music runners
- Stage 05 → Stage 09 provider-backed 自动化测试

当前仍未完全闭环：

- 用户本机真实 workflow_api.json 与节点映射稳定沉淀
- 用户本机 OpenAI / ComfyUI / FFmpeg 环境最终验收
- 最小真实项目案例跑通并保留足够证据
- fallback、失败恢复、重试和交付细节继续强化

## 二、开发总原则

1. 不破坏现有 Stage 00-09 状态机。
2. 不让模型直接跳过 manifest 和 validator。
3. 每个真实 provider 都必须有 dry-run、single-job、batch 三种模式。
4. provider 失败时必须写入错误清单，不能伪造完成。
5. Stage 05-07 不允许只凭自然语言判断成功，必须以文件和 manifest 为证据。
6. 真实 ComfyUI 工作流必须从用户本机 ComfyUI 导出 API JSON 后接入，不要凭空假设节点 ID。

## 三、建议版本路线

### 已完成基线：Provider 配置与健康检查

新增：

- `config/providers.yaml`
- `config/providers.example.yaml`
- `config/workflow_node_mapping.yaml`
- `scripts/providers/check_provider_config.py`
- `scripts/providers/check_comfyui_server.py`
- `scripts/providers/check_openai_image_provider.py`

验收标准：

- 能读取配置。
- 能检查 ComfyUI 是否在线。
- 能检查 OpenAI API key 是否存在。
- 不生成任何真实素材。

### 已完成基线：OpenAI GPT Image 2 Stage 05 接入

新增：

- `scripts/providers/openai_image_client.py`
- `scripts/providers/run_openai_gpt_image2.py`
- `scripts/providers/sync_openai_image_outputs.py`

改造：

- Stage 05 根据 `keyframe_prompts.json` 生成 `openai_image_requests.json`。
- 调用 GPT Image 2 生成关键帧图片。
- 输出到 `05_images/keyframes/`。
- 回写 `keyframe_image_manifest.json`。

验收标准：

- 单个 shot 可以真实生成 start/end keyframe。
- batch 模式可生成全部 keyframe。
- final validator 通过。
- 失败时 manifest 中记录 provider_error。

### 已完成基线：ComfyUI txt2img Stage 05 fallback 接入

新增：

- `scripts/providers/comfyui_client.py`
- `scripts/providers/run_comfyui_txt2img.py`
- `workflows/comfyui/txt2img_keyframe.workflow_api.json`，由用户本机导出后放入。

改造：

- OpenAI 失败或禁用时，自动使用 ComfyUI txt2img。
- 允许通过 node mapping 配置替换 prompt、negative_prompt、seed、width、height、batch_size。

验收标准：

- ComfyUI API `/prompt` 可提交任务。
- 能轮询 `/history/{prompt_id}`。
- 能定位输出图片并复制到项目目录。
- final validator 通过。

### 已完成基线：ComfyUI LTX I2V Stage 06 接入

新增：

- `scripts/providers/run_comfyui_ltx_i2v.py`
- `workflows/comfyui/i2v_ltx.workflow_api.json`，由用户本机导出后放入。

改造：

- Stage 06 使用 Stage 05 的 start/end keyframe。
- 使用 Stage 04 的 motion prompt。
- 生成 5-15 秒视频片段。
- 输出到 `06_video_clips/clips/`。

验收标准：

- 每个 shot 至少有一个 mp4。
- mp4 文件真实存在，大小大于 0。
- `video_clip_manifest.json` final 校验通过。

### 已完成基线：IndexTTS2 / 音乐 Stage 07 接入

新增：

- `scripts/providers/run_comfyui_indextts2.py`
- `scripts/providers/run_comfyui_music.py`
- `workflows/comfyui/indextts2.workflow_api.json`
- `workflows/comfyui/HeartMuLa_workflow_fixed_importable.json`
- `workflows/comfyui/AceStep_Music_Workflow.json`

改造：

- 根据 `script.json` 和 `storyboard.json` 生成旁白/对白任务。
- 调用 IndexTTS2 生成 `voice/*.wav`。
- 调用音乐 provider 或本地音乐库生成/复制 `music/BGM_MAIN.wav`。
- 回写 `audio_manifest.json`。

验收标准：

- 需要配音时 voice 文件真实存在。
- 需要背景音乐时 music 文件真实存在。
- `audio_manifest.json` final 校验通过。

### 当前重点：Stage 08 FFmpeg 与 Stage 09 交付稳定化

目标：从 placeholder/基础合成升级成更可靠的粗剪生成。

新增：

- 视频规格统一：分辨率、帧率、编码、音频采样率。
- 音频混音：旁白、对白、BGM 音量控制。
- 字幕生成与烧录可选。
- concat 失败重试。

验收标准：

- `rough_cut.mp4` 可播放。
- `assembly_manifest.json` 记录 ffmpeg 命令、返回码、stderr 摘要。
- 失败时不能进入 Stage 09。

### 当前重点：全链路真实本机 E2E

目标：从一个简单创意到粗剪交付，至少跑通一个真实本地案例。

验收标准：

- OpenAI Image 或 ComfyUI 至少一个图片 provider 可用。
- ComfyUI LTX I2V 可生成至少一个视频片段。
- Stage 08 可合成。
- Stage 09 可交付。
- 产生完整 `video_projects/<project_id>/` 工程包。

## 四、Codex CLI 执行顺序建议

在本地 Codex CLI 中按以下顺序执行：

1. 先让 Codex 阅读：
   - `docs/CURRENT_PROVIDER_STATUS.md`
   - `docs/DEVELOPMENT_PLAN_COMFYUI_AND_OPENAI_IMAGE.md`
   - `docs/PROVIDER_INTEGRATION_CONTRACTS.md`
   - `docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md`
2. 执行 `prompts/codex/00-master-task-comfyui-openai-image.md`。
3. 先跑本机前置检查和 provider health。
4. 再用最小真实项目验证 Stage 05-09。
5. 针对失败点补强 fallback、重试和交付稳定性。
6. 每一步都跑 `run_all_tests.cmd`。

## 五、禁止事项

- 禁止绕过 manifest。
- 禁止没有真实输出文件却写 success。
- 禁止只靠 Codex 自述说“已生成”。
- 禁止把 workflow 节点 ID 写死在代码里，必须走 `workflow_node_mapping.yaml`。
- 禁止把 API key 写入仓库或项目文件。
