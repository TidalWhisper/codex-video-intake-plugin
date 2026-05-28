@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PACKAGE_ROOT=%~dp0"
set "SRC_SKILLS=%PACKAGE_ROOT%plugins\codex-video-pipeline-plugin\skills"
if not exist "%SRC_SKILLS%\video-production-pipeline\SKILL.md" echo [ERROR] source skills missing & pause & exit /b 1
if not exist "%USERPROFILE%\.agents\skills" mkdir "%USERPROFILE%\.agents\skills"
for %%S in (video-production-pipeline video-project-intake video-script-generation video-storyboard-generation video-character-bible video-keyframe-prompts video-keyframe-images video-video-clips video-audio video-assembly video-qa-delivery) do (
  if exist "%USERPROFILE%\.agents\skills\%%S" rmdir /S /Q "%USERPROFILE%\.agents\skills\%%S"
  xcopy /E /I /Y "%SRC_SKILLS%\%%S" "%USERPROFILE%\.agents\skills\%%S" >nul
)
echo [OK] Direct skills installed to %USERPROFILE%\.agents\skills
echo Restart Codex, then test: $video-production-pipeline
pause
