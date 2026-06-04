# ComfyUI workflow 放置目录

Stage 05 当前已经固定为两段式主线：

1. `Stage05-A` 只使用三套本地 Zimage UI workflow 生成主角色参考图
2. `Stage05-B` 固定使用本地 `QwenEdit+NextScene` reference-guided workflow 生成一致性分镜图

## Stage05-A bootstrap workflows

```text
F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-photo_SAFETENSORS.json
F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-image-a_SAFETENSORS.json
F:/ComfyUI/ComfyUI/user/default/workflows/Zimage/amazing-z-comics_SAFETENSORS.json
```

当前 Stage05-A 路由映射：

- `realistic_cinematic` / `shortdrama_realistic` -> `stage05_realistic_cinematic_amazing_z_photo_original`
- `anime_jp` / `anime_cn_newguofeng` / `guofeng_ink` -> `stage05_anime_jp`
- `western_cartoon` / `stylized_concept` / `game_cg` -> `stage05_western_cartoon`

## Stage05-B mainline workflow

```text
F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json
```

当前 Stage05-B 固定映射：

- `stage05_realistic_cinematic_qwen_edit_nextscene_local`

执行约束：

- `Stage05-A` 和 `Stage05-B` 不允许混成双主线
- 不允许恢复任何 Stage 05 bridge workflow、prompt-only Qwen 分支、或旧兼容 fallback
- `Stage05-B` 必须带主角色参考图，以 `reference_guided` 模式执行
- `Stage05-B` 只按单镜头帧串行执行，不把这条工作流当成 16 宫格批量分镜器

维护入口：

- Stage05-A 路由：`config/stage05_route_registry.yaml`
- 节点绑定：`config/workflow_node_mapping.yaml`
- 尺寸/档位：`config/stage05_optimization_profiles.yaml`
- 主线规则：`docs/STAGE05_REFERENCE_GUIDED_REFACTOR_PLAN_20260604.md`
