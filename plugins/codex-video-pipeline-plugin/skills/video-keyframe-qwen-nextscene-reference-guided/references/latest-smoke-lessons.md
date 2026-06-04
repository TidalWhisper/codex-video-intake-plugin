# Latest Smoke Lessons For Qwen NextScene

This note distills the latest validated behavior from:

- `video_projects/video_20260603_162507_一名年轻的亚洲女性穿着裙/05_images/qwen_nextscene_smoke_result_20260604.md`
- `video_projects/video_20260603_162507_一名年轻的亚洲女性穿着裙/05_images/qwen_nextscene_smoke_round2_result_20260604.md`

## Confirmed strengths

1. One primary character reference image is enough to keep:
   - face identity
   - hairstyle
   - dress silhouette
   reasonably stable across multiple shots.
2. The workflow is good enough to keep moving for:
   - single protagonist
   - low-action shots
   - multi-shot scene progression
   - `single_subject_motion` Stage 06 input preparation
3. Prompt convergence rules clearly improved shot separation between neighboring frames.

## Confirmed failure modes

1. Similar prompts tend to collapse into similar framing.
2. Rear-view shots can still produce black bars even after prompt tightening.
3. Wide establishing shots are not fully obedient yet; the subject may still come out too large.
4. Parallel writes to the same `keyframe_image_manifest.json` can leave image files generated while manifest status remains stale.

## What must now be treated as hard rules

1. Run this workflow in single-shot mode only.
2. Keep one workflow run per image frame.
3. Keep one primary reference image only.
4. Serialize real runs per manifest.
5. Treat rear-view shots as high-risk:
   - require border guardrails in prompt
   - require post-run black-bar inspection
6. Treat wide establishing shots as high-risk:
   - reinforce small subject ratio
   - reinforce environment-first composition
7. Do not pass outputs to Stage 06 if they contain:
   - black bars
   - grid / collage
   - identity drift
   - near-duplicate framing vs adjacent shots

## Best current usage envelope

Use the workflow when the job is:

- single female lead or otherwise single protagonist
- one reference image
- weak action
- small prop complexity
- no handoff interaction
- no need for mid guide

Avoid forcing it onto:

- multi-character shots
- strong action exchange
- wide action staging with multiple subjects
- shots that need a guaranteed borderless rear view on the first try
