@echo off
setlocal
cd /d "%~dp0.."

set "ENABLE_LOCAL_OCR=true"
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

if not exist "%PYTHON_EXE%" goto missing_venv

set "APP_URL=http://localhost:8000/app"
echo Starting local OCR Plan B web app: %APP_URL%
echo ENABLE_LOCAL_OCR=%ENABLE_LOCAL_OCR%
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process '%APP_URL%'"

"%PYTHON_EXE%" -m uvicorn storenotificationcircula.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir "%CD%\src" --reload-dir "%CD%\public"
pause
exit /b %ERRORLEVEL%

:missing_venv
echo Missing .venv\Scripts\python.exe
echo Please run: uv sync
pause
exit /b 1
