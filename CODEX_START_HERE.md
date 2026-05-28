# CODEX_START_HERE.md

这是给本地 Codex CLI 的总入口文档。

## 目录说明

外层 `codex-video-intake-plugin/` 是安装包和本地 marketplace wrapper。
真正的插件本体在：

```text
plugins/codex-video-pipeline-plugin/
```

后续所有开发都应围绕这个插件本体目录进行。

## 给 Codex CLI 的第一条指令

```text
你现在接手 codex-video-intake-plugin。请先读取以下文档，不要立刻修改代码：

1. CODEX_START_HERE.md
2. plugins/codex-video-pipeline-plugin/CODEX_START_HERE.md
3. plugins/codex-video-pipeline-plugin/docs/00_CODEX_MASTER_PLAN.md
4. plugins/codex-video-pipeline-plugin/docs/CURRENT_PROVIDER_STATUS.md
5. plugins/codex-video-pipeline-plugin/docs/DEVELOPMENT_PLAN_COMFYUI_AND_OPENAI_IMAGE.md
6. plugins/codex-video-pipeline-plugin/docs/PROVIDER_INTEGRATION_CONTRACTS.md
7. plugins/codex-video-pipeline-plugin/docs/COMFYUI_WORKFLOW_EXPORT_GUIDE.md
8. plugins/codex-video-pipeline-plugin/docs/CODEX_LOCAL_TASK_RUNBOOK.md

读完后，先告诉我：
1. 当前插件完成到哪个阶段
2. 哪些功能只是框架/placeholder
3. 哪些功能还没有真实接入
4. 下一步你准备修改哪些文件
5. 你准备执行哪些测试

在我确认之前，不要修改代码。
```

## 当前状态

已完成 Stage 00-09 的流程框架、状态机、manifest、validator、placeholder 测试和交付结构。

尚未真实接入：

```text
GPT Image 2 / OpenAI Images API
ComfyUI txt2img
ComfyUI LTX I2V
IndexTTS2 / ComfyUI 音频工作流
真实生产级 FFmpeg 参数
```

## 正常使用入口

```text
$video-production-pipeline
```

## 本机自检

```cmd
cd /d E:\Codex-Plugin\codex-video-intake-plugin
run_all_tests.cmd
```
