@echo off
setlocal EnableExtensions
chcp 65001 >nul
echo ==== Debug Personal Plugin ====
echo Package root: %~dp0
echo.
echo Expected source plugin:
echo   %~dp0plugins\codex-video-pipeline-plugin\
dir /a "%~dp0plugins\codex-video-pipeline-plugin" 2>nul
echo.
echo Installed plugin:
echo   %USERPROFILE%\.codex\plugins\codex-video-pipeline-plugin
dir /a "%USERPROFILE%\.codex\plugins\codex-video-pipeline-plugin" 2>nul
echo.
echo Marketplace:
echo   %USERPROFILE%\.agents\plugins\marketplace.json
type "%USERPROFILE%\.agents\plugins\marketplace.json" 2>nul
echo.
echo Codex marketplace list:
codex plugin marketplace list
pause
