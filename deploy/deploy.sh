#!/bin/bash
set -e

# ===================================================
# Ozon Analytics — 一键更新部署脚本
# 在服务器上运行，拉取最新代码并重启服务
# 用法: sudo bash deploy/deploy.sh
# ===================================================

APP_DIR="/opt/ozon-analytics"
LOG_DIR="/var/log/ozon-analytics"

echo "========================================="
echo "  Ozon Analytics — 更新部署"
echo "========================================="

echo ""
echo "=== 1/5: 拉取最新代码 ==="
cd "$APP_DIR"

if [ -d ".git" ]; then
    git pull origin main
else
    echo "⚠️  非 git 仓库，跳过拉取。请手动上传代码。"
fi

echo ""
echo "=== 2/5: 更新 Python 依赖 ==="
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt" --quiet

echo ""
echo "=== 3/5: 构建前端 ==="
cd "$APP_DIR/frontend"
if [ -d "node_modules" ]; then
    npm install --silent
else
    npm install
fi
npm run build
echo "✅ 前端构建完成"

echo ""
echo "=== 4/5: 数据库迁移检查 ==="
cd "$APP_DIR/backend"
# 如果使用 PostgreSQL，Alembic 迁移会在服务启动时自动执行
# 这里预先检查，确保迁移脚本存在
if [ -d "alembic/versions" ] && [ -n "$(ls -A alembic/versions/ 2>/dev/null)" ]; then
    echo "✅ Alembic 迁移脚本就绪（服务启动时自动执行）"
else
    echo "⚠️  未发现 Alembic 迁移脚本，将使用 create_all 初始化"
fi

echo ""
echo "=== 5/5: 重启服务 ==="
systemctl restart ozon-analytics-web
systemctl restart ozon-analytics-scheduler
systemctl reload nginx 2>/dev/null || true

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
systemctl status ozon-analytics-web --no-pager | head -10
echo "---"
systemctl status ozon-analytics-scheduler --no-pager | head -10
echo ""
echo "查看实时日志:"
echo "  journalctl -u ozon-analytics-web -f"
echo "  journalctl -u ozon-analytics-scheduler -f"
echo ""
