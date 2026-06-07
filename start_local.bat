@echo off
chcp 65001 >nul
title Ozon Analytics - 本地开发服务
cd /d "%~dp0"

echo ====================================
echo   Ozon Analytics 启动脚本
echo ====================================
echo.

REM 检查是否存在虚拟环境
if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
    echo [INFO] 使用项目虚拟环境: venv
) else if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo [INFO] 使用项目虚拟环境: .venv
) else (
    echo [INFO] 未找到虚拟环境，尝试使用系统 Python
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] 未找到 Python，请先安装 Python 3.12+
        pause
        exit /b 1
    )
    set PYTHON=python
)

echo [1/2] 安装/检查依赖...
%PYTHON% -m pip install -r backend\requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖就绪

echo [2/2] 启动后端服务...
echo.
echo 访问地址: http://localhost:8848
echo 按 Ctrl+C 停止服务
echo.

cd backend
%PYTHON% -m uvicorn main:app --host 0.0.0.0 --port 8848 --reload
pause
