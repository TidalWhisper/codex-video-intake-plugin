# ComfyUI workflow 放置目录

仓库当前只保留本地免费路线相关的 workflow 约定，不再保留任何收费背景音乐 workflow。

建议放置的 API workflow 文件：

```text
txt2img_keyframe.workflow_api.json
txt2img_keyframe_realistic.workflow_api.json
txt2img_keyframe_anime.workflow_api.json
txt2img_keyframe_guofeng.workflow_api.json
txt2img_keyframe_stylized.workflow_api.json
i2v_ltx.workflow_api.json
indextts2.workflow_api.json
HeartMuLa_workflow_fixed_importable.json
AceStep_Music_Workflow.json
```

注意：

- 必须是 ComfyUI 导出的 API 格式 workflow，不是普通 UI workflow
- Stage 05 txt2img 现在推荐使用四路最小架构：`realistic / anime / guofeng / stylized`
- `txt2img_keyframe.workflow_api.json` 仍保留为兼容入口；默认 runner 会根据 Stage 05 manifest 自动路由到四个 style-family workflow
- 维护 Stage 05 风格路由时，先看 `config/stage05_style_profiles.example.yaml`，不要把同一个通用底模仅靠 prompt 改名后当成多个成熟风格路线
- 当前本机已验证的 Stage 05 模型栈：
  - `realistic` → `Qwen 2512` 基础栈
  - `anime` → `Zimage` 基础栈
  - `guofeng` → `Qwen 2512 + qwen_image_gufeng LoRA`
  - `stylized` → `Qwen 2512 + illustration-1.0-qwen-image LoRA`
- Stage 07 默认 ComfyUI 音乐 workflow 入口已切到 `AceStep_Music_Workflow.json`
- `run_comfyui_music.py` 的默认 `music_generation` 映射现在指向 AceStep
- `music_generation_heartmula` 仍保留给 HeartMuLa 兼容路径

各 runner 当前需要的可写输入：

- `run_comfyui_txt2img.py`
  - `positive_prompt`
  - `negative_prompt`
  - `seed`
  - `width`
  - `height`
- `run_comfyui_ltx_i2v.py`
  - `start_image`
  - `positive_prompt`
  - `negative_prompt`
  - `seed`
  - `frame_count`
  - `fps`
  - `width`
  - `height`
- `run_comfyui_indextts2.py`
  - `text`
  - `speaker_reference`
  - `emotion`
- `run_comfyui_music.py`
  - `tags`
  - `lyrics`
  - `seed`
  - `duration`
  - `latent seconds`
  - `bpm`
  - `language`
  - `keyscale`
  - `timesignature`
