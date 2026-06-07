# CHANGELOG

## 1.1.3

- 修正目录结构，避免 `codex-video-intake-plugin/plugins/codex-video-intake-plugin` 套娃式重名。
- 外层目录保留固定包名 `codex-video-intake-plugin/`。
- 内层真正插件目录改为 `plugins/codex-video-pipeline-plugin/`。
- 插件显示名改为 `Codex Video Pipeline`。
- 更新 install_personal_plugin.cmd / verify_package.cmd / run_all_tests.py 以适配新结构。
- 保留 Stage 00-09 全部流程框架与后续 GPT Image 2 / ComfyUI 开发计划。

## 1.1.4

- 删除历史计划、进度、反馈类文档，不再把它们作为当前实现依据。
- 重建仓库级 `.codex/current-task-contract.md` 作为唯一权威上下文。
- 收紧入口规则：测试仅允许由监督者 Agent 从 `$video-production-pipeline` 入口执行。
