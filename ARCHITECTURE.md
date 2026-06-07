# Ozon Analytics — 系统架构设计文档

> 版本: v1.0 | 作者: Software Architect | 日期: 2026-06-05
> 适用团队规模: 1-3 人 | 设计原则: 渐进式演进，不过度设计

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [当前架构评估](#2-当前架构评估)
3. [目标架构](#3-目标架构)
4. [架构决策记录](#4-架构决策记录)
5. [有界上下文与领域模型](#5-有界上下文与领域模型)
6. [目录结构与代码组织](#6-目录结构与代码组织)
7. [分阶段实施路线图](#7-分阶段实施路线图)
8. [质量属性分析](#8-质量属性分析)

---

## 1. 执行摘要

Ozon Analytics 是一个面向多店铺 Ozon 卖家的数据分析看板系统。当前处于 **MVP 阶段**——单体架构（FastAPI + SQLite + 原生 SPA），功能已验证但存在大量技术债务。

**核心目标：** 在不引入过度复杂性的前提下，将系统从"能运行"演进为"可维护、可扩展、可交付"。

**架构策略：** 采用 **分层模块化单体（Layered Modular Monolith）**——保持单一部署单元降低运维成本，通过清晰的层边界、服务抽象和仓库模式实现内聚与解耦。仅在性能瓶颈或独立扩展需求确实出现时，才考虑拆分为微服务。

**关键权衡：**

| 选择 | 得 | 失 |
|------|----|----|
| 分层单体 → 非微服务 | 低运维成本、单一事务边界、调试简单 | 无法独立水平扩展某些模块 |
| 保留 SQLite → 逐步迁移 PostgreSQL | 当前零迁移成本 | 并发写入受限，不适合多用户 |
| 原生前端 → 不动框架 | 零构建步骤，技术债务最低 | 代码组织松散，长线维护成本高 |
| Repository Pattern | 数据库可切换、可 mock 测试 | 增加一层抽象，小项目初期感知不到收益 |

---

## 2. 当前架构评估

### 2.1 现状快照

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Monolith (单一进程, uvicorn)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  main.py    │  │ models.py    │  │ ozon_client  │   │
│  │  (路由+模型) │  │ database.py  │  │ crypto       │   │
│  │  526行      │  │              │  │ scheduler    │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
│                         │                                │
│                    ┌────┴────┐                          │
│                    │ SQLite  │                          │
│                    └─────────┘                          │
│                         │                                │
│                    ┌────┴────┐                          │
│                    │ index.html (59KB 原生 SPA)          │
│                    │ ECharts 5.5.1                       │
│                    └─────────┘                          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 主要问题

| 分类 | 问题 | 严重度 |
|------|------|--------|
| **架构** | main.py 混合路由、Pydantic 模型、工具函数，无分层 | 🔴 高 |
| **架构** | 无 Service/Repository 层，业务逻辑散落在路由和客户端中 | 🔴 高 |
| **测试** | 零测试覆盖 | 🔴 高 |
| **安全** | 无用户认证和授权 | 🟡 中 |
| **数据** | SQLite 并发受限，且无迁移管理 | 🟡 中 |
| **前端** | 原生 JS 单文件 1234 行，无模块化 | 🟡 中 |
| **功能** | 财务/订单 API 已实现但未接入 | 🟢 低 |
| **运维** | 无 Dockerfile，无 CI/CD | 🟢 低 |
| **依赖** | 根目录和 backend/ 下各有一份 requirements.txt | 🟢 低 |

### 2.3 当前优势（不应丢失）

- FastAPI + SQLAlchemy + APScheduler 技术栈选择合理
- Fernet 加密存储 API Key 的安全策略正确
- CORS 白名单限制得当
- OzonClient 的重试/限流处理完善
- 定时任务设计合理（异步 BackgroundScheduler）
- 前端 ECharts 看板功能完整

---

## 3. 目标架构

### 3.1 分层架构总览

```
┌────────────────────────────────────────────────────────────────────────┐
│  Layer 1: PRESENTATION (presentation/)                                │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────────┐     │
│  │ Routers  │ │ Pydantic     │ │ Auth     │ │ Frontend         │     │
│  │ (api/v1) │ │ Schema       │ │ Middle   │ │ (React/Vue SPA)  │     │
│  └──────────┘ └──────────────┘ └──────────┘ └──────────────────┘     │
│  → 职责: HTTP 处理、请求校验、序列化、认证                           │
│  → 规则: 不含任何业务逻辑                                           │
├────────────────────────────────────────────────────────────────────────┤
│  Layer 2: APPLICATION (service/)                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐           │
│  │ Store    │ │ Product  │ │Analytics │ │ Sync         │           │
│  │ Service  │ │ Service  │ │ Service  │ │ Orchestrator │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘           │
│  → 职责: 用例编排、事务管理、跨实体协调                               │
│  → 规则: 依赖 Domain 层，对 Infrastructure 层仅通过接口依赖          │
├────────────────────────────────────────────────────────────────────────┤
│  Layer 3: DOMAIN (domain/)                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Store    │ │ Product  │ │Analytics │ │ Finance  │ │ Order    │  │
│  │ Entity   │ │ Entity   │ │ Entity   │ │ Entity   │ │ Entity   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Domain Events: ProductSynced, AnalyticsUpdated, OrderPlaced...  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│  → 职责: 业务实体、不变量、领域逻辑                                  │
│  → 规则: 零外部依赖（纯 Python），不依赖 FastAPI/SQLAlchemy          │
├────────────────────────────────────────────────────────────────────────┤
│  Layer 4: INFRASTRUCTURE (infrastructure/)                           │
│  ┌──────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐       │
│  │ OzonClient   │ │ Repository │ │ Crypto     │ │ Task     │       │
│  │ (API 客户端) │ │ (持久化)    │ │ (加密)      │ │ Queue    │       │
│  └──────────────┘ └────────────┘ └────────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                             │
│  │PostgreSQL│ │  Redis   │ │ RabbitMQ │  ← 可选，渐进引入            │
│  └──────────┘ └──────────┘ └──────────┘                             │
│  → 职责: 外部集成、数据持久化、消息传递                               │
│  → 规则: 依赖倒置，实现 Domain 层定义的接口                           │
└────────────────────────────────────────────────────────────────────────┘

核心原则: 依赖反转（Dependency Inversion）
- Domain 层定义接口（Repository 抽象、API Client 抽象）
- Infrastructure 层实现这些接口
- 依赖方向永远向内: Presentation → Application → Domain ← Infrastructure
```

### 3.2 数据流示例

以"用户查看分析看板 → 数据同步 → 显示图表"为例：

```
User Browser                          FastAPI App                        Ozon API
    │                                      │                               │
    ├─ GET /api/analytics?store_id=1 ──────┤                               │
    │                                      │                               │
    │                              ┌───────┴────────┐                     │
    │                              │ Router (v1)     │                     │
    │                              │ → 校验参数       │                     │
    │                              │ → 调用 Service   │                     │
    │                              └───────┬────────┘                     │
    │                                      │                               │
    │                              ┌───────┴────────┐                     │
    │                              │ AnalyticsService │                    │
    │                              │ → 查询 Repository │                   │
    │                              └───────┬────────┘                     │
    │                                      │                               │
    │                              ┌───────┴────────┐                     │
    │                              │ Repository      │                     │
    │                              │ → SQLAlchemy    │                     │
    │                              │ → PostgreSQL    │                     │
    │                              └───────┬────────┘                     │
    │                                      │                               │
    │◄───── JSON Response (ECharts data) ──┤                               │
    │                                      │                               │
    │ (如果数据不足，触发同步)               │                               │
    ├─ POST /api/sync/analytics ──────────┤                               │
    │                              ┌───────┴────────┐                     │
    │                              │ SyncOrchestrator│                    │
    │                              │ → OzonClient     │ ──── HTTP ──────►│
    │                              │ → Repository     │◄─── JSON ────────│
    │                              └─────────────────┘                    │
```

---

## 4. 架构决策记录

### ADR-001: 保持单体架构（Modular Monolith）

**状态：** Accepted

**上下文：**
- 当前团队 1 人（道帆），未来可能扩展至 2-3 人
- 系统当前为单用户数据看板工具
- 数据量级较小（4 家店铺，~1600 行分析数据/天）
- Ozon API 本身有速率限制（同一仓库同一商品 2 分钟/次）

**决策：**
保持单体部署，但重构为 **分层模块化单体**。所有代码在同一进程中运行，通过 Python 包（package）划分模块边界。

**理由：**
| 因素 | 单体优势 | 微服务代价 |
|------|---------|-----------|
| 部署复杂度 | 1 个服务 = 1 条命令 | N 个服务 = CI/CD + 容器编排 |
| 数据一致性 | 单事务边界，无需 Saga | 分布式事务，最终一致性 |
| 调试 | IDE 单步调试即可 | 需分布式追踪 |
| 团队规模 | 1-3 人可维护 | 5+ 人才有意义 |
| Ozon API 限流 | 单体限流容易控制 | 多服务共享配额需协调 |

**后果：**
- 好：运维简单，部署即一个 uvicorn 进程
- 好：所有数据在单一事务中，无需处理最终一致性
- 好：可以逐步重构，不必一次做完
- 差：如果未来用户规模爆发式增长，需拆分（但 Ozon API 限流本身就限制了数据规模）

---

### ADR-002: Service + Repository 分层

**状态：** Accepted

**上下文：**
- 当前业务逻辑散落在路由（main.py）、OzonClient 和调度器中
- 无法单元测试——测试一个路由需要启动整个应用
- 如果要切换数据库（SQLite → PostgreSQL），没有抽象层保护

**决策：**
引入标准的 **Service Layer** 和 **Repository Pattern**：

```
Router (presentation) → Service (application) → Repository (infrastructure)
                                                      ↓
                                               SQLAlchemy ORM (infrastructure)
```

**后果：**
- 好：业务逻辑可独立测试（Mock Repository）
- 好：数据库切换只需更换 Repository 实现
- 好：路由变得更薄，职责清晰
- 差：增加了一些样板代码（接口定义 + 实现）

---

### ADR-003: 逐步迁移到 PostgreSQL

**状态：** Proposed（Phase 2）

**上下文：**
- 当前使用 SQLite，在 Render 上需切换到 PostgreSQL
- SQLite 不支持并发写入（同一时间只能一个写连接）
- 如果需要多用户同时操作或未来有 Webhook 回调写入，SQLite 会成为瓶颈

**决策：**
分两步走：
1. **Phase 1**: 保持 SQLite，但通过 Repository 抽象消除对 SQLite 的直接依赖
2. **Phase 2**: 当需要部署到生产环境或出现写入冲突时，迁移到 PostgreSQL

**后果：**
- 好：当前零迁移成本，SQLite 对单用户开发友好
- 好：Repository 抽象保证了可切换性
- 差：Phase 2 迁移时需要处理现有数据导出导入

---

### ADR-004: 前端暂时保持原生 JS，但提取模块

**状态：** Accepted

**上下文：**
- 当前前端为单文件 index.html（1234 行原生 JS）
- 引入 Vue/React 需要构建工具链、npm 配置、开发服务器
- 当前看板功能有限，主要展示 6 个图表 + 表格

**决策：**
- **立即**：将 index.html 中的 JS 拆分为多个 .js 文件（charts.js, api.js, ui.js, store.js），通过 ES Module 方式加载
- **Phase 2** 再评估是否需要 Vue/React

**后果：**
- 好：零构建步骤，保留原生 HTML 的优势
- 好：模块拆分后代码可维护性大幅提升
- 差：如果未来需要复杂交互（实时推送、拖拽报表），原生 JS 开发效率低于框架
- Phase 2 升级到框架时，API 接口保持不变，仅重构前端展示层

---

### ADR-005: 引入测试金字塔

**状态：** Accepted

**上下文：**
- 当前零测试覆盖
- 重构过程中需要测试保护，否则不敢改代码
- 关键测试点：Ozon API 数据解析逻辑、同步去重逻辑、财务计算

**决策：**
按以下优先级逐步引入：

1. **Unit Tests**（Pytest）：Service 层 + 数据解析逻辑
2. **Integration Tests**：Repository + API 路由（使用 TestClient）
3. **E2E Tests**：看板页面（可选，Phase 2）

**后果：**
- 好：重构时有安全网，敢改代码
- 好：Ozon API 响应格式变化时能及时发现
- 差：需要投入时间写测试

---

### ADR-006: 差量同步策略

**状态：** Accepted

**上下文：**
- Ozon 分析 API 支持按日期范围查询
- 当前同步策略：每天 08:00 同步全部数据
- 分析数据不可逆（历史数据可能被 Ozon 修正）

**决策：**
```
每日同步流程:
  1. 获取所有最近 7 天的日期范围（含修正窗口）
  2. 对已有数据 UPSERT（覆盖更新，因为 Ozon 可能修正历史）
  3. 增量同步仅同步"未同步"的日期 + 最近 3 天（修正窗口）
```

**后果：**
- 好：减少 API 调用次数，规避 Ozon 限流
- 好：自动捕获 Ozon 对历史数据的修正
- 好：手动同步时只需选择缺失日期
- 差：需要额外的逻辑来管理同步状态

---

## 5. 有界上下文与领域模型

### 5.1 Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Ozon Analytics 系统                            │
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │ Store Mgt   │──▶│ Product Mgt │──▶│ Analytics   │               │
│  │ 店铺管理     │   │ 商品管理     │   │ 数据分析     │               │
│  │             │   │             │   │             │               │
│  │ - 绑定/解绑  │   │ - 商品列表   │   │ - 曝光/浏览  │               │
│  │ - API Key   │   │ - 价格/库存  │   │ - 转化漏斗   │               │
│  │ - 连通性检查 │   │ - 状态追踪   │   │ - 销售数据   │               │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘               │
│         │                 │                  │                       │
│         ▼                 ▼                  ▼                       │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │                    Sync Orchestrator                    │       │
│  │                   同步编排上下文                         │       │
│  │  - 编排多步骤同步流程                                    │       │
│  │  - 管理同步状态与日志                                    │       │
│  │  - 处理限流与重试                                        │       │
│  └──────────────────────┬──────────────────────────────────┘       │
│                         │                                            │
│                         ▼                                            │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │ Finance     │   │ Order       │   │ Alert       │               │
│  │ 财务管理     │   │ 订单管理     │   │ 告警通知     │               │
│  │ (Phase 2)   │   │ (Phase 2)   │   │ (Phase 3)   │               │
│  └─────────────┘   └─────────────┘   └─────────────┘               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 核心领域实体

#### Store（店铺聚合根）

```
Store {
  id: UUID
  name: str
  clientId: str (脱敏展示)
  apiKey: EncryptedSecret (Fernet 加密)
  isActive: bool
  lastSyncAt: datetime | None
  createdAt: datetime
  updatedAt: datetime

  // 行为
  connect(): HealthCheckResult
  updateCredentials(clientId, apiKey): void
  deactivate(): void
}
```

#### Product（商品实体）

```
Product {
  id: UUID
  storeId: UUID
  offerId: str
  productId: int (Ozon ID)
  sku: int | None
  name: str
  category: str | None
  price: float
  oldPrice: float | None
  currency: str (default: RUB)
  status: ProductStatus
  images: list[str]
  isArchived: bool
  updatedAt: datetime
}
```

#### AnalyticsDaily（分析数据值对象）

```
AnalyticsDaily {
  storeId: UUID
  productId: int
  offerId: str
  sku: int | None
  date: date
  impressionsSearch: int
  viewsPdp: int
  viewsTotal: int
  sessions: int
  addToCart: int
  orderedUnits: int
  deliveredUnits: int
  revenue: float
  returnsCount: int
  cancellations: int
  positionAvg: float | None
  ctr: float
  orderConversion: float
}
```

---

## 6. 目录结构与代码组织

### Phase 1 目标结构

```
ozon-analytics/
├── backend/
│   ├── main.py                    # FastAPI 入口（仅启动和路由注册）
│   ├── config.py                  # 配置管理（环境变量 + 默认值）
│   ├── database.py                # 数据库引擎和 Session 工厂
│   │
│   ├── presentation/              # Layer 1: 表现层
│   │   ├── __init__.py
│   │   ├── api/                   # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── v1/                # 版本化 API
│   │   │   │   ├── __init__.py
│   │   │   │   ├── stores.py      # /api/v1/stores
│   │   │   │   ├── products.py    # /api/v1/products
│   │   │   │   ├── analytics.py   # /api/v1/analytics
│   │   │   │   ├── sync.py        # /api/v1/sync
│   │   │   │   └── export.py      # /api/v1/export
│   │   │   └── deps.py            # 依赖注入（get_db, get_current_store...）
│   │   ├── schemas/               # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── store.py
│   │   │   ├── product.py
│   │   │   ├── analytics.py
│   │   │   └── sync.py
│   │   └── middleware/            # 中间件
│   │       ├── __init__.py
│   │       └── auth.py
│   │
│   ├── application/               # Layer 2: 应用层
│   │   ├── __init__.py
│   │   ├── services/              # 服务层（用例编排）
│   │   │   ├── __init__.py
│   │   │   ├── store_service.py
│   │   │   ├── product_service.py
│   │   │   ├── analytics_service.py
│   │   │   └── sync_orchestrator.py
│   │   └── interfaces/            # 应用层所需接口
│   │       └── __init__.py
│   │
│   ├── domain/                    # Layer 3: 领域层
│   │   ├── __init__.py
│   │   ├── entities/              # 实体
│   │   │   ├── __init__.py
│   │   │   ├── store.py
│   │   │   ├── product.py
│   │   │   ├── analytics.py
│   │   │   ├── finance.py
│   │   │   └── order.py
│   │   ├── events/                # 领域事件
│   │   │   ├── __init__.py
│   │   │   └── events.py
│   │   └── repositories/          # 仓库接口（抽象）
│   │       ├── __init__.py
│   │       ├── store_repo.py
│   │       ├── product_repo.py
│   │       ├── analytics_repo.py
│   │       └── sync_log_repo.py
│   │
│   ├── infrastructure/            # Layer 4: 基础设施层
│   │   ├── __init__.py
│   │   ├── persistence/           # 持久化实现
│   │   │   ├── __init__.py
│   │   │   ├── repositories/      # Repository 实现
│   │   │   │   ├── __init__.py
│   │   │   │   ├── store_repo.py
│   │   │   │   ├── product_repo.py
│   │   │   │   ├── analytics_repo.py
│   │   │   │   └── sync_log_repo.py
│   │   │   └── models/            # SQLAlchemy ORM 模型
│   │   │       ├── __init__.py
│   │   │       ├── base.py        # declarative base
│   │   │       ├── store_model.py
│   │   │       ├── product_model.py
│   │   │       ├── analytics_model.py
│   │   │       └── sync_log_model.py
│   │   ├── api/                   # 外部 API 客户端
│   │   │   ├── __init__.py
│   │   │   └── ozon_client.py
│   │   ├── crypto/                # 加密工具
│   │   │   ├── __init__.py
│   │   │   └── fernet.py
│   │   └── scheduler/             # 定时任务
│   │       ├── __init__.py
│   │       └── scheduler.py
│   │
│   ├── tests/                     # 测试
│   │   ├── __init__.py
│   │   ├── conftest.py            # 共享 fixture
│   │   ├── unit/                  # 单元测试
│   │   │   ├── __init__.py
│   │   │   ├── test_domain/
│   │   │   ├── test_services/
│   │   │   └── test_infrastructure/
│   │   ├── integration/           # 集成测试
│   │   │   ├── __init__.py
│   │   │   ├── test_repositories/
│   │   │   └── test_routers/
│   │   └── fixtures/              # 测试数据
│   │       ├── __init__.py
│   │       └── data.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── index.html                 # 入口（轻量骨架）
│   ├── css/
│   │   └── styles.css             # 从 index.html 提取
│   └── js/
│       ├── app.js                 # 主入口和初始化
│       ├── api.js                 # API 调用封装
│       ├── charts.js              # ECharts 图表渲染
│       ├── ui.js                  # UI 交互逻辑
│       └── store.js               # 前端状态管理
│
├── migrations/                    # 数据库迁移（Alembic）
│   ├── env.py
│   ├── versions/
│   └── alembic.ini
│
├── data/                          # 本地 SQLite 数据
├── docker/
│   └── Dockerfile
├── .env.example
├── .gitignore
└── requirements.txt               # 根级（仅聚合后端依赖）
```

---

## 7. 分阶段实施路线图

### Phase 1: 架构重构（2-3 周）← 立即开始

**目标：** 建立分层架构基础，不改功能，只重构结构

| 任务 | 工作量 | 预期成果 |
|------|--------|---------|
| 1.1 按目标目录重组代码 | 1-2 天 | 物理目录结构就绪 |
| 1.2 抽象 Repository 接口 + 实现 | 3 天 | StoreRepo / ProductRepo / AnalyticsRepo |
| 1.3 创建 Service 层 | 2 天 | Store / Product / Analytics Service |
| 1.4 拆分 main.py 路由 | 1 天 | presentation/api/v1/*.py |
| 1.5 提取 Pydantic Schema | 1 天 | presentation/schemas/*.py |
| 1.6 配置管理抽取 config.py | 0.5 天 | 统一配置入口 |
| 1.7 前端 JS 模块拆分 | 1 天 | js/api.js, charts.js, ui.js |
| **验证** | 1 天 | 所有 API 端点测试通过 |

**输出：**
- [ ] 代码分层结构落地
- [ ] 所有路由正常工作
- [ ] 前端功能完整
- [ ] DEVLOG.md 更新

---

### Phase 1.5: 测试基础（1 周）

| 任务 | 工作量 | 说明 |
|------|--------|------|
| 1.8 配置 Pytest + conftest | 0.5 天 | TestClient + InMemory DB |
| 1.9 Service 层单元测试 | 2 天 | 覆盖核心业务逻辑 |
| 1.10 Repository 集成测试 | 1 天 | SQLite test DB |
| 1.11 API 路由集成测试 | 1 天 | 关键端点 |

---

### Phase 2: 功能增强（3-4 周）

**目标：** 接入已有但未使用的 API，补充关键缺失功能

| 优先级 | 功能 | 依赖 | 说明 |
|--------|------|------|------|
| P0 | PostgreSQL 迁移 | Phase 1 完成 | Alembic 迁移脚本 + 数据导出工具 |
| P0 | 用户认证 | Phase 1 完成 | JWT + 简单密码登录（单用户或少量用户） |
| P1 | 财务数据接入 | Phase 1 完成 | Finance Transaction + Realization 同步 |
| P1 | 订单数据看板 | Phase 1 完成 | FBO/FBS 订单列表 + 状态追踪 |
| P2 | 告警规则引擎 | Phase 2 财务/订单完成 | 转化率骤降、库存预警等 |
| P2 | 数据导出增强 | Phase 1 完成 | 支持 PDF 报表、定时邮件发送 |

---

### Phase 3: 规模化准备（按需）

**仅在以下场景触发：**
- 店铺数量 > 50 家
- 多用户同时使用
- 需要独立扩展同步模块

| 措施 | 说明 |
|------|------|
| 同步模块独立为 Worker | Celery / RQ 异步任务队列 |
| 引入 Redis | 缓存、速率限制共享、任务结果存储 |
| 事件驱动 | RabbitMQ / Kafka 解耦同步和展示 |
| 前端框架化 | 升级为 Vue/React 以支持复杂交互 |
| Docker + Docker Compose | 标准化部署 |

---

### 时间线总览

```
Week 1    Week 2    Week 3    Week 4    Week 5    Week 6    Week 7    Week 8
├─Phase 1─┼─Ph1.5───┼─Phase 2─────────────────────┼─Phase 3 (if needed)───┤
│代码重构   │测试基础  │PostgreSQL   │财务/订单    │告警      │Docker    │
│分层落地   │Pytest   │用户认证     │看板增强     │导出增强   │事件驱动  │
│JS模块化   │         │             │             │          │         │
```

---

## 8. 质量属性分析

### 8.1 可维护性（Maintainability）

| 维度 | 当前 | 目标 | 实现方式 |
|------|------|------|---------|
| 模块内聚 | 🔴 低 | 🟢 高 | 领域驱动分层，每层单一职责 |
| 耦合度 | 🔴 高 | 🟢 低 | 依赖反转，面向接口编程 |
| 代码复杂度 | 🟡 中 | 🟢 低 | Service/Repository 拆分长函数 |
| 测试覆盖 | 🔴 0% | 🟢 >70% | Pytest 逐步覆盖 |

### 8.2 可扩展性（Scalability）

| 场景 | 上限估算 | 瓶颈 |
|------|---------|------|
| 店铺数 | 50 家以内 | Ozon API 限流（而非系统能力） |
| 分析数据量 | 1 亿行/年 | PostgreSQL 分区表，按店铺+月份分区 |
| 前端用户 | 10 人以内 | 15min 轮询，无瓶颈 |
| 同步并发 | 单进程足够 | Ozon API 限流是天然节流阀 |

### 8.3 可靠性（Reliability）

| 风险 | 缓解措施 |
|------|---------|
| Ozon API 限流 | OzonClient 已实现指数退避重试 |
| 同步失败 | SyncLog 记录错误，支持手动重试 |
| 数据丢失 | PostgreSQL + 定期备份 |
| 数据库升级失败 | Alembic 迁移脚本版本控制 |

### 8.4 安全性（Security）

| 需求 | 当前 | 目标 |
|------|------|------|
| API Key 存储 | Fernet 加密 ✅ | 不变 |
| 用户认证 | ❌ 无 | JWT + Session |
| 接口鉴权 | ❌ 无 | 按店铺限权 |
| HTTPS | 依赖外部 | Docker 内 Nginx 反代 + Let's Encrypt |
| CORS | localhost 白名单 | 可配置白名单 |

---

## 附录 A: 技术栈总结

| 层 | 技术 | 版本 | 选型理由 |
|----|------|------|---------|
| 后端框架 | FastAPI | 0.115+ | 异步支持、自动文档、类型安全 |
| ORM | SQLAlchemy | 2.0+ | 成熟、异步、支持 PostgreSQL+SQLite |
| 数据库 (Dev) | SQLite | — | 零配置，单用户开发友好 |
| 数据库 (Prod) | PostgreSQL | 15+ | 并发、稳定，托管数据库可选 |
| 迁移 | Alembic | 最新 | SQLAlchemy 官方迁移工具 |
| 任务调度 | APScheduler | 3.11+ | 内置进程内定时任务 |
| 加密 | cryptography (Fernet) | 44+ | 对称加密，密钥管理简单 |
| 前端 | 原生 JS + ECharts | 5.5+ | 轻量、零构建依赖 |
| HTTP 测试 | httpx + pytest | 最新 | FastAPI TestClient 依赖 |
| 部署 (Dev) | uvicorn | 0.34+ | ASGI 开发服务器 |
| 部署 (Prod) | gunicorn + uvicorn workers | 最新 | 多进程、可靠 |

---

## 附录 B: 关键指标（建议持续追踪）

1. **同步成功率** = 成功同步次数 / 总同步次数（>99%）
2. **平均同步延迟** = 发起同步 → 数据就绪的时间（<5 分钟）
3. **API 限流命中率** = 429 响应次数 / 总 API 调用次数（<1%）
4. **数据新鲜度** = 最近一次成功同步的时间与当前时间的差距
5. **测试覆盖率** = 代码行覆盖率（目标 >70%）

---

> **最后建议：** Phase 1 是地基，不要跳过。当前代码虽然"能跑"，但接下来每加一个功能都会让主要文件膨胀得更严重。花 2 周时间把地基打牢，后续所有开发都会快得多。
