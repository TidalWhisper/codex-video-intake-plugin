# 00_CODEX_MASTER_PLAN.md

这是 `codex-video-intake-plugin` 的总计划文档。Codex CLI 后续继续开发时，必须先读本文件。

## A. 总目标

把当前 Stage 00-09 的视频生产流程框架，升级为可以调用真实后端的生产插件：

```text
用户想法
→ 剧本
→ 分镜
→ 人物画像
→ 关键帧提示词
→ GPT Image 2 / ComfyUI 生成关键帧
→ ComfyUI LTX I2V 生成视频片段
→ IndexTTS2 / 音乐生成音频
→ FFmpeg 粗剪合成
→ QA 检查与交付
```

## B. 当前真实状态

已完成：

```text
Stage 00-09 目录结构
Stage 00-09 SKILL.md
Stage 00-09 manifest / schema / validator
Stage 00-09 placeholder 生成脚本
run_all_tests.cmd / run_all_tests.py
后续 provider 接入文档和任务提示词
```

未完成：

```text
真实 GPT Image 2 API 调用
真实 ComfyUI API Client
真实 ComfyUI txt2img 工作流接入
真实 ComfyUI LTX I2V 工作流接入
真实 IndexTTS2 / 音乐工作流接入
真实 provider fallback
真实失败重试策略
```

## C. 必读文件顺序

Codex 必须按顺序读取：

```text
1. CODEX_START_HERE.md
2. docs/00_CODEX_MASTER_PLAN.md
3. docs/CURRENT_PROVIDER_STATUS.md
4. docs/DEVELOPMENT_PLAN_COMFYUI_AND_OPENAI_IMAGE.md
5. docs/PROVIDER_INTEGRATION_CONTRACTS.md
6. docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md
7. docs/CODEX_LOCAL_TASK_RUNBOOK.md
8. config/providers.example.yaml
9. config/workflow_node_mapping.example.yaml
10. prompts/codex/00-master-task-comfyui-openai-image.md
```

## D. 推荐实现顺序

### D1. Provider 基础设施

新增或完善：

```text
config/providers.example.yaml
scripts/provider_config.py
scripts/check_provider_health.py
```

验收：

```text
配置缺失时报明确错误
环境变量缺失时报明确错误
provider disabled 时不会被调用
run_all_tests.py 通过
```

### D2. GPT Image 2 / OpenAI Images Provider

新增：

```text
scripts/openai_image_client.py
scripts/run_openai_image2_keyframes.py
```

接入 Stage 05：

```text
05_images/openai_image_requests.json
05_images/keyframe_image_manifest.json
05_images/keyframes/*.png
```

验收：

```text
请求记录完整
输出图片存在且非 0 字节
manifest 写入 provider=openai_image2
失败时写入 error_message，不允许假成功
```

### D3. ComfyUI Core Client

新增：

```text
scripts/comfyui_client.py
scripts/check_comfyui_server.py
scripts/run_comfyui_workflow.py
```

基础能力：

```text
GET /system_stats 或健康检查
POST /prompt
轮询 /history/{prompt_id}
收集 output images/videos/audio
```

验收：

```text
ComfyUI 未启动时报明确错误
workflow 文件不存在时报明确错误
节点映射缺失时报明确错误
```

### D4. Stage 05 ComfyUI txt2img fallback

新增：

```text
workflows/comfyui/txt2img_keyframe.workflow_api.json
scripts/run_comfyui_txt2img_keyframes.py
```

验收：

```text
OpenAI provider 失败或禁用时可切 ComfyUI
生成图片写入 keyframe_image_manifest.json
final validator 通过
```

### D5. Stage 06 LTX I2V

新增：

```text
workflows/comfyui/i2v_ltx23.workflow_api.json
scripts/run_comfyui_ltx_i2v.py
```

验收：

```text
每个 shot 引用 Stage 05 start/end keyframe
生成 clips/*.mp4
video_clip_manifest.json final 通过
```

### D6. Stage 07 IndexTTS2 / Music

新增：

```text
workflows/comfyui/indextts2.workflow_api.json
workflows/comfyui/music_generation.workflow_api.json
scripts/run_comfyui_indextts2.py
scripts/run_comfyui_music.py
```

验收：

```text
voice/*.wav 真实存在
music/*.wav 真实存在
audio_manifest.json final 通过
```

### D7. Stage 08/09 真实合成与交付强化

完善：

```text
scripts/ffmpeg_assembler.py
scripts/package_delivery.py
scripts/validate_qa_manifest.py
```

验收：

```text
rough_cut.mp4 真实存在
final_delivery/rough_cut.mp4 真实存在
QA 和 delivery manifest final 通过
```

## E. 每个阶段的禁止事项

```text
禁止只改文档不改脚本却声称 provider 已接入。
禁止只有请求 JSON 没有 client 就声称已接入 GPT Image 2。
禁止只有 workflow 占位文件却声称 ComfyUI 已接入。
禁止把 placeholder 输出当成真实生成结果。
禁止跳过 run_all_tests.cmd。
```

## F. 下一轮建议任务

下一轮最合理的任务是：

```text
实现 provider_config.py + check_provider_health.py + openai_image_client.py 的第一版，
并把 Stage 05 的 keyframe image provider 从 placeholder 扩展为：
openai_image2 → comfyui_txt2img → manual/placeholder fallback。
```
