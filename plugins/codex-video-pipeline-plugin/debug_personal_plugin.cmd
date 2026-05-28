@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo ============================================================
echo  Codex Video Intake - Debug Personal Plugin Install
echo ============================================================
echo.
set "DEST_PLUGIN=%USERPROFILE%\.codex\plugins\codex-video-intake-plugin"
set "MKT_FILE=%USERPROFILE%\.agents\plugins\marketplace.json"

echo [User]
echo USERPROFILE=%USERPROFILE%
echo.

echo [Check marketplace file]
echo %MKT_FILE%
if exist "%MKT_FILE%" (
  echo FOUND
  findstr /C:"codex-video-intake-plugin" "%MKT_FILE%" >nul && echo Contains plugin entry: YES || echo Contains plugin entry: NO
) else (
  echo MISSING
)
echo.

echo [Check plugin directory]
echo %DEST_PLUGIN%
if exist "%DEST_PLUGIN%" (echo FOUND) else (echo MISSING)
echo.

echo [Check plugin manifest]
if exist "%DEST_PLUGIN%\.codex-plugin\plugin.json" (echo FOUND: %DEST_PLUGIN%\.codex-plugin\plugin.json) else (echo MISSING)
echo.

echo [Check bundled Stage 00-09 skills]
for %%S in (video-production-pipeline video-project-intake video-script-generation video-storyboard-generation video-character-bible video-keyframe-prompts video-keyframe-images video-video-clips video-audio video-assembly video-qa-delivery) do (
  if exist "%DEST_PLUGIN%\skills\%%S\SKILL.md" (echo FOUND: %%S) else (echo MISSING: %%S)
)
echo.

echo [Codex marketplace list]
codex plugin marketplace list

echo.
echo Expected UI location:
echo   codex  ^>  /plugins  ^>  Personal / Personal Local Plugins  ^>  Codex Video Intake
echo.
pause
