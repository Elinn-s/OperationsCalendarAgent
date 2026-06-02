@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

if not exist "%PYTHON_EXE%" goto missing_venv

set "APP_URL=http://localhost:8501"
echo Starting backup Streamlit demo: %APP_URL%
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process '%APP_URL%'"

"%PYTHON_EXE%" -m streamlit run "%~dp0streamlit_demo\streamlit_app.py"
pause
exit /b %ERRORLEVEL%

:missing_venv
echo Missing .venv\Scripts\python.exe
echo Please run: uv sync
pause
exit /b 1
