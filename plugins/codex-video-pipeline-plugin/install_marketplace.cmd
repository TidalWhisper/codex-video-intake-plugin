@echo off
setlocal
cd /d "%~dp0"
echo [1/3] Removing old local-codex-video-plugins marketplace if exists...
codex plugin marketplace remove local-codex-video-plugins

echo [2/3] Adding marketplace root: %CD%
codex plugin marketplace add "%CD%"

echo [3/3] Current marketplaces:
codex plugin marketplace list

echo.
echo Next: run codex, then open /plugins and install "Codex Video Intake".
endlocal
