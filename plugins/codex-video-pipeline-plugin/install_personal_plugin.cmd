@echo off
setlocal EnableExtensions
chcp 65001 >nul

echo ============================================================
echo  Codex Video Pipeline - Personal Plugin Installer
echo ============================================================
echo.

set "SRC_PLUGIN=%~dp0"
if not exist "%SRC_PLUGIN%.codex-plugin\plugin.json" (
  echo [ERROR] Cannot find plugin manifest:
  echo         "%SRC_PLUGIN%.codex-plugin\plugin.json"
  pause
  exit /b 1
)
if not exist "%SRC_PLUGIN%skills\video-production-pipeline\SKILL.md" (
  echo [ERROR] Cannot find skills directory under source plugin root.
  pause
  exit /b 1
)

set "DEST_PLUGIN=%USERPROFILE%\.codex\plugins\codex-video-pipeline-plugin"
if not exist "%USERPROFILE%\.codex\plugins" mkdir "%USERPROFILE%\.codex\plugins"
if exist "%USERPROFILE%\.codex\plugins\codex-video-intake-plugin" rmdir /S /Q "%USERPROFILE%\.codex\plugins\codex-video-intake-plugin"
if exist "%DEST_PLUGIN%" rmdir /S /Q "%DEST_PLUGIN%"
xcopy /E /I /Y "%SRC_PLUGIN%" "%DEST_PLUGIN%" >nul
if errorlevel 1 (
  echo [ERROR] Failed to copy plugin to:
  echo         "%DEST_PLUGIN%"
  pause
  exit /b 1
)

set "MKT_DIR=%USERPROFILE%\.agents\plugins"
set "MKT_FILE=%MKT_DIR%\marketplace.json"
if not exist "%MKT_DIR%" mkdir "%MKT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$path = Join-Path $env:USERPROFILE '.agents\plugins\marketplace.json';" ^
  "$dir = Split-Path -Parent $path; New-Item -ItemType Directory -Force -Path $dir | Out-Null;" ^
  "if (Test-Path $path) { Copy-Item $path ($path + '.bak') -Force; try { $m = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json } catch { $m = $null } } else { $m = $null };" ^
  "if ($null -eq $m) { $m = [pscustomobject]@{ name='personal-local-plugins'; interface=[pscustomobject]@{ displayName='Personal Local Plugins' }; plugins=@() } };" ^
  "if (-not ($m.PSObject.Properties.Name -contains 'name') -or [string]::IsNullOrWhiteSpace($m.name)) { Add-Member -InputObject $m -NotePropertyName name -NotePropertyValue 'personal-local-plugins' -Force };" ^
  "if (-not ($m.PSObject.Properties.Name -contains 'interface') -or $null -eq $m.interface) { Add-Member -InputObject $m -NotePropertyName interface -NotePropertyValue ([pscustomobject]@{ displayName='Personal Local Plugins' }) -Force };" ^
  "if (-not ($m.PSObject.Properties.Name -contains 'plugins') -or $null -eq $m.plugins) { Add-Member -InputObject $m -NotePropertyName plugins -NotePropertyValue @() -Force };" ^
  "$entry = [pscustomobject]@{ name='codex-video-pipeline-plugin'; source=[pscustomobject]@{ source='local'; path='./.codex/plugins/codex-video-pipeline-plugin' }; policy=[pscustomobject]@{ installation='AVAILABLE'; authentication='ON_INSTALL' }; category='Productivity' };" ^
  "$plugins = @($m.plugins | Where-Object { $_.name -ne 'codex-video-intake-plugin' -and $_.name -ne 'codex-video-pipeline-plugin' }); $plugins += $entry; $m.plugins = $plugins;" ^
  "$m | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $path -Encoding UTF8;"
if errorlevel 1 (
  echo [ERROR] Failed to write personal marketplace:
  echo         "%MKT_FILE%"
  pause
  exit /b 1
)

if not exist "%DEST_PLUGIN%\.codex-plugin\plugin.json" echo [ERROR] Installed plugin manifest missing. & pause & exit /b 1
for %%S in (video-production-pipeline video-project-intake video-script-generation video-storyboard-generation video-character-bible video-keyframe-prompts video-keyframe-images video-video-clips video-audio video-assembly video-qa-delivery) do (
  if not exist "%DEST_PLUGIN%\skills\%%S\SKILL.md" (
    echo [ERROR] Installed skill missing: %%S
    pause
    exit /b 1
  )
)

echo.
echo [OK] Installed plugin directory:
echo   %DEST_PLUGIN%
echo.
echo [OK] Personal marketplace file:
echo   %MKT_FILE%
echo.
echo IMPORTANT:
echo   1. Close all running Codex CLI windows.
echo   2. Start Codex again: codex
echo   3. Open: /plugins
echo   4. Look for plugin: Codex Video Pipeline
echo   5. Install or enable it, then start a new thread.
echo   6. Recommended test with: $video-production-pipeline
echo.
pause
