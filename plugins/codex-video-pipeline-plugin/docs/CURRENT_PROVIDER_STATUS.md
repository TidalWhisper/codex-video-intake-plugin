# 当前 Provider 接入状态

包内版本：1.1.2

## 结论

当前插件已经包含 Stage 00-09 的流程框架、状态机、manifest、validator、placeholder 测试脚本和交付检查。

但当前包**还没有真正实现**以下真实后端调用：

- OpenAI GPT Image 2 图片生成
- ComfyUI 文生图 / 图生图工作流调用
- ComfyUI LTX / LTXVideo 图生视频工作流调用
- ComfyUI IndexTTS2 工作流调用
- ComfyUI 音乐生成工作流调用

## 当前 Stage 05 的真实状态

Stage 05 已经具备：

- `image_generation_jobs.json` 计划文件
- `keyframe_image_manifest.json` 结果清单
- `openai_image_requests.json` 请求清单结构
- `comfyui_image_requests.json` 请求清单结构
- placeholder 图片生成脚本
- final validator：要求图片真实存在且文件大小大于 0

但 Stage 05 目前**没有**：

- `openai_image_client.py`
- `run_openai_gpt_image2.py`
- `comfyui_client.py`
- `run_comfyui_txt2img.py`
- 可导入 ComfyUI 的真实 `workflow_api.json`

因此当前包不能声称“已经可以调用 GPT Image 2 生成图”。

## 后续目标

下一轮由本地 Codex CLI 完成真实 provider 接入时，必须满足：

1. 能检查 provider 配置。
2. 能真正调用 OpenAI Images API 或 ComfyUI API。
3. 能把真实输出文件写入项目目录。
4. 能回写 manifest。
5. final validator 能通过。
6. 失败时写入错误证据，不能口头假装成功。
