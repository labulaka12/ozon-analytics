# Ozon Analytics 开发日志

> 最后更新: 2026-06-05
> 项目路径: `C:\Users\Administrator\WorkBuddy\2026-06-04-11-46-07\ozon-analytics\`

---

## 一、项目概述

**Ozon 数据分析看板** — 基于 Ozon Seller API 的店铺数据采集、存储与可视化系统。支持多店铺绑定、商品同步、每日分析数据自动采集，提供前端看板展示与 CSV 导出。

**业务背景**: 用户（杨道帆）运营多个 Ozon 店铺，需要集中监控搜索曝光、浏览量、加购率、转化率、销售额等核心指标，替代 Ozon 后台逐店查看的低效流程。

---

## 二、技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.13 + FastAPI 0.115.6 | REST API 服务 |
| ORM | SQLAlchemy 2.0.36 | 数据模型 & 查询 |
| 数据库 | SQLite | 文件数据库, 位于 `data/ozon_analytics.db` |
| 定时任务 | APScheduler 3.11.0 | 每日 08:00 自动同步分析数据 |
| 前端 | 原生 HTML + ECharts 5.5.1 | 单文件 SPA, 无框架 |
| 加密 | cryptography (Fernet) | API Key 加密存储 |
| HTTP | requests 2.32.3 | Ozon API 调用 |

**运行环境**: Python venv (`C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\`)
**端口**: 8848
**启动方式**: `一键启动.bat` 或 `cd backend && python start_server.py`

---

## 三、目录结构

```
ozon-analytics/
├── .env.example           # 环境变量模板
├── .env                   # 实际环境变量（不提交）
├── .gitignore
├── requirements.txt       # Python 依赖（根级，旧版）
├── 一键启动.bat            # 启动脚本（自动检测 venv）
├── run.bat                # 旧版启动脚本
├── start.bat              # 旧版启动脚本
├── backend/
│   ├── main.py            # FastAPI 主入口（路由、生命周期、静态文件）
│   ├── models.py          # SQLAlchemy 模型（Store / Product / AnalyticsDaily / SyncLog）
│   ├── database.py        # 数据库连接配置（SQLite）
│   ├── ozon_client.py     # Ozon Seller API 客户端封装
│   ├── scheduler.py       # 数据同步调度器（商品 + 分析数据）
│   ├── crypto.py          # Fernet 对称加密（API Key 保护）
│   ├── start_server.py    # uvicorn 启动脚本
│   ├── requirements.txt   # Python 依赖（backend 级）
│   └── uvicorn.log        # 运行日志
├── frontend/
│   └── index.html         # 前端看板（~59KB 单文件 SPA）
└── data/
    ├── ozon_analytics.db  # SQLite 数据库文件
    └── .encryption_key    # Fernet 加密密钥（开发模式自动生成）
```

---

## 四、数据模型

### Store（店铺）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| name | String(100) | 店铺名称 |
| client_id | String(50) | Ozon Client-Id |
| api_key | String(200) | Ozon Api-Key（Fernet 加密存储） |
| is_active | Boolean | 是否启用 |
| last_sync_at | DateTime | 最后同步时间 |
| created_at / updated_at | DateTime | 时间戳 |

### Product（商品）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增ID |
| store_id | Integer FK | 所属店铺 |
| offer_id | String(100) | 卖家货号 |
| product_id | Integer | Ozon 商品ID |
| sku | Integer | SKU |
| name | String(500) | 商品名称 |
| category | String(200) | 类目 |
| price / old_price | Float | 价格 |
| currency | String(10) | 货币（默认 RUB） |
| barcode | String(50) | 条形码 |
| status | String(50) | 商品状态 |
| images | Text | 图片URL（JSON数组） |

**唯一约束**: `(store_id, product_id)`

### AnalyticsDaily（每日分析数据）

| 字段 | 类型 | 说明 |
|------|------|------|
| store_id | Integer | 店铺ID |
| product_id | Integer | 商品ID |
| offer_id | String(100) | 卖家货号 |
| sku | Integer | SKU |
| date | Date | 日期 |
| impressions_search | Integer | 搜索曝光量 |
| views_pdp | Integer | 商品页浏览量 |
| views_total | Integer | 总浏览量 |
| sessions | Integer | 会话数 |
| add_to_cart | Integer | 加购数 |
| conversion_to_cart | Float | 加购率(%) |
| ctr | Float | 搜索点击率(%) |
| order_conversion | Float | 订单转化率(%) |
| ordered_units | Integer | 下单件数 |
| revenue | Float | 销售额(RUB) |
| returns_count | Integer | 退货数 |
| cancellations | Integer | 取消数 |
| position_avg | Float | 平均搜索排名 |

**唯一约束**: `(store_id, product_id, date)`

### SyncLog（同步日志）

| 字段 | 类型 | 说明 |
|------|------|------|
| store_id | Integer | 店铺ID |
| sync_type | String(50) | 同步类型: products / analytics |
| status | String(20) | 状态: success / error |
| message | Text | 日志信息 |

---

## 五、API 端点

### 店铺管理
- `GET /api/stores` — 店铺列表（api_key 脱敏为前8位+***）
- `POST /api/stores` — 绑定店铺（先验证 API 连通性，成功后后台异步同步商品+分析）
- `PUT /api/stores/{id}` — 更新店铺
- `DELETE /api/stores/{id}` — 删除店铺（级联删除关联数据）

### 商品管理
- `GET /api/products?store_id=` — 商品列表
- `GET /api/products/{product_id}?store_id=` — 商品详情

### 分析数据
- `GET /api/analytics?store_id=&product_ids=&date_from=&date_to=` — 分析数据明细
- `GET /api/analytics/summary?store_id=&product_ids=&date_from=&date_to=` — 分析数据汇总

### 数据同步
- `POST /api/sync/{sync_type}` — 手动触发同步（products / analytics / all）
  - body: `{ store_id, target_date?, target_dates?, product_ids? }`
- `GET /api/sync/logs?store_id=&limit=` — 同步日志

### 数据导出
- `GET /api/export/csv?store_id=&date_from=&date_to=` — CSV 导出（UTF-8 BOM）

### 静态文件
- `GET /` — 首页重定向到看板
- `/static/*` — 前端静态文件

---

## 六、核心业务逻辑

### 6.1 数据同步流程

```
绑定店铺 → API 连通性检查 → 后台异步:
  ├─ sync_products_for_store()
  │   1. get_all_products()（自动翻页，限速 0.3s/页）
  │   2. get_product_info_list()（批量获取详情）
  │   3. get_product_prices()（批量获取价格）
  │   4. UPSERT 到 products 表
  │
  └─ sync_analytics_for_store()
      1. get_all_analytics_data()（按 SKU+天 维度，自动翻页，限速 1.5s/页）
      2. 解析 Ozon Analytics 返回格式（dimensions + metrics）
      3. 批量预加载 SKU→Product 映射（避免 N+1）
      4. 计算衍生指标: CTR, 加购率, 订单转化率
      5. UPSERT 到 analytics_daily 表
```

### 6.2 Ozon API 关键约束

| 约束 | 说明 |
|------|------|
| 库存更新频率 | 同一仓库同一商品 2分钟/次 |
| 商品创建 | 每请求最多100个，每日有配额 |
| 价格更新 | 每次最多1000个商品 |
| Analytics 指标 | 最多14个 metrics/请求 |
| Analytics 翻页 | offset 分页，每页最多1000条 |
| 频率限制 | 429 限流自动重试（指数退避，最多10次） |

### 6.3 安全设计

- **API Key 加密存储**: Fernet 对称加密，密钥来自环境变量 `OZON_ENCRYPTION_KEY` 或自动生成文件 `data/.encryption_key`
- **API Key 脱敏**: 列表接口仅返回 `client_id[:8] + "***"`
- **代理隔离**: `OzonClient` 默认禁用系统代理（`trust_env=False`），仅使用显式配置的 `OZON_PROXY_URL`
- **CORS**: 默认仅允许 `localhost:8848`

### 6.4 定时任务

- 每日 08:00 (Asia/Shanghai) 自动同步所有活跃店铺的分析数据
- 使用 APScheduler BackgroundScheduler
- 仅同步分析数据，不同步商品列表

---

## 七、Ozon Seller API 参考文档

完整 API 文档位于项目根目录: `Ozon_Seller_API_参考文档.md`

**关键端点速查**:

| 功能 | 端点 | 说明 |
|------|------|------|
| 商品列表 | `/v3/product/list` | 分页，limit 最大100 |
| 商品详情 | `/v3/product/info/list` | 批量查询 |
| 价格查询 | `/v5/product/info/prices` | 批量查询 |
| 库存查询 | `/v3/product/info/stocks` | 分页 |
| 分析数据 | `/v1/analytics/data` | 核心分析接口，最多14指标 |
| FBS订单 | `/v3/posting/fbs/list` | 分页+筛选 |
| 财务交易 | `/v3/finance/transaction/list` | 分页 |

---

## 八、环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `OZON_ENCRYPTION_KEY` | 否 | Fernet 加密密钥，不设则自动生成 |
| `CORS_ORIGINS` | 否 | 前端源，逗号分隔，默认 localhost:8848 |
| `OZON_PROXY_URL` | 否 | HTTP 代理（国内访问 Ozon API 需要） |
| `SERVER_PORT` | 否 | 服务端口，默认 8848 |

---

## 九、前端看板

- **技术**: 原生 HTML + ECharts 5.5.1，单文件 SPA（`frontend/index.html`，约59KB）
- **功能**: 店铺管理、商品选择、日期筛选、趋势图表、数据表格、CSV 导出
- **设计**: 蓝白配色，卡片式布局，响应式

---

## 十、已知问题 & 待改进

### 已知问题
1. **代理依赖**: 国内服务器直连 Ozon API 不稳定，需配置 `OZON_PROXY_URL`
2. **Ozon API 限流**: 429 频率限制可能影响批量同步，当前已做指数退避重试
3. **SQLite 并发**: 多用户同时写入可能锁库，当前单用户场景无问题

### 待改进方向
1. **财务数据同步**: `ozon_client.py` 已实现 `get_finance_transactions()` 和 `get_realization()`，但尚未接入同步调度
2. **订单数据同步**: `ozon_client.py` 已实现 `get_fbo_orders()` 和 `get_fbs_orders()`，但尚未接入
3. **多维度分析**: 当前仅按 SKU+天 维度，可扩展类目/品牌维度
4. **告警机制**: 指标异常时主动通知（如转化率骤降）
5. **数据备份**: SQLite 定期备份策略
6. **用户认证**: 当前无登录机制，仅适合内网使用

---

## 十一、快速启动

```bash
# 1. 创建虚拟环境（如未创建）
python -m venv C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics

# 2. 安装依赖
C:\Users\Administrator\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\pip install -r backend\requirements.txt

# 3. 配置环境变量
copy .env.example .env
# 编辑 .env 填入代理等配置

# 4. 启动服务
cd backend && ..\..\..\..\..\..\..\..\.workbuddy\binaries\python\envs\ozon-analytics\Scripts\python.exe start_server.py

# 5. 访问看板
# 浏览器打开 http://localhost:8848
```

或直接双击 `一键启动.bat`

---

## 十二、变更记录

| 日期 | 变更 |
|------|------|
| 2026-06-04 | 项目初始化：搭建 FastAPI 后端 + 原生前端看板 |
| 2026-06-04 | 实现 Ozon API 客户端封装（商品/分析/订单/财务） |
| 2026-06-04 | 实现数据同步调度器（商品列表 + 每日分析数据） |
| 2026-06-04 | 实现 API Key Fernet 加密存储 |
| 2026-06-04 | 整理 Ozon Seller API 参考文档（Postman Collection → Markdown） |
| 2026-06-04 | 实现前端看板（ECharts 图表 + 数据表格） |
| 2026-06-05 | 添加一键启动脚本（自动检测 venv） |
| 2026-06-05 | 编写开发日志 |
