@echo off
setlocal EnableExtensions
chcp 65001 >nul
echo Verifying codex-video-intake-plugin wrapper package...
set "ROOT=%~dp0"
set "PLUGIN=%ROOT%plugins\codex-video-pipeline-plugin\"
if not exist "%ROOT%.agents\plugins\marketplace.json" echo [ERROR] root marketplace.json missing & exit /b 1
if not exist "%PLUGIN%.codex-plugin\plugin.json" echo [ERROR] plugin.json missing & exit /b 1
if exist "%ROOT%plugins\codex-video-intake-plugin" echo [ERROR] old plugins\codex-video-intake-plugin directory still exists & exit /b 1
for %%S in (video-production-pipeline video-project-intake video-script-generation video-storyboard-generation video-character-bible video-keyframe-prompts video-keyframe-images video-video-clips video-audio video-assembly video-qa-delivery) do (
  if not exist "%PLUGIN%skills\%%S\SKILL.md" echo [ERROR] %%S skill missing & exit /b 1
)
if not exist "%PLUGIN%skills\video-video-clips\scripts\validate_video_clip_manifest.py" echo [ERROR] Stage 06 validator missing & exit /b 1
if not exist "%PLUGIN%skills\video-audio\scripts\validate_audio_manifest.py" echo [ERROR] Stage 07 validator missing & exit /b 1
if not exist "%PLUGIN%skills\video-assembly\scripts\validate_assembly_manifest.py" echo [ERROR] Stage 08 validator missing & exit /b 1
if not exist "%PLUGIN%skills\video-qa-delivery\scripts\validate_qa_manifest.py" echo [ERROR] Stage 09 validator missing & exit /b 1
if not exist "%ROOT%CODEX_START_HERE.md" echo [ERROR] root CODEX_START_HERE.md missing & exit /b 1
if not exist "%ROOT%.codex\current-task-contract.md" echo [ERROR] current task contract missing & exit /b 1
if not exist "%PLUGIN%docs\PROVIDER_INTEGRATION_CONTRACTS.md" echo [ERROR] provider contracts doc missing & exit /b 1
if not exist "%PLUGIN%docs\COMFYUI_WORKFLOW_EXPORT_GUIDE.md" echo [ERROR] workflow export guide missing & exit /b 1
if not exist "%PLUGIN%docs\CODEX_LOCAL_TASK_RUNBOOK.md" echo [ERROR] local task runbook missing & exit /b 1
if not exist "%PLUGIN%docs\STAGE00_STAGE02_ARCHITECTURE_CONTRACT.md" echo [ERROR] Stage00-Stage02 contract missing & exit /b 1
if not exist "%PLUGIN%docs\STAGE05_MAINLINE_GUARDRAILS.md" echo [ERROR] Stage05 guardrails missing & exit /b 1
echo [OK] Wrapper package structure looks valid.
