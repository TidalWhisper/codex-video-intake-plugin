# CODEX_START_HERE.md

> 这是插件本体目录的当前入口文档。这里描述的是“现在真实存在的插件结构和主线”，不是历史批次过程记录。

## 1. 当前插件定位

当前插件是：

```text
Codex CLI 专用的视频生产流水线插件
+ Stage 00-09 流程框架
+ manifest / validator / creator-facing 状态面
+ provider 配置与运行脚手架
+ Stage05 reference-guided 主线
+ Stage06 / Stage07 显式确认与继续执行入口
```

当前总方向仍然是：

```text
Codex 主导语义与决策
Python 仅机械执行
```

## 2. 当前建议先读

```text
1. ../../.codex/current-task-contract.md
2. docs/PROVIDER_INTEGRATION_CONTRACTS.md
3. docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md
4. docs/CODEX_LOCAL_TASK_RUNBOOK.md
5. docs/STAGE00_STAGE02_ARCHITECTURE_CONTRACT.md
6. docs/STAGE05_MAINLINE_GUARDRAILS.md
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

这些子 skill 只用于恢复、调试、单阶段重跑或开发排查。

## 4. 当前稳定事实

```text
1. Stage00-Stage04 的正式链路已经落在官方入口与对应 stage runner 上。
2. Stage05 当前主线是 reference-guided keyframe image 生成，不再以 prompt-only 路线为默认主线。
3. creator_home / reference_image_start_here / stage05_start_here 这类 creator-facing 恢复入口已经是当前真实产物面。
4. workflows/comfyui/ 下已经内置仓库当前使用的 workflow JSON，不应再写成“仓库不内置 workflow”。
5. 日常针对性验证可以按需执行；完整业务链路验证优先从 $video-production-pipeline 入口开始。
```
