@echo off
chcp 65001 >nul
title Ozon Analytics - Stop Servers

echo Stopping backend (port 8848)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /c:":8848"') do (
    taskkill /f /pid %%a >nul 2>&1 && echo [OK] Stopped PID %%a
)

echo Stopping frontend (port 5173)...
for /f "tokens=5" %%b in ('netstat -ano ^| findstr /c:":5173"') do (
    taskkill /f /pid %%b >nul 2>&1 && echo [OK] Stopped PID %%b
)

echo.
echo [OK] All services stopped.
pause
