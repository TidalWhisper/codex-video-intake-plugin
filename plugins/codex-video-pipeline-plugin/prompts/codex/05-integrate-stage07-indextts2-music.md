# 任务：接入 Stage 07 IndexTTS2 与背景音乐

目标：把 Stage 07 从 placeholder 音频改造成真实配音/音乐生成或本地音乐库接入。

必须新增：

- `scripts/providers/run_comfyui_indextts2.py`
- `scripts/providers/run_local_music_library.py` 或 `run_comfyui_music.py`
- tests

要求：

1. 从 `audio_jobs.json` 读取 voice/music 任务。
2. 旁白/对白按镜头拆分，不要整篇一次性 TTS。
3. 输出到 `07_audio/voice/` 和 `07_audio/music/`。
4. 更新 `audio_manifest.json`。
5. final validator 通过。
