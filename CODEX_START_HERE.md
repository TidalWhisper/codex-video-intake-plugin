# CODEX_START_HERE.md

这是当前仓库的根入口文档。

## 仓库定位

外层 `codex-video-intake-plugin/` 是安装包和本地 marketplace wrapper。
真正的插件本体在：

```text
plugins/codex-video-pipeline-plugin/
```

后续所有插件开发、排查和文档修订，都应以这个插件本体目录为准。

## 当前建议先读

```text
1. .codex/current-task-contract.md
2. plugins/codex-video-pipeline-plugin/CODEX_START_HERE.md
3. plugins/codex-video-pipeline-plugin/docs/PROVIDER_INTEGRATION_CONTRACTS.md
4. plugins/codex-video-pipeline-plugin/docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md
5. plugins/codex-video-pipeline-plugin/docs/CODEX_LOCAL_TASK_RUNBOOK.md
6. plugins/codex-video-pipeline-plugin/docs/STAGE00_STAGE02_ARCHITECTURE_CONTRACT.md
7. plugins/codex-video-pipeline-plugin/docs/STAGE05_MAINLINE_GUARDRAILS.md
```

## 当前执行原则

```text
1. 官方用户入口仍然只有 $video-production-pipeline。
2. 真实插件代码、技能、workflow、docs 都以 plugins/codex-video-pipeline-plugin/ 为准。
3. 已删除的历史计划/反馈文档不要重新当作权威依据。
4. .codex/full-batch-implementation-plan.md 和 .codex/supervisor-audit-log.md 只作历史背景，不是启动必读入口。
5. 日常针对性验证可以按需执行；如果要验证完整业务链路，优先从 $video-production-pipeline 正常入口开始。
6. 继续保持“Codex 主导语义与决策，Python 仅机械执行”的主线。
```

## 正常使用入口

```text
$video-production-pipeline
```
