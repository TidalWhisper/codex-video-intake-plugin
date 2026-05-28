---
name: video-qa-delivery
description: Internal/recovery skill for Stage 09 QA and delivery. It checks the Stage 08 rough cut, generates QA checklist, issue report, delivery report, asset index, and final delivery package evidence. In normal use, $video-production-pipeline invokes this automatically after Stage 08 is confirmed.
---

# Stage 09：质量检查与交付

## 目标

本阶段用于完成最终质量检查与交付归档。它不是重新创作阶段，而是基于 Stage 08 的粗剪成片进行证据化验收、问题记录、交付包生成。

正常流程中，用户不需要手动调用本 skill。总控入口仍然是：

```text
$video-production-pipeline
```

本 skill 只用于失败恢复、单阶段重跑和调试。

## 输入文件

必须读取：

```text
<project_dir>/00_intake/project_brief.locked.json
<project_dir>/08_assembly/assembly_manifest.json
```

建议读取：

```text
<project_dir>/01_script/script.json
<project_dir>/02_storyboard/storyboard.json
<project_dir>/03_characters/character_bible.json
<project_dir>/04_keyframes/keyframe_prompts.json
<project_dir>/05_images/keyframe_image_manifest.json
<project_dir>/06_video_clips/video_clip_manifest.json
<project_dir>/07_audio/audio_manifest.json
```

## 输出文件

必须写入：

```text
<project_dir>/09_qa/qa_plan.md
<project_dir>/09_qa/qa_manifest.json
<project_dir>/09_qa/qa_checklist.json
<project_dir>/09_qa/issue_report.md
<project_dir>/09_qa/delivery_report.md
<project_dir>/09_qa/delivery_manifest.json
<project_dir>/09_qa/asset_index.json
<project_dir>/09_qa/qa_review.md
<project_dir>/09_qa/final_delivery/
  ├─ rough_cut.mp4
  ├─ README_DELIVERY.md
  ├─ delivery_report.md
  └─ asset_index.json
```

## 硬规则

1. 不允许只口头说“已交付”。
2. Stage 08 的 rough_cut.mp4 必须真实存在且大小大于 0。
3. `qa_manifest.json` 必须记录 QA 检查项、最终视频证据、交付包文件清单。
4. `final_delivery/rough_cut.mp4` 必须真实存在且大小大于 0。
5. `validate_qa_manifest.py --mode final` 必须通过。
6. 如果发现阻塞问题，必须写入 `issue_report.md`，不得进入交付完成状态。

## 推荐执行命令

创建 QA 草稿：

```bash
python skills/video-qa-delivery/scripts/new_qa_manifest.py <project_dir>/00_intake/project_brief.locked.json <project_dir>/08_assembly/assembly_manifest.json <project_dir>/09_qa/qa_manifest.json
```

生成交付包并同步证据：

```bash
python skills/video-qa-delivery/scripts/package_delivery.py <project_dir>/09_qa/qa_manifest.json
```

最终校验：

```bash
python skills/video-qa-delivery/scripts/validate_qa_manifest.py --mode final <project_dir>/09_qa/qa_manifest.json
```

## 用户确认门

Stage 09 完成后必须提示：

```text
Stage 09 质量检查与交付包已生成。

请确认：
A. 确认交付完成，项目结束
B. 返回 Stage 08 重新合成粗剪
C. 返回 Stage 07 调整配音/音乐
D. 返回 Stage 06 替换视频片段
E. 返回 Stage 05 替换关键帧图片
F. 导出问题清单，暂不结束项目
```

用户确认 A 后，更新 `project_manifest.json`：

```json
{
  "current_stage": "STAGE_09_QA_CONFIRMED",
  "qa_confirmed": true,
  "delivery_complete": true,
  "allowed_next_stage": "PROJECT_DELIVERED"
}
```
