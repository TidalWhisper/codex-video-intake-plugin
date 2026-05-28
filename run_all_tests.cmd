@echo off
setlocal
python "%~dp0run_all_tests.py"
if errorlevel 1 pause
