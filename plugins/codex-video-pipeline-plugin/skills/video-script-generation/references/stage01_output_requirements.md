# Stage 01 Output Requirements

Stage 01 turns a locked Stage 00 brief into a script package. It must not create storyboards, character image prompts, ComfyUI workflows, TTS files, music files, or assembled videos.

Required outputs in `<project_dir>/01_script/`:

1. `story_direction.md` and `story_direction.json`
   - theme
   - emotional arc
   - protagonist intention
   - conflict or subtle narrative movement
   - ending direction

2. `plot_structure.md` and `plot_structure.json`
   - time-coded structure based on target duration
   - for 15-60 seconds, use 3-6 beats
   - for 90-180 seconds, use 6-12 beats
   - for 300 seconds, use 10-20 beats

3. `script.md` and `script.json`
   - title
   - logline
   - complete script
   - scene-level timing
   - voiceover/dialogue lines depending on the locked brief
   - no storyboard shot list yet

4. `script_review.md`
   - duration fit check
   - genre/style fit check
   - voice/music consistency check
   - whether it is ready for Stage 02

After writing the files, show the user a concise script confirmation menu:

```text
剧本已生成，请确认：
A. 剧本可以，进入分镜拆解
B. 修改故事走向
C. 修改人物设定
D. 修改旁白/对白
E. 修改视频节奏
F. 重新生成剧本
```

Only after explicit user confirmation may the project manifest set `allowed_next_stage` to `STAGE_02_STORYBOARD`.

## Planned Codex-First Refactor

This document now also defines the design-track direction for a future Stage 01 refactor.

Planned architecture:

- Python compiles constraints and validates outputs.
- Codex generates the creative text.
- Python writes md/json artifacts and drives repair loops.

First-batch design artifacts:

- `references/stage01_llm_output.schema.json`
- `references/stage01_codex_generation_prompt.md`
- `references/stage01_codex_repair_prompt.md`
- `references/stage01_repair_packet.schema.json`
- `scripts/build_stage01_prompt_packet.py`
- `scripts/write_stage01_outputs.py`
- `scripts/build_stage01_repair_packet.py`

Important:

- These artifacts are design-track only in the current batch.
- The active production Stage 01 path has not been switched yet.
