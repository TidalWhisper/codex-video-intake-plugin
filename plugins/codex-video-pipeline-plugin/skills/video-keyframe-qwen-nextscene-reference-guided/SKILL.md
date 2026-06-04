---
name: video-keyframe-qwen-nextscene-reference-guided
description: Use when Stage 05 needs the local `AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json` workflow, or when the task involves Qwen NextScene reference-guided single-character continuity, single-shot prompt execution, or reducing rerolls for that workflow. This skill must be loaded before selecting or calling the local Qwen NextScene Stage 05 workflow.
---

# Stage 05 Qwen NextScene Reference-Guided

## Role

This skill is the mandatory execution contract for the local Qwen NextScene Stage 05 workflow.

Use it before:

- selecting the Qwen NextScene Stage 05 route
- composing prompts for that workflow
- running smoke tests for that workflow
- rerunning failed Qwen NextScene Stage 05 shots

## Required reads

Always read these files first, in order:

1. [references/latest-smoke-lessons.md](./references/latest-smoke-lessons.md)
2. [../video-keyframe-images/references/stage05-qwen-workflow-runtime-map.md](../video-keyframe-images/references/stage05-qwen-workflow-runtime-map.md)
3. [../video-keyframe-images/references/stage05-qwen-reference-guided-workflow-rules.md](../video-keyframe-images/references/stage05-qwen-reference-guided-workflow-rules.md)
4. [../video-keyframe-images/references/stage05-qwen-nextscene-prompt-convergence-rules.md](../video-keyframe-images/references/stage05-qwen-nextscene-prompt-convergence-rules.md)
5. [../video-keyframe-images/references/stage05-qwen-quality-gate-rules.md](../video-keyframe-images/references/stage05-qwen-quality-gate-rules.md)

## Hard execution rules

1. Workflow fixed to:
   - `F:/ComfyUI/ComfyUI/user/default/workflows/AI漫剧制作/AI漫剧-16宫格分镜图生成-QwenEdit+NextScene（自动分镜）-V1版.json`
2. Execution mode fixed to:
   - `reference_guided`
3. Only one primary reference image:
   - `03_characters/reference_images/CHAR_001_primary.png`
4. One Stage 05 job means one workflow execution, one `Next Scene`, one output frame.
5. Do not use this workflow as a 16-panel generator, contact sheet generator, or multi-line batch prompt runner.
6. Do not use it for:
   - multi-character interaction
   - `interaction_handoff`
   - `mid` guide shots
   - shots that require multiple reference images
7. Do not run multiple real `image_id` jobs in parallel against the same `keyframe_image_manifest.json`.

## Prompt contract

Each `Next Scene` prompt must explicitly lock:

- same protagonist identity
- same face
- same hairstyle
- same outfit silhouette
- action
- camera angle
- shot size
- subject size in frame
- lighting
- emotional progression

For back-view or rear-three-quarter shots, explicitly reinforce:

- `full-frame image`
- `no black bars`
- `no embedded border`
- `no picture-in-picture frame`

For wide or establishing shots, explicitly reinforce:

- small in-frame subject
- environment-first composition
- coastline / sky / scene readability

## Output acceptance

Do not treat “image generated successfully” as success.

Minimum pass bar before Stage 06:

- single full-frame image
- no grid / collage / panel split
- no black bars or fake letterbox
- single protagonist only
- stable face / hair / outfit silhouette
- shot intent matches Stage 04
- adjacent shots are meaningfully different

## Preferred use

Use this workflow first when all are true:

- single protagonist
- single reference image
- Stage 04 shot semantics are already confirmed
- Stage 06 target is `single_subject_motion`

If those conditions are not true, stop and choose another Stage 05 route instead of forcing this one.
