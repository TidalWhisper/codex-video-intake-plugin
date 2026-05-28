# 任务：接入 Stage 06 ComfyUI LTX I2V

目标：使用 Stage 05 关键帧和 Stage 04 motion prompt 生成视频片段。

必须新增：

- `scripts/providers/run_comfyui_ltx_i2v.py`
- LTX workflow 接入说明
- tests

要求：

1. 从 `video_clip_jobs.json` 读取任务。
2. 每个任务必须引用 start/end keyframe。
3. 替换 workflow 中图片、motion prompt、seed、frame_count、fps。
4. 输出 mp4 到 `06_video_clips/clips/`。
5. 更新 `video_clip_manifest.json`。
6. final validator 通过。
