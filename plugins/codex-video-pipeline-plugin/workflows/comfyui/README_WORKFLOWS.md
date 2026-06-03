# ComfyUI workflow 放置目录

仓库当前只保留本地免费路线相关的 workflow 约定，不再保留任何收费背景音乐 workflow。

建议放置的 API workflow 文件：

```text
txt2img_keyframe.workflow_api.json
txt2img_keyframe_realistic.workflow_api.json
txt2img_keyframe_realistic_zimage_photo_bridge.workflow_api.json
txt2img_keyframe_anime.workflow_api.json
txt2img_keyframe_anime_cn_newguofeng.workflow_api.json
txt2img_keyframe_guofeng.workflow_api.json
txt2img_keyframe_guofeng_ink.workflow_api.json
txt2img_keyframe_stylized.workflow_api.json
txt2img_keyframe_stylized_concept.workflow_api.json
txt2img_keyframe_stylized_zimage_image_b_bridge.workflow_api.json
i2v_ltx.workflow_api.json
indextts2.workflow_api.json
HeartMuLa_workflow_fixed_importable.json
AceStep_Music_Workflow.json
```

注意：

- 必须是 ComfyUI 导出的 API 格式 workflow，不是普通 UI workflow
- Stage 05 txt2img 的 provider 顺序固定为：`OpenAI GPT Image 2 -> ComfyUI -> manual`
- Stage 05 的真正路由入口已经切到 `config/stage05_route_registry.example.yaml`
- `txt2img_keyframe.workflow_api.json` 仍保留为兼容入口；默认 runner 会根据 Stage 05 manifest 先解析 `route_key`，再路由到对应 workflow
- 第一批 route-specific workflow 已拆出独立文件：
  - `anime_cn_newguofeng`
  - `guofeng_ink`
  - `stylized_concept`
- 这三条现在也补了可直接指定的 mapping key：
  - `txt2img_keyframe_anime_cn_newguofeng`
  - `txt2img_keyframe_guofeng_ink`
  - `txt2img_keyframe_stylized_concept`
- 维护 Stage 05 风格路由时，先看 `config/stage05_route_registry.example.yaml`，不要把同一个通用底模仅靠 prompt 改名后当成多个成熟风格路线
- route registry 里的 `adoption_strategy` / `evidence_refs` 用来记录每条路线当前桥接实现、社区优先候选、以及外部证据来源
- 当前本机已验证的 Stage 05 模型栈：
  - `realistic` → `Qwen 2512` 基础栈
  - `anime` → `Zimage` 基础栈
  - `guofeng` → `Qwen 2512 + qwen_image_gufeng LoRA`
  - `stylized` → `Qwen 2512 + illustration-1.0-qwen-image LoRA`
- 当前第一批 route-specific workflow 试点：
  - `realistic_zimage_photo_bridge` → `Z-Image photo` 社区 UI graph 的最小 API bridge，使用 `z_image_turbo_bf16.safetensors + qwen_3_4b.safetensors + ae.safetensors`
  - `anime_cn_newguofeng` → `Neta-Lumina` 风格 API 结构，使用 `neta-lumina-v1.0.safetensors + gemma_2_2b_fp16 + ae.safetensors`
  - `guofeng_ink` → `Qwen 2512 + qwen_image_gufeng LoRA` 独立工作流文件，并额外暴露 `style_anchor / negative_style_anchor` 节点给 Stage 05 route/preset 层
  - `stylized_concept` → `Z-Image image-b` 社区 UI graph 的最小 API bridge，使用 `z_image_turbo_bf16.safetensors + qwen_3_4b.safetensors + ae.safetensors`
- `scripts/providers/build_stage05_zimage_photo_bridge.py` 用来把 `AmazingZImageWorkflow/amazing-z-photo_SAFETENSORS.json` 裁成 Stage 05 可 patch 的 API bridge
- `scripts/providers/build_stage05_zimage_image_b_bridge.py` 用来把 `AmazingZImageWorkflow/amazing-z-image-b_SAFETENSORS.json` 裁成 Stage 05 可 patch 的 API bridge
- 这些 repo 内 route-specific workflow 仍然只是过渡桥接，并不自动等于“社区最佳版”
- `realistic_cinematic` 当前默认 prompt-only 已切到 `Qwen 2512` 原生路线：`txt2img_keyframe_realistic.workflow_api.json`
- `realistic_cinematic` 的 `Z-Image photo bridge` 仍保留为社区桥接比较候选：`txt2img_keyframe_realistic_zimage_photo_bridge.workflow_api.json`
- `stylized_concept` 当前已经切到仓库内 bridge：`txt2img_keyframe_stylized_zimage_image_b_bridge.workflow_api.json`
- `stylized_concept` 已有本地 smoke evidence：`video_projects/real_smoke_20260530_stage05_stylized_bridge/05_images/keyframe_image_manifest.json`
- `stylized_concept` 现在还支持 route-internal preset anchor：
  - `cyberpunk_neon`
  - `dark_fantasy_noir`
  - `chromatic_editorial`
- `game_cg` 现在使用独立的 clean-plate bridge：`txt2img_keyframe_game_cg_clean_plate.workflow_api.json`
- `game_cg` 仍复用同一套 `Z-Image image-b` 模型底座，但 prompt anchor 与默认保存前缀已经和 `stylized_concept` 分开，优先压低标题字 / logo / poster layout 倾向
- `game_cg` 已有本地 smoke evidence：`video_projects/real_smoke_20260530_stage05_gamecg_bridge/05_images/keyframe_image_manifest.json`
- `guofeng_ink` 已有本地 smoke evidence：`video_projects/real_smoke_20260530_stage05_guofeng_ink/05_images/keyframe_image_manifest.json`
- Stage 05 路线升级必须先看真实语义结果，不允许只凭“能出图”升级为默认：
  - `realistic` 先看建立镜头是否真的变成环境镜头，而不是片场/棚拍
  - `guofeng` 先看中景叙事和道具关系，而不是唯美半身像
  - `game_cg` 先看标题字、logo 和顶部文本是否被压掉，而不是只看角色是否站着
- 社区成熟 workflow 优先级高于仓库自写桥接；如果社区方案在本机缺模型/缺节点，必须先把 blocker 写清，再谈默认路由切换
- `anime_cn_newguofeng` 在本机当前仍未通过 smoke：
  - 失败原因不是 prompt，而是本机缺少这条 Lumina 栈所需的 `neta-lumina-v1.0.safetensors`、`gemma_2_2b_fp16.safetensors` 和匹配的 VAE 路径
  - 失败证据：`video_projects/real_smoke_20260530_stage05_anime_cn_newguofeng/05_images/comfyui_image_requests.json`
- `guofeng_ink` 当前有一个额外例外：外部 `Workflow-Qwen-Image-LORA.json` 源在 2026-05-30 核验时出现了与 `liuyifei` LoRA 混线的问题，所以 repo 内独立文件暂时仍是更可信的执行版本
- 后续优先迁移顺序：
- `realistic_cinematic` 已吸收 `AmazingZImageWorkflow/amazing-z-photo_SAFETENSORS.json` 的桥接经验，但在 2026-06-01 语义验收后，默认 prompt-only 路由改为 `Qwen 2512`，后续重点是继续压实建立镜头语义而不是继续把 Z-Image bridge 当默认
  - `stylized_concept` 已通过 repo bridge 吸收 `AmazingZImageWorkflow/amazing-z-image-b_SAFETENSORS.json` 的核心模型栈；后续重点是补 smoke evidence 与细分 preset
  - `anime_jp` → `Anima` / `Z-Anime` 原生 workflow
  - `guofeng_ink` → `Qwen-Image-Gufeng-LoRA` 专用 workflow
  - `anime_cn_newguofeng` → 继续以 `Neta-Lumina` 为主线补 community source
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
