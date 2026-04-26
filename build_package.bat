@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_package.ps1" %*
exit /b %ERRORLEVEL%
