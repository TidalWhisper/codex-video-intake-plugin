# CHANGELOG

## Unreleased

- 清理并收口根入口文档、插件入口文档和当前任务契约，使其反映当前真实插件结构。
- 将历史批次计划和监督日志降级为归档背景，不再作为启动必读入口。
- 同步 Stage00-Stage02 文档里关于 `repo_change_gate.py` 的说明，避免继续误写成慢速全套回归 gate。

## 1.1.3

- 修正目录结构，避免 `codex-video-intake-plugin/plugins/codex-video-intake-plugin` 套娃式重名。
- 外层目录保留固定包名 `codex-video-intake-plugin/`。
- 内层真正插件目录改为 `plugins/codex-video-pipeline-plugin/`。
- 插件显示名改为 `Codex Video Pipeline`。
- 更新 install_personal_plugin.cmd / verify_package.cmd / run_all_tests.py 以适配新结构。
