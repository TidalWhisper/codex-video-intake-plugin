# 任务：实现 Stage 05 OpenAI GPT Image 2 Provider

目标：给 Stage 05 关键帧图片生成增加真实 OpenAI 图片 provider。

必须新增或修改：

- `scripts/providers/openai_image_client.py`
- `scripts/providers/run_openai_gpt_image2.py`
- `config/providers.example.yaml`
- Stage 05 相关 SKILL.md
- Stage 05 相关 tests

要求：

1. 从 `04_keyframes/keyframe_prompts.json` 读取图片任务。
2. 生成或读取 `05_images/openai_image_requests.json`。
3. 使用环境变量 `OPENAI_API_KEY`。
4. 模型名从配置读取，默认 `gpt-image-2`。
5. 输出图片到 `05_images/keyframes/`。
6. 更新 `keyframe_image_manifest.json`。
7. final validator 必须通过。
8. 如果 API 调用失败，写入 errors，不允许伪造图片。

不要实现 ComfyUI fallback，本任务只做 OpenAI image provider。
