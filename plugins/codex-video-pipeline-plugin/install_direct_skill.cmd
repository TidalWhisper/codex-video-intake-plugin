@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "SRC=%~dp0skills"
set "DEST=%USERPROFILE%\.agents\skills"
if not exist "%SRC%\video-production-pipeline\SKILL.md" (
  echo [ERROR] Source skills directory missing: %SRC%
  pause
  exit /b 1
)
if not exist "%DEST%" mkdir "%DEST%"
for %%S in (video-production-pipeline video-project-intake video-script-generation video-storyboard-generation video-character-bible video-keyframe-prompts video-keyframe-images video-video-clips video-audio video-assembly video-qa-delivery) do (
  if exist "%DEST%\%%S" rmdir /S /Q "%DEST%\%%S"
  xcopy /E /I /Y "%SRC%\%%S" "%DEST%\%%S" >nul
  if errorlevel 1 (
    echo [ERROR] Failed to install direct skill: %%S
    pause
    exit /b 1
  )
)
echo Installed direct skills into:
echo   %DEST%
echo Restart Codex, then test with: /skills and $video-production-pipeline
pause
