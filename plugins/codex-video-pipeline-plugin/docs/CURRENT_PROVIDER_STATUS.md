# 当前 Provider 接入状态

包内版本：1.1.3

## 结论

当前插件已经具备从 Stage 05 到 Stage 09 的真实落盘、manifest 回写、自动化测试和最终交付能力。

当前仓库对 Stage 07 音乐的口径已经收回到本地免费路线：

- 主线：`comfyui_music` + `AceStep_Music_Workflow.json`
- 保留的本地 fallback：`local_music_library`
- 兼容保留的本地 ComfyUI 音乐入口：`HeartMuLa_workflow_fixed_importable.json`
- 已删除：所有收费背景音乐 workflow、映射、鉴权说明和相关测试

## 已接入能力

- Stage 05
  - OpenAI GPT Image 2
  - ComfyUI txt2img fallback with 4 style-family routes:
    - `txt2img_keyframe_realistic`
    - `txt2img_keyframe_anime`
    - `txt2img_keyframe_guofeng`
    - `txt2img_keyframe_stylized`
- Stage 06
  - ComfyUI LTX I2V
- Stage 07
  - ComfyUI IndexTTS2
  - ComfyUI Music runner
  - AceStep prompt 构造与注入
  - HeartMuLa prompt 构造与注入
  - `local_music_library` fallback
- Stage 08 / Stage 09
  - FFmpeg 合成
  - QA manifest
  - final delivery 打包

## 当前限制

- 仓库仍然不内置你本机可直接运行的 ComfyUI API workflow，需要你本地导出后放进 `workflows/comfyui/`
- `config/providers.yaml` 和 `config/workflow_node_mapping.yaml` 仍然需要本地填写
- AceStep 现在是默认 ComfyUI 音乐入口，但仍依赖本机真实节点、模型和工作流
- Stage 05 四路 workflow 目前是最小 starter 版本，仓库内置的是路由与文件位，不保证单一底模天然覆盖所有风格
- `local_music_library` 仍可作为兜底路径

## 当前建议

1. Stage 07 默认音乐 workflow 走 AceStep，统一通过 `music_generation`
2. 需要更高质量提示词时，先走 `$acestep-prompt-builder`
3. `local_music_library` 和 `music_generation_heartmula` 保留为 fallback / 兼容路径
4. Stage 05 本地 ComfyUI 建议按 `realistic / anime / guofeng / stylized` 分别维护独立 workflow，而不是要求单一 workflow 覆盖所有预设风格
