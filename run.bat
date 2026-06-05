@echo off
chcp 65001 >nul
echo ====================================
echo   Ozon Analytics - 启动中...
echo ====================================
cd /d "%~dp0backend"
C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8848 --reload
pause
