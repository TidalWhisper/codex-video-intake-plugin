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
provider 配置读取与健康检查
OpenAI GPT Image 2 图片生成 runner
ComfyUI core client 与 txt2img / LTX I2V / IndexTTS2 / Music runners
Stage 05-09 provider-backed 自动化测试与交付打包链路
后续 provider 接入文档和任务提示词
```

仍未完全闭环：

```text
本机真实 OpenAI / ComfyUI / FFmpeg 环境最终验收
稳定的真实 workflow_api.json 导出与节点映射沉淀
最小真实项目样例的仓库化基线
更完整的 provider fallback / failure recovery / retry hardening
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

当前已具备：

```text
config/providers.example.yaml
scripts/providers/provider_config.py
scripts/providers/check_provider_health.py
scripts/providers/check_provider_config.py
scripts/providers/check_openai_image_provider.py
scripts/providers/check_comfyui_server.py
```

验收：

```text
配置缺失时报明确错误
环境变量缺失时报明确错误
provider disabled 时不会被调用
run_all_tests.py 通过
```

### D2. GPT Image 2 / OpenAI Images Provider

当前已具备：

```text
scripts/providers/openai_image_client.py
scripts/providers/run_openai_gpt_image2.py
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

当前已具备：

```text
scripts/providers/comfyui_client.py
scripts/providers/check_comfyui_server.py
scripts/providers/run_comfyui_workflow.py
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

当前已具备：

```text
workflows/comfyui/txt2img_keyframe.workflow_api.json
scripts/providers/run_comfyui_txt2img.py
```

验收：

```text
OpenAI provider 失败或禁用时可切 ComfyUI
生成图片写入 keyframe_image_manifest.json
final validator 通过
```

### D5. Stage 06 LTX I2V

当前已具备：

```text
workflows/comfyui/i2v_ltx.workflow_api.json
scripts/providers/run_comfyui_ltx_i2v.py
```

验收：

```text
每个 shot 引用 Stage 05 start/end keyframe
生成 clips/*.mp4
video_clip_manifest.json final 通过
```

### D6. Stage 07 IndexTTS2 / Music

当前已具备：

```text
workflows/comfyui/indextts2.workflow_api.json
workflows/comfyui/HeartMuLa_workflow_fixed_importable.json
workflows/comfyui/AceStep_Music_Workflow.json
scripts/providers/run_comfyui_indextts2.py
scripts/providers/run_comfyui_music.py
```

验收：

```text
voice/*.wav 真实存在
music/*.wav 真实存在
audio_manifest.json final 通过
```

### D7. Stage 08/09 真实合成与交付强化

当前已具备基础真实链路：

```text
skills/video-assembly/scripts/assemble_with_ffmpeg.py
skills/video-qa-delivery/scripts/package_delivery.py
skills/video-qa-delivery/scripts/validate_qa_manifest.py
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
先校正文档与代码状态不一致的问题，
再执行本机真实环境前置检查与最小 Stage 05-09 冒烟验证，
最后针对验证结果补强 fallback、重试、失败证据和交付稳定性。
```
