@echo off
chcp 65001 >nul
title Ozon Analytics - Environment Check

echo ============================================
echo   Ozon Analytics - Environment Check
echo ============================================
echo.

:: Check Python
echo [1/4] Checking Python...
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f %%a in ('python -c "import sys; print(sys.version.split()[0])"') do echo   [OK] Python %%a
) else (
    echo   [FAIL] Python not found in PATH
)

:: Check venv
echo.
echo [2/4] Checking venv...
if exist "C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe" (
    echo   [OK] Found venv at C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\
) else (
    echo   [WARN] Default venv not found
)

:: Check Node
echo.
echo [3/4] Checking Node.js...
where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f %%a in ('node -v') do echo   [OK] Node.js %%a
) else (
    echo   [FAIL] Node.js not found
)

where npm >nul 2>&1
if %errorlevel% equ 0 (
    for /f %%a in ('npm -v') do echo   [OK] npm v%%a
) else (
    echo   [FAIL] npm not found
)

:: Check ports
echo.
echo [4/4] Checking ports...

>nul 2>&1 netstat -an | findstr /c:":8848" && (
    echo   [WARN] Port 8848 is in use
) || (
    echo   [OK] Port 8848 is free
)

>nul 2>&1 netstat -an | findstr /c:":5173" && (
    echo   [WARN] Port 5173 is in use
) || (
    echo   [OK] Port 5173 is free
)

echo.
echo ============================================
echo   Check complete.
echo   If all items show [OK], you can start.
echo ============================================
echo.
pause
