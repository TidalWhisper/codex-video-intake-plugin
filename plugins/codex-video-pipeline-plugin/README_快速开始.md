# Codex Video Pipeline Plugin

当前插件版本：1.1.3

## 插件本体目录

如果你正在阅读这个文件，当前目录就是插件本体：

```text
plugins/codex-video-pipeline-plugin/
├─ .codex-plugin/
├─ docs/
├─ prompts/
├─ scripts/
├─ skills/
├─ tests/
└─ workflows/
```

外层 `codex-video-intake-plugin/` 是安装包 / marketplace wrapper，不是真正的插件本体。

## 推荐入口

```text
$video-production-pipeline
```

## 当前插件真实能力

当前仓库已经包含：

- Stage 00-09 流程框架
- manifest / validator / project_state / creator-facing 状态产物
- Stage00-Stage04 正式 stage runner
- Stage05 reference-guided keyframe image 主线
- Stage06 / Stage07 显式确认与继续执行脚本
- provider 配置与健康检查脚手架
- OpenAI GPT Image 2 / ComfyUI txt2img / LTX I2V / IndexTTS2 / Music runners
- `workflows/comfyui/` 下的仓库内置 workflow JSON

## 当前本地依赖边界

仓库虽然已经内置 workflow 文件和运行脚手架，但本机仍需要准备：

- `config/providers.yaml`
- `config/workflow_node_mapping.yaml`
- 可访问的本地 ComfyUI
- 对应模型、节点和工作流运行环境

## creator-facing 恢复入口

如果你想直接看“当前项目卡在哪、下一步该点哪里”，可以运行：

```bash
python skills/video-production-pipeline/scripts/show_creator_home.py
```

它会同步当前项目状态，并输出这些恢复面：

- `creator_home.html`
- `03_characters/reference_image_start_here.md`
- `04_keyframes/stage05_start_here.md`
- `05_images/stage05_review_workbench.html`

## 继续开发前建议先读

```text
../../.codex/current-task-contract.md
CODEX_START_HERE.md
docs/PROVIDER_INTEGRATION_CONTRACTS.md
docs/CODEX_LOCAL_TASK_RUNBOOK.md
docs/STAGE00_STAGE02_ARCHITECTURE_CONTRACT.md
docs/STAGE05_MAINLINE_GUARDRAILS.md
```
