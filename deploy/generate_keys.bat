@echo off
chcp 65001 >nul
echo ============================================
echo  Ozon Analytics — 生产密钥生成工具
echo  用于云服务器部署前生成加密密钥
echo ============================================
echo.

set "VENV_PYTHON=C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe"

echo [1] 生成 OZON_ENCRYPTION_KEY（API Key 加密）...
%VENV_PYTHON% -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
echo.

echo [2] 生成 OZON_JWT_SECRET（JWT 签名）...
%VENV_PYTHON% -c "import secrets; print(secrets.token_hex(32))"
echo.

echo ============================================
echo  将以上两个值填入服务器的 .env 文件
echo  不要使用自动生成的临时密钥！
echo ============================================
pause
