@echo off
chcp 65001 >nul
title Ozon Analytics Launcher

set PROJECT_DIR=%~dp0
set BACKEND_DIR=%PROJECT_DIR%backend
set FRONTEND_DIR=%PROJECT_DIR%frontend

echo ============================================
echo   Ozon Analytics - Starting...
echo   Backend : FastAPI + Uvicorn (:8848)
echo   Frontend : Vue 3 + Vite (:5173)
echo ============================================
echo.

:: ====== Find Python ======
set PYTHON_CMD=

if exist "C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe" (
    set PYTHON_CMD=C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe
    echo [OK] Found venv Python
)

if "%PYTHON_CMD%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=python
        echo [OK] Using system Python
    )
)

if "%PYTHON_CMD%"=="" (
    if exist "C:\Program Files\Python312\python.exe" set PYTHON_CMD=C:\Program Files\Python312\python.exe
    if exist "C:\Program Files\Python311\python.exe" set PYTHON_CMD=C:\Program Files\Python311\python.exe
    if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" set PYTHON_CMD=C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe
    if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe" set PYTHON_CMD=C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

echo.

:: ====== Start Backend ======
echo [1/3] Starting backend...
start "Ozon Backend" cmd /c "cd /d "%BACKEND_DIR%" && "%PYTHON_CMD%" -m uvicorn main:app --host 0.0.0.0 --port 8848 --reload --log-level info"

echo   Waiting 3 seconds for backend...
timeout /t 3 /nobreak >nul
echo   [OK] Backend starting at http://localhost:8848
echo.

:: ====== Frontend ======
echo [2/3] Checking frontend dependencies...

cd /d "%FRONTEND_DIR%"
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Please install Node.js
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo   Running npm install...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
    echo   [OK] Dependencies installed
) else (
    echo   [OK] Dependencies ready
)
echo.

:: ====== Start Frontend ======
echo [3/3] Starting frontend dev server...
start "Ozon Frontend" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev"

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo   [OK] All services started!
echo.
echo   Backend  : http://localhost:8848
echo   Frontend : http://localhost:5173
echo.
echo   Close the server windows to stop.
echo   Or run stop-all.bat
echo ============================================
echo.

start http://localhost:5173
echo Browser opened. If not, visit http://localhost:5173 manually.
echo.
pause
