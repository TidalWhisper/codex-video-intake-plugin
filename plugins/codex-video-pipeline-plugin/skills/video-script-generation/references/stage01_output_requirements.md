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
