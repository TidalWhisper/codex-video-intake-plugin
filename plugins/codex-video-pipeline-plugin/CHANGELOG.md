# CHANGELOG

## Unreleased

- 对入口文档、任务契约和 README 做了现状对齐，移除会误导后续改造的旧测试/批次口径。
- 把 `repo_change_gate.py` 的文档口径同步为当前真实行为：只拦截临时/生成垃圾文件。
- 修复上一版 changelog 中误混入补丁文本的问题。

## 1.1.3

- 修正目录结构，避免 `codex-video-intake-plugin/plugins/codex-video-intake-plugin` 套娃式重名。
- 外层目录保留固定包名 `codex-video-intake-plugin/`。
- 内层真正插件目录改为 `plugins/codex-video-pipeline-plugin/`。
- 插件显示名改为 `Codex Video Pipeline`。
- 更新 install_personal_plugin.cmd / verify_package.cmd / run_all_tests.py 以适配新结构。
