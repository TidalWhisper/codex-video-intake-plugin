# 任务：接入 Stage 05 ComfyUI txt2img fallback

前置：ComfyUI core client 已完成。

目标：OpenAI 图片 provider 不可用时，使用 ComfyUI txt2img 生成关键帧图片。

必须新增：

- `scripts/providers/run_comfyui_txt2img.py`
- `workflows/comfyui/txt2img_keyframe.workflow_api.json` 的接入说明
- `config/workflow_node_mapping.example.yaml` 对应节点映射

要求：

1. 从 `keyframe_prompts.json` 读取 prompt。
2. 读取 `workflow_node_mapping.yaml`。
3. 替换 positive prompt、negative prompt、seed、width、height。
4. 提交 ComfyUI。
5. 收集输出图片。
6. 写入 `keyframe_image_manifest.json`。
7. final validator 通过。
