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

如果你想直接查看“当前项目卡在哪、下一步该点哪里”，可以运行：

```bash
python skills/video-production-pipeline/scripts/show_creator_home.py
```

它会自动同步最新项目状态，并给出：

- `creator_home.html`：普通创作者主页
- `reference_image_start_here.md`：角色参考图补齐入口
- `stage05_review_workbench.html`：Stage 05 默认审图工作台

## 当前状态

已包含：

- Stage 00-09 流程框架
- manifest / validator
- provider 配置与健康检查
- OpenAI GPT Image 2 图片生成 runner
- ComfyUI txt2img / LTX I2V / IndexTTS2 / Music runners
- Stage 05 → Stage 09 provider-backed 自动化测试

当前仍有本机依赖，但已完成一次最小真实样本冒烟：

```text
仓库内不内置可直接复用的真实 ComfyUI workflow_api.json
config/providers.yaml 与 config/workflow_node_mapping.yaml 仍需本机配置
2026-05-28 已在 video_projects/real_smoke_20260528_stage0509/ 跑通一条真实 Stage 05-09 样本链路
Stage 07 默认 ComfyUI 音乐 workflow 已切到 AceStep，当前机器仍保留 local_music_library fallback
```

后续开发请先读：

```text
CODEX_START_HERE.md
../../.codex/current-task-contract.md
```
