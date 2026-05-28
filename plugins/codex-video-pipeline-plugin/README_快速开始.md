# Codex Video Pipeline Plugin

当前插件版本：1.1.3

## 插件本体目录

如果你正在阅读这个文件，当前目录就是插件本体：

```text
plugins/codex-video-pipeline-plugin/
├─ .codex-plugin/
├─ skills/
├─ docs/
├─ config/
├─ workflows/
├─ templates/
└─ tests/
```

外层 `codex-video-intake-plugin/` 是本地安装包 / marketplace wrapper，不是真正的插件本体。

## 推荐入口

```text
$video-production-pipeline
```

## 当前状态

已包含 Stage 00-09 流程框架、manifest、validator、placeholder 测试与后续 provider 接入计划。

尚未真实接入：

```text
GPT Image 2 / OpenAI Images API
ComfyUI txt2img
ComfyUI LTX I2V
IndexTTS2 / ComfyUI 音频工作流
```

后续开发请先读：

```text
CODEX_START_HERE.md
docs/00_CODEX_MASTER_PLAN.md
```
