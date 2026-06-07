#!/bin/bash
set -e

# ===================================================
# Ozon Analytics — 服务器首次初始化脚本
# 目标: Ubuntu 22.04 LTS
# 数据库: PostgreSQL 15+
# 用法: sudo bash setup.sh
# ===================================================

APP_DIR="/opt/ozon-analytics"
LOG_DIR="/var/log/ozon-analytics"
DB_USER="ozon"
DB_NAME="ozon_analytics"
DB_PASS=$(openssl rand -hex 16)

echo "========================================="
echo "  Ozon Analytics — 服务器初始化"
echo "========================================="

echo ""
echo "=== 1/9: 系统更新 ==="
apt update && apt upgrade -y

echo ""
echo "=== 2/9: 安装系统依赖 ==="
apt install -y python3 python3-pip python3-venv nginx git curl \
  postgresql postgresql-contrib

echo ""
echo "=== 3/9: 安装 Node.js (前端构建需要) ==="
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
fi
echo "Node.js: $(node --version)"
echo "npm: $(npm --version)"

echo ""
echo "=== 4/9: 创建系统用户 ==="
id -u ozon &>/dev/null || useradd -m -s /bin/bash ozon

echo ""
echo "=== 5/9: 创建目录结构 ==="
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
chown -R ozon:ozon "$APP_DIR" "$LOG_DIR"

echo ""
echo "=== 6/9: 配置 PostgreSQL ==="
# 确保 PostgreSQL 正在运行
systemctl enable postgresql
systemctl start postgresql

# 创建数据库和用户（如果不存在）
su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'\"" | grep -q 1 || \
  su - postgres -c "psql -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';\""

su - postgres -c "psql -lqt" | cut -d \| -f 1 | grep -qw "$DB_NAME" || \
  su - postgres -c "psql -c \"CREATE DATABASE $DB_NAME OWNER $DB_USER;\""

echo "✅ PostgreSQL 数据库 '$DB_NAME' 和用户 '$DB_USER' 已创建"
echo "   数据库密码: $DB_PASS"

echo ""
echo "=== 7/9: 创建 Python 虚拟环境 & 安装依赖 ==="
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

echo ""
echo "=== 8/9: 构建前端 ==="
cd "$APP_DIR/frontend"
npm install
npm run build
echo "✅ 前端构建完成: $APP_DIR/frontend/dist/"

echo ""
echo "=== 9/9: 安装 systemd 服务 & Nginx 配置 ==="
# 复制服务文件
cp "$APP_DIR/deploy/ozon-analytics-web.service" /etc/systemd/system/
cp "$APP_DIR/deploy/ozon-analytics-scheduler.service" /etc/systemd/system/

# 复制 Nginx 配置
cp "$APP_DIR/deploy/ozon-analytics.conf" /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/ozon-analytics.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试 Nginx 配置
nginx -t

# 创建 .env 文件
if [ ! -f "$APP_DIR/.env" ]; then
    # 生成加密密钥
    ENCRYPTION_KEY=$("$APP_DIR/venv/bin/python" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    # 生成 JWT 密钥
    JWT_SECRET=$("$APP_DIR/venv/bin/python" -c "import secrets; print(secrets.token_hex(32))")

    # 获取服务器 IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

    cat > "$APP_DIR/.env" << ENVEOF
# ============================================
# Ozon Analytics — 生产环境配置
# ============================================

# 环境标识（必填，不要修改）
ENV=production

# 数据库连接（PostgreSQL，必填）
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}

# 加密密钥（必填 — 用于加密存储 Ozon API Key）
OZON_ENCRYPTION_KEY=${ENCRYPTION_KEY}

# JWT 密钥（必填 — 用于用户认证 Token 签名）
OZON_JWT_SECRET=${JWT_SECRET}

# CORS 允许的源（改为你的服务器 IP）
CORS_ORIGINS=http://${SERVER_IP},http://${SERVER_IP}:80

# 前端 URL（邮件链接中使用）
FRONTEND_URL=http://${SERVER_IP}

# Ozon API 代理（中国服务器访问俄罗斯 API 可能需要）
# OZON_PROXY_URL=http://your-proxy:port

# 试用天数
TRIAL_DAYS=14

# 限流（每分钟请求数）
RATE_LIMIT_PER_MINUTE=60
ENVEOF

    echo "✅ .env 文件已生成: $APP_DIR/.env"
    echo ""
    echo "⚠️  重要: 请确认以下配置："
    echo "   - CORS_ORIGINS=http://${SERVER_IP}  (如果 IP 不对请手动修改)"
    echo "   - 如果服务器在国内，建议设置 OZON_PROXY_URL 代理访问 Ozon API"
else
    echo "⚠️  .env 文件已存在，跳过生成"
fi

# 设置 .env 文件权限
chown ozon:ozon "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

# 创建日志轮转
cat > /etc/logrotate.d/ozon-analytics << 'EOF'
/var/log/ozon-analytics/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

# 设置目录权限
chown -R ozon:ozon "$APP_DIR" "$LOG_DIR"

# 确保 PostgreSQL 允许本地密码连接
PG_HBA=$(find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1)
if [ -n "$PG_HBA" ]; then
    if ! grep -q "local.*all.*ozon.*md5" "$PG_HBA" 2>/dev/null; then
        # 在文件开头添加 ozon 用户的 md5 认证
        sed -i "/^#.*TYPE.*DATABASE.*USER/a local   all             ozon                                   md5" "$PG_HBA"
        sed -i "/^#.*TYPE.*DATABASE.*USER/a host    all             ozon           127.0.0.1/32            md5" "$PG_HBA"
        su - postgres -c "psql -c 'SELECT pg_reload_conf();'" 2>/dev/null || systemctl restart postgresql
        echo "✅ PostgreSQL 认证已配置"
    fi
fi

echo ""
echo "========================================="
echo "  初始化完成！"
echo "========================================="
echo ""
echo "下一步操作："
echo ""
echo "  1. 检查 .env 配置："
echo "     nano $APP_DIR/.env"
echo ""
echo "  2. 启动服务："
echo "     systemctl daemon-reload"
echo "     systemctl enable ozon-analytics-web ozon-analytics-scheduler"
echo "     systemctl start ozon-analytics-web ozon-analytics-scheduler"
echo "     systemctl restart nginx"
echo ""
echo "  3. 验证服务状态："
echo "     systemctl status ozon-analytics-web"
echo "     systemctl status ozon-analytics-scheduler"
echo ""
echo "  4. 浏览器访问："
echo "     http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_SERVER_IP')"
echo ""
echo "  5. 查看实时日志："
echo "     journalctl -u ozon-analytics-web -f"
echo "     journalctl -u ozon-analytics-scheduler -f"
echo ""
