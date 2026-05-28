# Provider 接入契约

## 1. 统一 Provider 结果结构

每个真实 provider 完成一个任务后，必须返回或写入类似结构：

```json
{
  "job_id": "S001_start",
  "provider": "openai_gpt_image2",
  "status": "success",
  "input_prompt": "...",
  "output_path": "05_images/keyframes/S001_start.png",
  "evidence": {
    "file_exists": true,
    "file_size_bytes": 123456,
    "created_at": "2026-05-28T12:00:00+08:00"
  },
  "errors": []
}
```

失败时：

```json
{
  "job_id": "S001_start",
  "provider": "comfyui_txt2img",
  "status": "failed",
  "output_path": null,
  "errors": [
    {
      "type": "provider_error",
      "message": "ComfyUI server unavailable"
    }
  ]
}
```

## 2. Stage 05 图片 Provider 契约

输入：

- `04_keyframes/keyframe_prompts.json`
- `03_characters/character_bible.json`
- `00_intake/project_brief.locked.json`

输出：

- `05_images/openai_image_requests.json`
- `05_images/comfyui_image_requests.json`
- `05_images/keyframes/*.png`
- `05_images/keyframe_image_manifest.json`

成功门禁：

- 每个要求生成的 keyframe 都有真实图片文件。
- 文件大小大于 0。
- final validator 通过。

## 3. Stage 06 视频 Provider 契约

输入：

- `04_keyframes/motion_prompts.json`
- `05_images/keyframe_image_manifest.json`
- `02_storyboard/storyboard.json`

输出：

- `06_video_clips/comfyui_ltx_i2v_requests.json`
- `06_video_clips/clips/*.mp4`
- `06_video_clips/video_clip_manifest.json`

成功门禁：

- 每个 shot 至少有一个 mp4。
- 每个 mp4 文件真实存在且大小大于 0。
- manifest 记录 start/end keyframe 引用。

## 4. Stage 07 音频 Provider 契约

输入：

- `01_script/script.json`
- `02_storyboard/storyboard.json`
- `00_intake/project_brief.locked.json`

输出：

- `07_audio/indextts2_requests.json`
- `07_audio/music_requests.json`
- `07_audio/voice/*.wav`
- `07_audio/music/*.wav`
- `07_audio/audio_manifest.json`

成功门禁：

- 配音需求为 true 时，voice 文件必须存在。
- 音乐需求为 true 时，music 文件必须存在。
- final validator 通过。
