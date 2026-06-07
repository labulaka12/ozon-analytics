# Ozon Analytics SaaS 改造 — 阶段一 PRD

## 1. 项目信息

- **Language**: 中文
- **Programming Language**: Python (FastAPI) + SQLAlchemy + 单文件 HTML/JS (ECharts)
- **Project Name**: ozon_analytics_saas
- **原始需求**: 将现有的单用户本地 Ozon 数据分析工具改造为多租户 SaaS 平台的基础骨架。跑通「用户注册 → 登录 → 绑定店铺 → 查看数据」的完整闭环。
- **当前状态**: 单用户应用，无用户系统，无认证，所有 API 直接面向单用户。技术栈为 FastAPI + SQLAlchemy + SQLite + 单文件前端 SPA。

## 2. 产品定义

### 2.1 产品目标

1. **建立用户系统基础**：引入 User 模型和 JWT 认证机制，将匿名应用转变为可注册登录的多用户应用
2. **实现数据隔离**：所有业务数据（店铺/商品/分析/日志）绑定到所属用户，API 按登录用户过滤，确保租户间数据不可见
3. **打通业务闭环**：在前端 SPA 中增加登录/注册页面，用户可完成注册→登录→绑定店铺→查看分析数据的完整流程

### 2.2 用户故事

| 角色 | 需求 | 价值 |
|------|------|------|
| 作为**新用户**，我想要**注册账号（邮箱+密码）**，以便**开始使用 Ozon 数据分析服务** |
| 作为**已注册用户**，我想要**用邮箱和密码登录系统**，以便**访问我的店铺数据** |
| 作为**登录用户**，我想要**绑定我的 Ozon 店铺**，以便**查看该店铺的商品和分析数据** |
| 作为**多账号用户**，我想要**我的数据与其他用户完全隔离**，以便**我的商业数据安全保密** |
| 作为**登录用户**，我想要**退出登录**，以便**确保其他人在我的设备上无法访问数据** |
| 作为**注册用户**，我想要**登录状态持久化**（自动刷新 token），以便**在有效期内无需反复登录** |

## 3. 技术规范

### 3.1 需求池

#### P0（必须，上线必备）

| 编号 | 需求 | 说明 |
|------|------|------|
| P0-1 | **新建 User 模型** | 在 `models.py` 中新增 `User` 表，包含 id、email（唯一）、hashed_password、is_active、created_at、updated_at。密码使用 `passlib` 的 bcrypt 哈希 |
| P0-2 | **用户注册 API** | `POST /api/auth/register` — 接收 email + password，校验邮箱格式和密码强度（>=6位），返回用户信息（不含密码） |
| P0-3 | **用户登录 API** | `POST /api/auth/login` — 验证 email + password，返回 JWT token（含 user_id 和过期时间）。使用 `python-jose` 签发和验签 |
| P0-4 | **JWT 认证中间件** | 创建 `get_current_user` 依赖函数，从 `Authorization: Bearer <token>` 中解析并验证 JWT，注入当前用户到路由处理函数 |
| P0-5 | **所有业务表增加 user_id** | Store、Product、AnalyticsDaily、SyncLog 四张表各新增 `user_id = Column(Integer, nullable=False)` 字段。同步更新唯一约束和索引 |
| P0-6 | **所有 API 按用户过滤数据** | 当前的所有业务 API（店铺 CRUD、商品查询、分析数据、同步、导出）必须添加 `user_id` 过滤。用户只能操作自己名下的数据 |
| P0-7 | **注册/登录前端页面** | 在 `index.html` 中新增登录页和注册页 UI。两个页面间可切换（"已有账号？去登录" / "没有账号？去注册"）。表单验证（空值、邮箱格式、密码长度） |
| P0-8 | **前端虚拟路由** | 在现有 SPA 中通过 JS 实现虚拟路由：`#login` / `#register` / `#dashboard`。登录成功后跳转 dashboard，未登录时跳转 login |
| P0-9 | **前端请求携带 JWT** | 所有 API 请求在 `Authorization` header 中附带 JWT token（从 localStorage 读取） |
| P0-10 | **前端路由守卫** | 页面初始化时检查 localStorage 中的 token。token 不存在或已过期则跳转到登录页 |
| P0-11 | **APScheduler 独立进程** | 将定时任务拆出为独立进程（`scheduler_worker.py`），通过命令行参数与主应用分离。Gunicorn 多 worker 下不再重复执行定时任务 |

#### P1（重要，但可后补）

| 编号 | 需求 | 说明 |
|------|------|------|
| P1-1 | **密码重置** | 提供"忘记密码"流程：`POST /api/auth/forgot-password` 发送重置邮件 + `POST /api/auth/reset-password` 重置密码 |
| P1-2 | **Token 续期** | JWT 短期过期（如 24 小时），前端检测 401 后尝试用 refresh_token 续期；或实现静默刷新机制 |
| P1-3 | **数据库迁移(Alembic)** | 引入 Alembic 管理 schema 变更，生成 `add_user_id` 等迁移脚本，确保生产环境平滑升级 |
| P1-4 | **退出登录** | 前端清除 localStorage token，跳转登录页。后端可维护 token 黑名单（可选） |

#### P2（增强体验）

| 编号 | 需求 | 说明 |
|------|------|------|
| P2-1 | **邮箱验证** | 注册后发送验证邮件，用户点击链接验证后才可登录 |
| P2-2 | **个人信息编辑** | 修改密码、头像、昵称等 |
| P2-3 | **多语言支持** | 前端 UI 支持中/英切换 |

### 3.2 数据模型变更

#### 新增 User 表

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

#### 现有表变更

所有业务表增加 `user_id` 字段：

| 表名 | 新增字段 | 索引变更 |
|------|---------|---------|
| stores | `user_id = Column(Integer, nullable=False)` | 新增 `idx_stores_user` |
| products | `user_id = Column(Integer, nullable=False)` | 新增 `idx_products_user` |
| analytics_daily | `user_id = Column(Integer, nullable=False)` | 新增 `idx_analytics_daily_user` |
| sync_logs | `user_id = Column(Integer, nullable=False)` | 新增 `idx_sync_logs_user` |

唯一约束更新：原 `uq_store_product(store_id, product_id)` 需加上 user_id 维度的考量；原 `uq_analytics_daily(store_id, product_id, date)` 同理。

### 3.3 API 变更

#### 新增 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册（email + password），返回用户信息 |
| POST | `/api/auth/login` | 用户登录，返回 JWT token + 用户信息 |
| GET | `/api/auth/me` | 获取当前登录用户信息 |

#### 已有 API 变更

所有已有 API 端点增加 `user_id` 过滤。由 `get_current_user` 依赖注入当前用户对象，在查询条件中自动追加：

```python
# 示例: list_stores
@app.get("/api/stores")
def list_stores(current_user = Depends(get_current_user), db = Depends(get_db)):
    stores = db.query(Store).filter_by(user_id=current_user.id).all()
    ...
```

受影响的端点清单：
- `GET /api/stores`
- `POST /api/stores`
- `PUT /api/stores/{store_id}`
- `DELETE /api/stores/{store_id}`
- `GET /api/products`
- `GET /api/products/{product_id}`
- `GET /api/analytics`
- `GET /api/analytics/summary`
- `POST /api/sync/{sync_type}`
- `GET /api/sync/logs`
- `GET /api/export/csv`

### 3.4 新增依赖

在 `requirements.txt` 中新增：

```
python-jose[cryptography]==3.3.0   # JWT 签发和验证
passlib[bcrypt]==1.7.4             # 密码哈希
```

### 3.5 前端变更

#### 页面结构

在现有单文件 SPA 中新增两个视图，通过 `showPage('login')` / `showPage('register')` / `showPage('dashboard')` 切换显示/隐藏：

**登录页（#login）**
- Ozon Analytics 品牌 Logo / 标题
- 邮箱输入框 + 密码输入框
- "登录"按钮
- "没有账号？去注册"链接
- 表单验证：邮箱格式、非空检查
- 登录失败显示错误提示（如"邮箱或密码错误"）

**注册页（#register）**
- 邮箱输入框 + 密码输入框 + 确认密码输入框
- "注册"按钮
- "已有账号？去登录"链接
- 表单验证：邮箱格式、密码长度>=6、两次密码一致
- 注册成功自动跳转登录页并显示成功提示

**看板页（#dashboard）—— 已有逻辑，保持不变**
- 顶部 header 增加用户信息显示和"退出登录"按钮

#### 路由逻辑

```javascript
// 虚拟路由 dispatch
function routePage() {
    const hash = window.location.hash || '#login';
    if (hash === '#login') showPage('login');
    else if (hash === '#register') showPage('register');
    else if (hash === '#dashboard') showPage('dashboard');
    else window.location.hash = '#login';
}

// 路由守卫
function requireAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) { window.location.hash = '#login'; return false; }
    return true;
}

// 所有 API 请求携带 token
async function apiFetch(url, options = {}) {
    const token = localStorage.getItem('access_token');
    const headers = { ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(url, { ...options, headers });
    if (resp.status === 401) {
        localStorage.removeItem('access_token');
        window.location.hash = '#login';
        throw new Error('登录已过期，请重新登录');
    }
    return resp;
}
```

### 3.6 架构变更：APScheduler 独立进程

**问题**：Gunicorn 启动 4 个 worker 进程，每个都会初始化 APScheduler，导致定时任务重复执行 4 次。

**方案**：将 APScheduler 拆出为独立进程 `scheduler_worker.py`

```
backend/
├── main.py              # FastAPI 应用（Gunicorn 启动，不含调度器）
├── scheduler_worker.py   # 独立调度器进程（单独启动）
├── scheduler.py          # 同步逻辑函数（两个进程共享）
└── ...
```

`render.yaml` 更新为双服务：

```yaml
services:
  - type: web
    name: ozon-analytics-web
    startCommand: gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker ...
  - type: worker
    name: ozon-analytics-scheduler
    startCommand: python backend/scheduler_worker.py
```

## 4. UI 设计稿

### 登录页布局

```
┌─────────────────────────────────────────────────┐
│                                                 │
│                    ┌─────────┐                  │
│                    │  Logo    │                  │
│                    └─────────┘                  │
│                                                 │
│              Ozon Analytics                     │
│              数据分析平台                         │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  邮箱                                    │    │
│  │  [________________________________]     │    │
│  │                                         │    │
│  │  密码                                    │    │
│  │  [________________________________]     │    │
│  │                                         │    │
│  │  ┌─────────────────────────────────┐    │    │
│  │  │           登 录                  │    │    │
│  │  └─────────────────────────────────┘    │    │
│  │                                         │    │
│  │     没有账号？<去注册>                    │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 注册页布局

```
┌─────────────────────────────────────────────────┐
│                                                 │
│                    ┌─────────┐                  │
│                    │  Logo    │                  │
│                    └─────────┘                  │
│                                                 │
│              创建账号                            │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │  邮箱                                    │    │
│  │  [________________________________]     │    │
│  │                                         │    │
│  │  密码（至少6位）                          │    │
│  │  [________________________________]     │    │
│  │                                         │    │
│  │  确认密码                                │    │
│  │  [________________________________]     │    │
│  │                                         │    │
│  │  ┌─────────────────────────────────┐    │    │
│  │  │           注 册                  │    │    │
│  │  └─────────────────────────────────┘    │    │
│  │                                         │    │
│  │     已有账号？<去登录>                    │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 看板页 header 变更

在现有 header 右侧增加用户信息：

```
┌─────────────────────────────────────────────────┐
│  Ozon Analytics  [BETA]       user@example.com ▼│
│                                                [退出] │
└─────────────────────────────────────────────────┘
```

## 5. 待确认问题

1. **数据库迁移策略**：现有 SQLite 数据库文件中已有数据（老用户的店铺和商品），新增 `user_id` 字段后，存量数据如何处理？
   - 建议：开发环境直接删库重建（SQLite 无数据迁移负担）
   - 生产环境：通过 Alembic 迁移脚本，给所有存量数据设置 `user_id = 1`（适配为第一个管理员用户）

2. **JWT 过期时间**：token 有效期多长比较合适？
   - 建议：短期 access_token（24 小时）+ refresh_token（7 天），或简单方案 access_token 72 小时。
   - 需要确认是否有更高的安全要求（如 2 小时过期 + refresh 机制）

3. **密码强度要求**：密码最少长度及复杂度要求？
   - 建议：最少 6 位。是否需要字母+数字组合规则？
   - 如果需要更严格的安全策略，建议 8 位以上 + 大小写字母 + 数字

4. **注册方式**：阶段一是否开放"任何人都可注册"，还是需要管理员审核/邀请码？
   - 建议：阶段一开放注册（SaaS 模式常态），后续再考虑白名单限制

5. **前端单文件 SPA 的规模**：加入登录/注册逻辑和路由后，index.html 会超过 1500 行。是否接受继续膨胀，还是考虑引入极简的模块拆分（如将 JS 逻辑拆入独立 .js 文件）？
   - 建议：阶段一保持单文件，阶段二再评估拆分

6. **APScheduler 独立进程**：在 Render 上启动 worker 服务会额外产生费用。是否考虑其他方案（如使用 Render Cron Jobs + HTTP trigger，或轻量级 `schedule` 库在 web 进程单 worker 模式下运行）？
   - 建议：阶段一使用环境变量 `ENABLE_SCHEDULER=true` 在 web 进程中条件启动，后续再独立部署调度器

7. **注册时演示数据**：是否需要在用户注册时自动创建一个演示店铺并同步示例数据，以便用户注册后立即看到效果？
   - 建议：作为 P1 功能，阶段一不做自动演示数据

8. **加密密钥隔离**：当前 `crypto.py` 使用统一的 encryption_key 加密所有用户的 API Key。SaaS 场景下是否需要每个用户单独的加密密钥，或者使用同一个密钥 + user_id 衍生加密？
   - 建议：阶段一保持统一密钥，阶段二再升级为按用户派生密钥
