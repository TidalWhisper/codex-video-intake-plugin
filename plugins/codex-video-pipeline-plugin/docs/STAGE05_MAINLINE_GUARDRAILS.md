# Stage 05 Mainline Guardrails

> 本文件只保留当前 Stage05 已锁定主线的执行约束。当前仓库删除了历史 Stage05 改造计划后，这份 guardrails 文件自身就是 Stage05 文档侧的直接约束来源。

## 1. 当前唯一主线

Stage 05 现在只允许按两段式主线执行：

1. `Stage05-A`：根据 `Stage03` 人物语义选择一条 Zimage workflow，生成主角色参考图并回填 `Stage03`
2. `Stage05-B`：固定使用 `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`，把主角色参考图和 `Stage04` 分镜 prompt 组装成 reference-guided 单镜头任务

## 2. 禁止项

未经用户明确要求，禁止：

- 恢复任何 Stage 05 bridge workflow、兼容桥、过渡双轨或旧 fallback
- 把 `Stage05-B` 改回 prompt-only 路线
- 把 Qwen NextScene 当成批量 16 宫格分镜器使用
- 绕开 `Stage03 / Stage04` 语义，直接临时拼一套脱离上下文的新 prompt
- 让脚本自行决定“跳过 Stage05-A 直接进入 Stage05-B”

## 3. Stage05-A 约束

- 只允许在三套锁定的 Zimage workflow 中选：
  - `amazing-z-photo_SAFETENSORS.json`
  - `amazing-z-image-a_SAFETENSORS.json`
  - `amazing-z-comics_SAFETENSORS.json`
- 路由选择必须服从 `Stage00 / Stage05` 已确认的风格路线
- 最终参考图必须回填到 `03_characters/reference_images/CHAR_001_primary.png`

## 4. Stage05-B 约束

- 固定 workflow mapping：`stage05_realistic_cinematic_qwen_edit_nextscene_local`
- 固定控制模式：`reference_guided`
- 固定主参考图：`03_characters/reference_images/CHAR_001_primary.png`
- 固定输入语义来源：`04_keyframes/keyframe_prompts.json`
- 固定交付目标：为 `Stage06` 提供人物一致性更强的分镜图，而不是普通 prompt-only 单帧图

## 5. 交付证据

声称 Stage 05 完成前，至少要有这些证据：

- `05_images/keyframe_image_manifest.json`
- `05_images/comfyui_image_requests.json`
- `05_images/keyframes/*.png`
- `validate_keyframe_image_manifest.py --mode final` 通过
- `Stage06` 消费契约明确来自 `reference_guided_storyboard`
