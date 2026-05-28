# 包内容说明

固定 zip 包名：`codex-video-intake-plugin.zip`

包内版本：1.1.2

## 重要修正

本版已改成扁平 plugin-root 结构，解决旧版中：

```text
codex-video-intake-plugin/plugins/codex-video-intake-plugin/
```

这种重复命名、容易误导的目录结构。

新版结构：

```text
codex-video-intake-plugin/
├─ .codex-plugin/plugin.json
├─ .agents/plugins/marketplace.json
├─ skills/
├─ docs/
├─ config/
├─ workflows/
├─ templates/
├─ tests/
├─ install_personal_plugin.cmd
├─ verify_package.cmd
└─ run_all_tests.cmd
```

## 核心能力

- Stage 00-09 视频生产流程框架
- 项目独立目录归档
- 各阶段 manifest / validator / placeholder 测试脚本
- QA 与交付框架
- 后续 GPT Image 2 / ComfyUI / LTX / IndexTTS2 接入计划

## 重要状态

当前包还没有真实调用 GPT Image 2 或 ComfyUI。
它提供的是后续本地 Codex CLI 对接所需的详细计划、任务提示词、配置模板和验收标准。
