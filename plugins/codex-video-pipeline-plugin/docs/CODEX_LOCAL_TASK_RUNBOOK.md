# 本地 Codex CLI 对接 ComfyUI / GPT Image 2 执行手顺

## 0. 准备

先确认你已经能在 Codex CLI 中识别插件：

```text
$video-production-pipeline
```

再确认本地测试：

```cmd
run_all_tests.cmd
```

## 1. 第一轮任务：Provider 配置

喂给 Codex：

```text
请阅读 docs/CURRENT_PROVIDER_STATUS.md、docs/DEVELOPMENT_PLAN_COMFYUI_AND_OPENAI_IMAGE.md、docs/PROVIDER_INTEGRATION_CONTRACTS.md，然后先实现 v1.2.0 Provider 配置与健康检查，不要实现真实生成。
```

验收：

```cmd
run_all_tests.cmd
```

## 2. 第二轮任务：GPT Image 2 图片生成

喂给 Codex：

```text
请执行 prompts/codex/01-implement-openai-image2-provider.md，只做 Stage 05 OpenAI 图片 provider，保持 ComfyUI fallback 不动。
```

验收：

- 能生成 `05_images/keyframes/*.png`
- 能更新 `keyframe_image_manifest.json`
- final validator 通过

## 3. 第三轮任务：ComfyUI txt2img fallback

喂给 Codex：

```text
请执行 prompts/codex/02-implement-comfyui-core-client.md 和 prompts/codex/03-integrate-stage05-keyframe-images.md，接入本机导出的 txt2img workflow_api.json。
```

## 4. 第四轮任务：LTX I2V

喂给 Codex：

```text
请执行 prompts/codex/04-integrate-stage06-ltx-i2v.md，接入本机 ComfyUI LTX 图生视频工作流。
```

## 5. 第五轮任务：IndexTTS2 和音乐

喂给 Codex：

```text
请执行 prompts/codex/05-integrate-stage07-indextts2-music.md，接入本机 IndexTTS2 与音乐生成或本地音乐库。
```

## 6. 每轮都必须要求 Codex 输出

- 修改了哪些文件
- 新增了哪些文件
- 如何运行
- 如何验证
- 失败日志在哪里
- manifest 中的证据是什么
