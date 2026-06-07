# CODEX_START_HERE.md

这是当前仓库的总入口文档。

## 仓库定位

外层 `codex-video-intake-plugin/` 是安装包和本地 marketplace wrapper。
真正的插件本体在：

```text
plugins/codex-video-pipeline-plugin/
```

后续所有开发都围绕这个插件本体目录进行。

## 当前唯一权威上下文

先读这些文件，不要再读取已删除的历史改造计划、进度文档或试跑反馈：

```text
1. .codex/current-task-contract.md
2. plugins/codex-video-pipeline-plugin/CODEX_START_HERE.md
3. plugins/codex-video-pipeline-plugin/docs/PROVIDER_INTEGRATION_CONTRACTS.md
4. plugins/codex-video-pipeline-plugin/docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md
5. plugins/codex-video-pipeline-plugin/docs/CODEX_LOCAL_TASK_RUNBOOK.md
6. plugins/codex-video-pipeline-plugin/docs/STAGE00_STAGE02_ARCHITECTURE_CONTRACT.md
7. plugins/codex-video-pipeline-plugin/docs/STAGE05_MAINLINE_GUARDRAILS.md
```

## 当前开发规则

```text
1. 官方用户入口只有 $video-production-pipeline。
2. Stage00-Stage09 的当前改造目标是：Codex 主导语义与决策，Python 仅机械执行。
3. 不允许再引用仓库中已删除的历史 codex-first 计划或进度文档。
4. 主实施者不做任何测试。
5. 唯一允许的测试由监督者 Agent 执行，且只能从 $video-production-pipeline 入口开始。
```

## 正常使用入口

```text
$video-production-pipeline
```
