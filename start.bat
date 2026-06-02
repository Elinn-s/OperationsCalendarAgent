@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

if not exist "%PYTHON_EXE%" goto missing_venv

set "APP_URL=http://localhost:8000/app"
echo Stopping existing StoreNotification API processes on port 8000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$self = $PID; $parent = (Get-CimInstance Win32_Process -Filter \"ProcessId=$self\").ParentProcessId; $project = [regex]::Escape((Resolve-Path '.').Path); Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -notin @($self, $parent) -and $_.CommandLine -match $project -and $_.Name -match 'python|cmd' -and $_.CommandLine -match 'uvicorn|multiprocessing-fork|run_api\.bat|start\.bat' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Starting StoreNotification web app: %APP_URL%
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process '%APP_URL%'"

"%PYTHON_EXE%" -m uvicorn storenotificationcircula.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir "%~dp0src" --reload-dir "%~dp0public"
pause
exit /b %ERRORLEVEL%

:missing_venv
echo Missing .venv\Scripts\python.exe
echo Please run: uv sync
pause
exit /b 1
