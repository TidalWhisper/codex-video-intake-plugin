# 任务：实现 ComfyUI Core Client

目标：新增通用 ComfyUI API client，供 Stage 05/06/07 使用。

必须新增：

- `scripts/providers/comfyui_client.py`
- `scripts/providers/check_comfyui_server.py`
- tests

功能：

1. 检查 `GET /system_stats` 或等效健康接口。
2. 提交 `POST /prompt`。
3. 获取 prompt_id。
4. 轮询 `/history/{prompt_id}`。
5. 解析输出文件。
6. 失败时返回结构化错误。

禁止：

- 禁止在 client 中写死某个 workflow 的节点 ID。
- 禁止吞掉 ComfyUI 错误。
