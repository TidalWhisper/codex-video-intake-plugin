# 本地 Codex CLI 对接 ComfyUI / GPT Image 2 执行手顺

## 0. 当前口径

- Stage 07 音乐主线：`comfyui_music` + `AceStep_Music_Workflow.json`
- 保留的 fallback：`local_music_library`
- 兼容保留的本地免费 ComfyUI 音乐 workflow：`HeartMuLa_workflow_fixed_importable.json`
- 已删除：所有收费背景音乐 workflow 和相关鉴权口径

## 1. 前置检查

先确认：

```cmd
python plugins/codex-video-pipeline-plugin/scripts/providers/check_local_real_e2e_prereqs.py --json
python plugins/codex-video-pipeline-plugin/scripts/providers/check_provider_health.py --json
```

重点看：

- `OPENAI_API_KEY` 是否存在
- `config/providers.yaml` 是否存在
- `config/workflow_node_mapping.yaml` 是否存在
- `127.0.0.1:8188` 是否可访问
- LTX / IndexTTS2 是否已加载
- 如果准备跑 HeartMuLa，再确认本机已加载对应节点

## 2. 当前建议的 workflow 文件

放到：

```text
plugins/codex-video-pipeline-plugin/workflows/comfyui/
```

当前建议保留：

```text
txt2img_keyframe.workflow_api.json
i2v_ltx.workflow_api.json
indextts2.workflow_api.json
HeartMuLa_workflow_fixed_importable.json
AceStep_Music_Workflow.json
```

## 3. 真实样本主线

样本目录：

```text
plugins/codex-video-pipeline-plugin/video_projects/real_smoke_20260528_stage0509/
```

当前最稳的实跑顺序：

1. Stage 05 图片
2. Stage 06 视频
3. Stage 07 语音
4. Stage 07 音乐优先走 AceStep
5. Stage 08 FFmpeg 粗剪
6. Stage 09 final delivery

## 4. 音乐 workflow 口径

- `run_comfyui_music.py` 默认 `music_generation` 已映射到 AceStep
- 需要高质量提示词时，先用 `$acestep-prompt-builder`
- HeartMuLa 仍可通过 `music_generation_heartmula` 单独测试
- 真要测时，优先缩短时长并单独跑 Stage 07

## 5. 当前已知限制

- `ready_for_real_local_e2e: true` 可以在本地音乐库 fallback 模式下成立
- `provider_backed_stage07_music_ready: true` 只表示当前映射到的本地音乐 workflow 真的可跑
- 当前仓库已经不再保留收费背景音乐链路，所以后续新增音乐能力时只接免费本地路线
