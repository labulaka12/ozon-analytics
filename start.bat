@echo off
chcp 65001 >nul
cd /d "%~dp0\backend"
echo [Ozon Analytics] 正在启动后端服务...
echo 访问地址: http://localhost:8848
echo 按 Ctrl+C 停止服务
echo.
"C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8848
pause
