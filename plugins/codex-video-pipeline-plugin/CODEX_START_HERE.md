# CODEX_START_HERE.md

> 这是插件本体目录的当前入口文档。当前主线规则、批次目标和测试约束统一以仓库级 `.codex/current-task-contract.md` 为准。

## 1. 当前插件定位

当前插件是：

```text
Codex CLI 专用的视频生产流水线插件
+ Stage 00-09 流程框架
+ 状态机
+ 每阶段 manifest / validator
+ provider 配置与运行脚手架
```

当前改造目标不是“补旧计划”，而是：

```text
把 Stage00-Stage09 改造成 Codex 主导语义与决策，Python 仅机械执行。
```

## 2. 当前应先读取的文件

```text
1. ../../.codex/current-task-contract.md
2. CODEX_START_HERE.md
3. docs/PROVIDER_INTEGRATION_CONTRACTS.md
4. docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md
5. docs/CODEX_LOCAL_TASK_RUNBOOK.md
6. docs/STAGE00_STAGE02_ARCHITECTURE_CONTRACT.md
7. docs/STAGE05_MAINLINE_GUARDRAILS.md
```

## 3. 当前唯一官方用户入口

```text
$video-production-pipeline
```

不要把下列子 skill 当成正常用户入口：

```text
$video-project-intake
$video-script-generation
$video-storyboard-generation
$video-character-bible
$video-keyframe-prompts
$video-keyframe-images
$video-video-clips
$video-audio
$video-assembly
$video-qa-delivery
```

这些子 skill 只用于恢复、调试、单阶段重跑。

## 4. 当前硬规则

```text
1. 不允许再引用仓库中已删除的历史 codex-first 计划或进度文档。
2. 不允许口头声称“已完成”；必须以后续审计和正式 evidence 为准。
3. 主实施者不做任何测试。
4. 唯一允许的测试由监督者 Agent 从 $video-production-pipeline 入口执行。
5. 不允许用兼容桥、旧 fallback、旧本地语义路径继续挂旧主线。
```
