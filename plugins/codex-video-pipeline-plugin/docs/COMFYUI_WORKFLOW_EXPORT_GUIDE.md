# ComfyUI 工作流导出与接入指南

## 一、为什么不能直接内置真实工作流

ComfyUI 工作流强依赖用户本机环境：

- 已安装哪些 custom nodes
- 模型文件放在哪个目录
- 节点 ID 是否变化
- LTX / LTXVideo / IndexTTS2 节点版本
- 图片、音频、视频输出节点名称

因此插件 1.1.2 不直接声称包含可用工作流，而是提供接入计划和映射模板。

## 二、导出 API 格式 workflow

在 ComfyUI 中：

1. 打开一个已经能手动运行成功的工作流。
2. 确认至少成功生成一次结果。
3. 打开开发者/设置中的 API workflow 导出功能。
4. 导出 API 格式 JSON。
5. 放入：

```text
workflows/comfyui/txt2img_keyframe.workflow_api.json
workflows/comfyui/i2v_ltx.workflow_api.json
workflows/comfyui/indextts2.workflow_api.json
workflows/comfyui/music_generation.workflow_api.json
```

## 三、节点映射

不要把节点 ID 写死到代码里。应写入：

```text
config/workflow_node_mapping.yaml
```

示例：

```yaml
txt2img_keyframe:
  positive_prompt_node: "6"
  positive_prompt_input: "text"
  negative_prompt_node: "7"
  negative_prompt_input: "text"
  seed_node: "3"
  seed_input: "seed"
  width_node: "5"
  width_input: "width"
  height_node: "5"
  height_input: "height"
  output_node: "9"
```

## 四、对接顺序

建议按这个顺序：

1. 先接 `check_comfyui_server.py`。
2. 再接最简单的 txt2img。
3. 再接 LTX I2V。
4. 再接 IndexTTS2。
5. 最后接音乐生成。

## 五、成功标准

每个工作流接入后，必须能做到：

- 从 manifest 读取任务。
- 修改 workflow API JSON。
- POST `/prompt`。
- 拿到 prompt_id。
- 轮询 history。
- 找到输出文件。
- 复制到项目目录。
- 更新 manifest。
- final validator 通过。
