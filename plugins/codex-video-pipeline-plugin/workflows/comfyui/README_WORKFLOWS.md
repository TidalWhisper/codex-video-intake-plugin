# ComfyUI workflow 放置目录

Stage 05 主线现在只保留三套本地 Zimage UI workflow，不再保留任何 Stage 05 的 Qwen 分流、bridge workflow、或旧兼容映射文件。

当前 Stage 05 只认这三条本地工作流：

```text
F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json
F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json
F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-comics_SAFETENSORS.json
```

路由入口：

- `config/stage05_route_registry.yaml`
- `config/stage05_optimization_profiles.yaml`
- `config/workflow_node_mapping.yaml`

Stage 05 当前映射关系：

- `realistic_cinematic` → `stage05_realistic_cinematic_amazing_z_photo_original` → `amazing-z-photo_SAFETENSORS.json`
- `shortdrama_realistic` → `stage05_realistic_cinematic_amazing_z_photo_original` → `amazing-z-photo_SAFETENSORS.json`
- `anime_jp` → `stage05_anime_jp` → `amazing-z-image-a_SAFETENSORS.json`
- `anime_cn_newguofeng` → `stage05_anime_jp` → `amazing-z-image-a_SAFETENSORS.json`
- `guofeng_ink` → `stage05_anime_jp` → `amazing-z-image-a_SAFETENSORS.json`
- `western_cartoon` → `stage05_western_cartoon` → `amazing-z-comics_SAFETENSORS.json`
- `stylized_concept` → `stage05_western_cartoon` → `amazing-z-comics_SAFETENSORS.json`
- `game_cg` → `stage05_western_cartoon` → `amazing-z-comics_SAFETENSORS.json`

执行约束：

- Stage 05 provider 顺序固定为：`OpenAI GPT Image 2 -> ComfyUI -> manual`
- 风格差异通过真实 `style_selector` 切换，不允许再回退到单独 bridge 或 Qwen reference workflow
- `txt2img_keyframe.workflow_api.json` 等通用 API workflow 仍可保留给非 Stage 05 通用能力，但不再作为 Stage 05 主线分支

维护规则：

- 如果要改 Stage 05 风格路由，先改 `stage05_route_registry.yaml`
- 如果要改尺寸/档位，改 `stage05_optimization_profiles.yaml`
- 如果要改 Zimage UI graph 控件绑定，改 `workflow_node_mapping.yaml`
- 不要恢复任何 Stage 05 bridge、兼容桥、旧 fallback、旧 example 主线说明
