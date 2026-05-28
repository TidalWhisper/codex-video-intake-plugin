# Project Folder Structure

Every generated video project must live in its own independent folder under `video_projects/`.

Recommended folder name:

```text
video_projects/<project_id>/
```

`project_id` format:

```text
video_YYYYMMDD_HHMMSS_<short_slug>
```

Required structure:

```text
video_projects/<project_id>/
├─ project_manifest.json
├─ 00_intake/
│  ├─ intake_state.json
│  ├─ project_brief.draft.json
│  └─ project_brief.locked.json
├─ 01_script/
│  ├─ story_direction.md
│  ├─ story_direction.json
│  ├─ plot_structure.md
│  ├─ plot_structure.json
│  ├─ script.md
│  ├─ script.json
│  └─ script_review.md
├─ 02_storyboard/
├─ 03_characters/
├─ 04_keyframes/
├─ 05_images/
├─ 06_video_clips/
├─ 07_audio/
│  ├─ voice/
│  └─ music/
├─ 08_assembly/
├─ 09_qa/
└─ logs/
```

Stage 00 is responsible for `00_intake`. Stage 01 is responsible for `01_script`. Later stages must not write into earlier stage folders except to append logs or status evidence.
