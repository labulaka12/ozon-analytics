@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%backend"

set "VENV_PYTHON=C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe"
set "FALLBACK_PYTHON=python"

if exist "%VENV_PYTHON%" (
    set "PYTHON_EXE=%VENV_PYTHON%"
) else (
    set "PYTHON_EXE=%FALLBACK_PYTHON%"
)

start "Ozon Analytics Server" cmd /k "%PYTHON_EXE% start_server.py"

timeout /t 2 /nobreak >nul
start "" "http://localhost:8848"
