# Ozon Analytics — 生产环境部署指南

> 适用场景：云服务器 + PostgreSQL + HTTP IP 访问（暂无域名和 HTTPS）

## 架构

```
                         ┌─ Worker 1 (Uvicorn)
浏览器 ──HTTP:80──→ Nginx ──→ Gunicorn ──┬─ Worker 2     ──→ FastAPI ──→ PostgreSQL
                         ↑         ├─ Worker 3
                    127.0.0.1:8848  └─ Worker 4
                         │
                         └─ Scheduler Worker (独立进程, APScheduler)
                              每日 08:00 自动同步
```

**请求路由**：
- `/static/*` → Nginx 直接返回 `frontend/dist/` 中的静态文件（高性能）
- `/api/*`, `/` → Nginx 反向代理到 Gunicorn → FastAPI

## 前置条件

| 项目 | 要求 |
|------|------|
| 云服务器 | 阿里云 ECS / 腾讯云 LightHouse / 华为云 |
| 操作系统 | Ubuntu 22.04 LTS（推荐） |
| 配置 | 2核4G 起 |
| Python | 3.12+ |
| Node.js | 20+（前端构建需要） |
| PostgreSQL | 15+ |
| 费用 | 服务器约 ¥100~150/月 |

## 快速部署

### 第一步：上传代码到服务器

**方式 A — SCP 上传（推荐首次使用）**

在本地电脑执行：

```bash
# 打包项目（排除 venv、__pycache__、data 等无用文件）
cd ozon-analytics
tar czf ../ozon-analytics.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='data' \
  --exclude='node_modules' \
  --exclude='.git' \
  .

# 上传到服务器
scp ../ozon-analytics.tar.gz root@你的服务器IP:/tmp/

# SSH 登录服务器
ssh root@你的服务器IP

# 解压到目标目录
mkdir -p /opt/ozon-analytics
cd /opt/ozon-analytics
tar xzf /tmp/ozon-analytics.tar.gz
```

**方式 B — Git Clone（如果项目在 Git 仓库）**

```bash
ssh root@你的服务器IP
git clone https://github.com/your-org/ozon-analytics.git /opt/ozon-analytics
```

### 第二步：运行初始化脚本

```bash
cd /opt/ozon-analytics
sudo bash deploy/setup.sh
```

脚本会自动完成：
1. 系统更新 + 安装依赖（Python, Node.js, Nginx, PostgreSQL）
2. 创建系统用户 `ozon`
3. 创建 PostgreSQL 数据库和用户
4. 创建 Python 虚拟环境 + 安装 Python 依赖
5. 构建前端（`npm run build`）
6. 安装 systemd 服务 + Nginx 配置
7. 自动生成 `.env` 文件（含加密密钥、JWT 密钥、数据库连接串）

### 第三步：检查并修改 .env 配置

```bash
nano /opt/ozon-analytics/.env
```

**必须确认的配置项**：

```ini
# 环境标识
ENV=production

# 数据库（setup.sh 已自动生成，确认即可）
DATABASE_URL=postgresql://ozon:自动生成的密码@localhost:5432/ozon_analytics

# 加密密钥和 JWT 密钥（setup.sh 已自动生成）
OZON_ENCRYPTION_KEY=已自动生成
OZON_JWT_SECRET=已自动生成

# ⚠️ 重要：替换为你的真实服务器 IP
CORS_ORIGINS=http://你的服务器IP
FRONTEND_URL=http://你的服务器IP

# 如果服务器在中国，访问俄罗斯 Ozon API 可能需要代理
# OZON_PROXY_URL=http://your-proxy:port
```

### 第四步：启动服务

```bash
# 重新加载 systemd 配置
systemctl daemon-reload

# 设置开机自启
systemctl enable ozon-analytics-web ozon-analytics-scheduler

# 启动服务
systemctl start ozon-analytics-web ozon-analytics-scheduler

# 重启 Nginx
systemctl restart nginx
```

### 第五步：验证

```bash
# 检查服务状态
systemctl status ozon-analytics-web
systemctl status ozon-analytics-scheduler

# 检查数据库连接
cd /opt/ozon-analytics/backend
/opt/ozon-analytics/venv/bin/python -c "
from database import engine
with engine.connect() as conn:
    print('✅ PostgreSQL 连接成功')
"
```

浏览器访问 `http://你的服务器IP`，应该看到登录页面。

注册第一个账号 → 绑定 Ozon 店铺 → 同步数据。

## 日常更新

在服务器上运行一键更新脚本：

```bash
sudo bash /opt/ozon-analytics/deploy/deploy.sh
```

该脚本会自动：拉取代码 → 更新依赖 → 构建前端 → 检查迁移 → 重启服务

或手动操作：

```bash
cd /opt/ozon-analytics
git pull origin main

# 更新 Python 依赖
/opt/ozon-analytics/venv/bin/pip install -r backend/requirements.txt

# 构建前端
cd frontend && npm install && npm run build && cd ..

# 重启服务
systemctl restart ozon-analytics-web ozon-analytics-scheduler
```

## 日志查看

```bash
# Web 服务日志
journalctl -u ozon-analytics-web -f --no-pager -n 50

# Scheduler 日志
journalctl -u ozon-analytics-scheduler -f --no-pager -n 50

# Nginx 访问日志
tail -f /var/log/nginx/ozon-analytics-access.log

# 应用文件日志
tail -f /var/log/ozon-analytics/web.log
tail -f /var/log/ozon-analytics/scheduler.log
```

## 数据库管理

### 连接数据库

```bash
su - postgres
psql -d ozon_analytics

# 或使用连接串
psql postgresql://ozon:密码@localhost:5432/ozon_analytics
```

### 数据库备份

```bash
# 手动备份
sudo -u postgres pg_dump ozon_analytics > /tmp/ozon_analytics_backup_$(date +%Y%m%d).sql

# 使用备份脚本
bash /opt/ozon-analytics/deploy/backup.sh
```

### 数据库迁移

生产环境使用 PostgreSQL 时，Alembic 迁移会在服务启动时自动执行。

如需手动运行迁移：

```bash
cd /opt/ozon-analytics/backend
/opt/ozon-analytics/venv/bin/alembic upgrade head
```

## 防火墙配置

```bash
# 开放 HTTP 端口
ufw allow 80/tcp

# 开放 SSH 端口
ufw allow 22/tcp

# 确保数据库端口不对外暴露
# PostgreSQL 只监听 127.0.0.1（默认配置，无需修改）
```

## 常见问题

### 国内服务器访问 Ozon API 慢/不可达

配置 `OZON_PROXY_URL` 指向一个可用的 HTTP 代理：

```ini
# .env
OZON_PROXY_URL=http://your-proxy-host:port
```

### 502 Bad Gateway

Gunicorn 进程可能挂了，检查日志：

```bash
journalctl -u ozon-analytics-web --no-pager -n 30
```

### CORS 错误（浏览器控制台报错）

确认 `.env` 中 `CORS_ORIGINS` 包含正确的地址：

```ini
# 确保包含你浏览器地址栏中显示的完整地址
CORS_ORIGINS=http://你的服务器IP
```

修改后重启服务：

```bash
systemctl restart ozon-analytics-web
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
systemctl status postgresql

# 检查连接
su - postgres -c "psql -d ozon_analytics -c 'SELECT 1;'"

# 检查 .env 中 DATABASE_URL 是否正确
grep DATABASE_URL /opt/ozon-analytics/.env
```

### 前端白屏/静态文件 404

确认前端已构建：

```bash
ls -la /opt/ozon-analytics/frontend/dist/
# 应该能看到 index.html 和 assets/ 目录
```

如果没有 dist 目录：

```bash
cd /opt/ozon-analytics/frontend
npm install
npm run build
```

### 切换到域名 + HTTPS

当有域名后，修改 Nginx 配置并使用 certbot 申请免费 SSL 证书：

```bash
# 安装 certbot
apt install -y certbot python3-certbot-nginx

# 修改 Nginx server_name
# 编辑 /etc/nginx/sites-available/ozon-analytics.conf
# 将 server_name _; 改为 server_name your-domain.com;

# 申请 SSL 证书（自动修改 Nginx 配置）
certbot --nginx -d your-domain.com

# 更新 .env
# CORS_ORIGINS=https://your-domain.com
# FRONTEND_URL=https://your-domain.com

# 重启服务
systemctl restart ozon-analytics-web nginx
```

## 服务器配置参考

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| CPU | 2核+ | Gunicorn 默认 4 Worker |
| 内存 | 4G+ | PostgreSQL + Python + Node.js 构建 |
| 硬盘 | 40G+ SSD | 数据库 + 日志 |
| PostgreSQL | 15+ | `apt install postgresql` |
| Python | 3.12+ | `python3 -V` 确认 |
| Node.js | 20+ | `node --version` 确认 |
