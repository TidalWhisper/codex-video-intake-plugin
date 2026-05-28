# Codex 总任务：接入 GPT Image 2 与 ComfyUI 真实 Provider

你正在修改 `codex-video-intake-plugin`。

请先阅读：

- `docs/CURRENT_PROVIDER_STATUS.md`
- `docs/DEVELOPMENT_PLAN_COMFYUI_AND_OPENAI_IMAGE.md`
- `docs/PROVIDER_INTEGRATION_CONTRACTS.md`
- `docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md`

目标：把 Stage 05-07 从 placeholder 框架升级为真实 provider 调用。

硬规则：

1. 不允许破坏 Stage 00-09 现有结构。
2. 不允许跳过 manifest。
3. 不允许没有真实文件就写 success。
4. 不允许把 API key 写入仓库。
5. ComfyUI 节点 ID 必须走 `config/workflow_node_mapping.yaml`。
6. 每次改完必须运行 `run_all_tests.cmd`。

先做 v1.2.0：Provider 配置与健康检查。不要一上来写所有功能。
