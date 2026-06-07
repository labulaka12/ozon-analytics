# Ozon Analytics — 前后端分离架构设计

> 版本: v1.0 | 目标: 从单体 SPA 演进为 前后端分离 SPA | 前端: Vue 3 + Vite | 后端: FastAPI
> 设计原则: 渐进迁移、不过度设计、单人开发者友好

---

## 目录

1. [现状分析](#1-现状分析)
2. [目标架构总览](#2-目标架构总览)
3. [后端改造方案](#3-后端改造方案)
4. [前端架构设计](#4-前端架构设计)
5. [组件树与页面路由](#5-组件树与页面路由)
6. [状态管理与数据流](#6-状态管理与数据流)
7. [API 层设计](#7-api-层设计)
8. [开发工作流](#8-开发工作流)
9. [部署方案](#9-部署方案)
10. [迁移路线图](#10-迁移路线图)
11. [目录结构](#11-目录结构)

---

## 1. 现状分析

### 1.1 当前架构（单体 SPA）

```
┌─────────────────────────────────────────────┐
│               FastAPI 服务 (:8848)            │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ REST API │  │ 静态文件  │  │ 定时任务   │  │
│  │ /api/*   │  │ 挂载/static│  │ scheduler │  │
│  └────┬─────┘  └────┬─────┘  └───────────┘  │
│       │              │                       │
│       ▼              ▼                       │
│  ┌──────────────────────────────────────┐   │
│  │       index.html (单文件 SPA)         │   │
│  │  ~1500 行 HTML + JS + CSS + ECharts  │   │
│  │  hash 路由: #login/#dashboard 等     │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**痛点：**
- 前端 1500+ 行单文件，无模块化，维护成本越来越高
- 页面从 1 个增到 4 个（分析/订单/利润/设置），JS 逻辑爆炸
- HTML/CSS/JS 混合，无法使用现代前端工具链
- 无组件化，DOM 操作散落在不同函数中
- 部署耦合——后端更新前端必须一起重启

### 1.2 现有基础（可复用资产）

| 资产 | 说明 | 迁移方式 |
|------|------|---------|
| REST API 接口 | 所有 /api/* 端点已完善 | 完全复用，仅去掉静态文件挂载 |
| JWT 认证 | auth.py 签发和验证 | 完全复用 |
| ECharts 图表逻辑 | 6 种图表的渲染逻辑 | 移植到 Vue 组件 |
| UI 样式 | 蓝白配色、卡片布局 | 提取为 CSS 变量 + 组件样式 |
| 数据模型 | 11 个 SQLAlchemy 模型 | 完全复用 |

---

## 2. 目标架构总览

### 2.1 最终架构

```
┌─────────────────────────────────┐    ┌──────────────────────────────────┐
│      前端 (Vue 3 SPA)            │    │       后端 (FastAPI API)          │
│                                 │    │                                  │
│  ┌───────────────────────────┐  │    │  ┌────────────────────────────┐  │
│  │ Vue Router (页面路由)      │  │    │  │  REST API                  │  │
│  │   /login                  │  │    │  │   /api/auth/*              │  │
│  │   /dashboard              │  │    │  │   /api/stores/*            │  │
│  │   /orders                 │  │    │  │   /api/products/*          │  │
│  │   /profit                 │  │    │  │   /api/analytics/*         │  │
│  │   /settings               │  │    │  │   /api/sync/*              │  │
│  └──────────┬────────────────┘  │    │  │   /api/orders/*            │  │
│             │                   │    │  │   /api/profit/*            │  │
│  ┌──────────▼────────────────┐  │    │  │   /api/settings/*          │  │
│  │ Pinia Store (状态管理)     │  │    │  │   /api/alerts/*            │  │
│  │  authStore               │  │    │  └────────────┬───────────────┘  │
│  │  storeStore              │  │    │               │                  │
│  │  analyticsStore          │  │    │  ┌────────────▼───────────────┐  │
│  │  orderStore              │  │    │  │  后台服务                    │  │
│  │  profitStore             │  │    │  │  scheduler_worker.py       │  │
│  └──────────┬────────────────┘  │    │  │  (定时任务独立进程)         │  │
│             │                   │    │  └────────────────────────────┘  │
│  ┌──────────▼────────────────┐  │    │                                  │
│  │ Vue 组件树                 │  │    │  Render/Server                  │
│  │  带 ECharts 图表封装      │  │    │  纯 API 服务，无静态文件        │
│  └───────────────────────────┘  │    └──────────────────────────────────┘
│                                 │
│  Vite Dev Server (:5173)        │         Vercel / Netlify / Nginx
│  或 Vercel/Netlify 部署        │         (静态 SPA 托管)
└─────────────────────────────────┘
```

### 2.2 核心变化

| 维度 | 当前（单体 SPA） | 目标（前后端分离） |
|------|-----------------|-------------------|
| 前端 | 单 HTML 文件 | Vue 3 + Vite 工程化项目 |
| 后端 | FastAPI + 静态文件 | 纯 API 服务 |
| 路由 | hash 路由 (#login) | Vue Router (history 模式) |
| 状态 | 全局变量 + DOM | Pinia 响应式状态管理 |
| HTTP | 原生 fetch | Axios + 拦截器 |
| 图表 | ECharts 直接挂载 | vue-echarts 组件封装 |
| 部署 | 单服务部署 | 前后端独立部署/更新 |
| 开发 | 刷新浏览器 | Vite HMR 热更新 |

---

## 3. 后端改造方案

### 3.1 变更清单

后端改动**极小**，API 层面几乎不变：

| 变更项 | 操作 | 说明 |
|--------|------|------|
| CORS 配置 | 修改 | 添加 Vue 开发服务器 origin（localhost:5173） |
| 静态文件挂载 | 移除 | 前端不再由 FastAPI 托管 |
| 首页路由 `/` | 移除或改成 API 状态页 | 不再返回 index.html |
| API prefix 统一 | 可选 | 所有 API 加 `/api` 前缀（目前大部分已加） |

### 3.2 CORS 配置（修改 main.py）

```python
# 改造后 CORS 配置
CORS_ORIGINS = ["http://localhost:5173"]  # Vite 开发服务器
if os.environ.get("FRONTEND_URL"):
    CORS_ORIGINS.append(os.environ["FRONTEND_URL"])  # 生产环境前端域名
# 原有 localhost:8848 保留（本地测试用）
CORS_ORIGINS.extend(["http://localhost:8848", "http://127.0.0.1:8848"])
```

### 3.3 移除静态文件托管

```python
# 移除（不再由后端托管前端）
# app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
# @app.get("/") → 改为简单的 API 状态检查

@app.get("/api/health")
def health_check():
    """健康检查端点"""
    return {"status": "ok", "version": "1.0.0"}
```

### 3.4 API 路由整理（可选重构）

当前 `main.py` 路由和 `routes/` 模块混合，建议统一：

```
main.py → 仅保留:
  - 应用初始化 (FastAPI app)
  - CORS 中间件
  - 生命周期 (lifespan)
  - 路由注册 (include_router)
  - 健康检查端点

各个路由模块（已有或新建）:
  routes/auth.py      ← 从 auth.py 移至此处（或保持现状）
  routes/stores.py    ← 从 main.py 抽出店铺路由
  routes/products.py  ← 从 main.py 抽出商品路由
  routes/analytics.py ← 从 main.py 抽出分析路由
  routes/sync.py      ← 从 main.py 抽出同步路由
  routes/export.py    ← 从 main.py 抽出导出路由
  routes/orders.py    ← 已有
  routes/profit.py    ← 已有
  routes/settings.py  ← 已有（含导出）
  routes/alerts.py    ← 已有
```

**优先度**: 低（可选）——API 接口不变，仅代码组织优化。单人开发可推迟。

---

## 4. 前端架构设计

### 4.1 技术选型

| 类别 | 选型 | 版本 | 理由 |
|------|------|------|------|
| 框架 | Vue 3 | 3.5+ | Composition API，TypeScript 友好，学习曲线平缓 |
| 构建 | Vite | 6+ | 冷启动快，HMR 即时，零配置 TypeScript |
| 路由 | Vue Router | 4.x | Vue 官方路由，支持 history/hash 模式 |
| 状态管理 | Pinia | 3.x | 轻量、TypeScript 原生支持、devtools 集成 |
| HTTP | Axios | 1.x | 拦截器机制（自动带 token、处理 401） |
| 图表 | ECharts + vue-echarts | 5.5+ | 现有 ECharts 资产直接复用 |
| CSS | UnoCSS / Tailwind | | 按需原子化 CSS，减少样式文件体积 |
| UI | 自己封装（或 Naive UI） | | 看板风格较独特，轻量组件库即可 |

### 4.2 项目初始化命令

```bash
cd ozon-analytics
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install
npm install vue-router@4 pinia axios echarts vue-echarts
# CSS 方案（选 UnoCSS 更轻量）
npm install -D unocss
```

### 4.3 目录结构

```
frontend/
├── index.html                 # Vite 入口 HTML
├── vite.config.ts             # Vite 配置（含 API 代理）
├── tsconfig.json
├── package.json
│
├── src/
│   ├── main.ts                # 应用入口（挂载 Vue）
│   ├── App.vue                # 根组件（布局容器）
│   │
│   ├── router/                # 路由定义
│   │   └── index.ts           # Vue Router 配置 + 路由守卫
│   │
│   ├── stores/                # Pinia 状态管理
│   │   ├── auth.ts            # 用户认证状态
│   │   ├── store.ts           # 店铺列表状态
│   │   ├── analytics.ts       # 分析数据状态
│   │   ├── orders.ts          # 订单数据状态
│   │   └── profit.ts          # 利润数据状态
│   │
│   ├── api/                   # API 封装层
│   │   ├── request.ts         # Axios 实例 + 拦截器
│   │   ├── auth.ts            # 认证相关 API
│   │   ├── stores.ts          # 店铺 API
│   │   ├── products.ts        # 商品 API
│   │   ├── analytics.ts       # 分析数据 API
│   │   ├── orders.ts          # 订单 API
│   │   ├── profit.ts          # 利润 API
│   │   ├── sync.ts            # 同步 API
│   │   └── settings.ts        # 设置 API
│   │
│   ├── types/                 # TypeScript 类型定义
│   │   ├── api.ts             # API 通用类型（分页响应等）
│   │   ├── store.ts           # 店铺类型
│   │   ├── product.ts         # 商品类型
│   │   ├── analytics.ts       # 分析数据类型
│   │   ├── order.ts           # 订单类型
│   │   └── profit.ts          # 利润数据类型
│   │
│   ├── layouts/               # 布局组件
│   │   ├── AppLayout.vue      # 主布局（侧栏 + 顶部栏 + 内容区）
│   │   └── AuthLayout.vue     # 认证页布局（居中卡片）
│   │
│   ├── views/                 # 页面组件
│   │   ├── login/             # 登录页
│   │   │   ├── LoginView.vue
│   │   │   └── RegisterView.vue
│   │   ├── dashboard/         # 分析看板
│   │   │   ├── DashboardView.vue
│   │   │   ├── KPICards.vue
│   │   │   ├── TrendChart.vue      # 曝光/浏览量趋势
│   │   │   ├── ConversionChart.vue # 转化漏斗
│   │   │   ├── ProductTable.vue    # 商品数据表格
│   │   │   └── FilterBar.vue       # 筛选器
│   │   ├── orders/            # 订单管理
│   │   │   ├── OrdersView.vue
│   │   │   ├── OrderTable.vue
│   │   │   └── OrderDetail.vue     # 订单详情弹窗
│   │   ├── profit/            # 利润看板
│   │   │   ├── ProfitView.vue
│   │   │   ├── ProfitKPI.vue
│   │   │   ├── ProfitTrend.vue     # 利润趋势折线图
│   │   │   ├── ProductRanking.vue  # 商品利润排行柱状图
│   │   │   ├── FeePieChart.vue     # 费用构成饼图
│   │   │   ├── ProfitTable.vue     # 利润明细表格
│   │   │   └── ProfitPredict.vue   # 利润预测卡片
│   │   └── settings/          # 设置页
│   │       ├── SettingsView.vue
│   │       ├── ExchangeRateEditor.vue
│   │       ├── CostEditor.vue
│   │       └── ExpenseManager.vue
│   │
│   ├── components/            # 通用组件
│   │   ├── common/            # 基础 UI 组件
│   │   │   ├── AppSidebar.vue       # 侧栏导航
│   │   │   ├── AppHeader.vue        # 顶部栏（用户信息+退出）
│   │   │   ├── Card.vue             # 卡片容器
│   │   │   ├── DataTable.vue        # 通用数据表格
│   │   │   ├── Pagination.vue       # 分页组件
│   │   │   ├── DateRangePicker.vue  # 日期范围选择器
│   │   │   ├── Loading.vue          # 加载状态
│   │   │   ├── Empty.vue            # 空数据状态
│   │   │   └── ErrorState.vue       # 错误状态
│   │   └── charts/            # 图表组件（封装 ECharts）
│   │       ├── LineChart.vue
│   │       ├── BarChart.vue
│   │       └── PieChart.vue
│   │
│   ├── composables/           # 组合式函数
│   │   ├── useAuth.ts         # 认证逻辑（登录/注册/登出）
│   │   ├── useStore.ts        # 店铺选择逻辑
│   │   ├── useDateRange.ts    # 日期范围逻辑
│   │   └── useExport.ts       # CSV 导出逻辑
│   │
│   ├── utils/                 # 工具函数
│   │   ├── format.ts          # 数字/日期格式化
│   │   └── constants.ts       # 常量（指标名称映射等）
│   │
│   └── assets/                # 静态资源
│       └── styles/
│           ├── variables.css  # CSS 变量（蓝白色系）
│           └── global.css     # 全局样式
```

### 4.4 关键配置：Vite 代理

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'

export default defineConfig({
  plugins: [vue(), UnoCSS()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8848',  // 后端地址
        changeOrigin: true,
      },
    },
  },
})
```

这样开发时前端 `fetch('/api/stores')` 会自动代理到后端的 `localhost:8848/api/stores`，无需处理跨域。

---

## 5. 组件树与页面路由

### 5.1 路由表

```typescript
// src/router/index.ts
const routes = [
  {
    path: '/',
    component: AuthLayout,
    children: [
      { path: '/login', name: 'Login', component: () => import('@/views/login/LoginView.vue') },
      { path: '/register', name: 'Register', component: () => import('@/views/login/RegisterView.vue') },
    ],
  },
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '/dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/DashboardView.vue') },
      { path: '/orders', name: 'Orders', component: () => import('@/views/orders/OrdersView.vue') },
      { path: '/profit', name: 'Profit', component: () => import('@/views/profit/ProfitView.vue') },
      { path: '/settings', name: 'Settings', component: () => import('@/views/settings/SettingsView.vue') },
      { path: '', redirect: '/dashboard' },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]
```

### 5.2 路由守卫

```typescript
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})
```

### 5.3 组件嵌套树

```
App.vue
├── <router-view>
│
├── [AuthLayout] ─── 路由: /login, /register
│   └── AuthCard (居中白色卡片容器)
│       ├── LoginView
│       │   ├── EmailInput
│       │   ├── PasswordInput
│       │   └── SubmitButton
│       └── RegisterView
│           ├── EmailInput
│           ├── PasswordInput
│           ├── ConfirmPasswordInput
│           └── SubmitButton
│
└── [AppLayout] ─── 路由: /dashboard, /orders, /profit, /settings
    ├── AppSidebar
    │   ├── Logo
    │   ├── NavItem (分析看板)
    │   ├── NavItem (订单管理)
    │   ├── NavItem (利润看板)
    │   └── NavItem (设置)
    ├── AppHeader
    │   ├── PageTitle
    │   ├── UserInfo
    │   └── LogoutButton
    └── <router-view> (内容区)
        │
        ├── DashboardView
        │   ├── FilterBar (店铺选择 + 日期范围)
        │   ├── KPICards × 6 (曝光/浏览/加购/转化/收入/排名)
        │   ├── TrendChart (ECharts 折线图)
        │   ├── ConversionChart (ECharts 柱状图/漏斗图)
        │   └── ProductTable (DataTable + 分页)
        │
        ├── OrdersView
        │   ├── OrderFilter (店铺/状态/日期)
        │   ├── OrderTable (DataTable + 分页)
        │   └── OrderDetail (Dialog 弹窗)
        │
        ├── ProfitView
        │   ├── ProfitKPI × 4 (总收入/总成本/总费用/净利润+毛利率)
        │   ├── ProfitTrend (ECharts 折线图)
        │   ├── ProductRanking (ECharts 柱状图)
        │   ├── FeePieChart (ECharts 饼图)
        │   ├── ProfitPredict (利润预测卡片)
        │   └── ProfitTable (DataTable + 分页)
        │
        └── SettingsView
            ├── ExchangeRateEditor
            ├── CostEditor
            └── ExpenseManager
```

---

## 6. 状态管理与数据流

### 6.1 Pinia Store 设计

```typescript
// stores/auth.ts
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => !!token.value)

  async function login(email: string, password: string) { /* ... */ }
  async function register(email: string, password: string) { /* ... */ }
  function logout() { token.value = ''; user.value = null; localStorage.removeItem('access_token') }

  return { token, user, isAuthenticated, login, register, logout }
})

// stores/store.ts
export const useStoreStore = defineStore('store', () => {
  const stores = ref<Store[]>([])
  const currentStoreId = ref<number | null>(null)

  async function fetchStores() { /* GET /api/stores */ }
  async function createStore(data: StoreCreate) { /* POST /api/stores */ }
  // ...

  return { stores, currentStoreId, fetchStores, createStore }
})

// stores/analytics.ts
export const useAnalyticsStore = defineStore('analytics', () => {
  const summary = ref<AnalyticsSummary | null>(null)
  const items = ref<AnalyticsRow[]>([])
  const loading = ref(false)

  async function fetchAnalytics(params: AnalyticsParams) { /* GET /api/analytics */ }
  async function fetchSummary(params: AnalyticsParams) { /* GET /api/analytics/summary */ }

  return { summary, items, loading, fetchAnalytics, fetchSummary }
})

// stores/profit.ts — 类似模式
// stores/orders.ts — 类似模式
```

### 6.2 数据流

```
用户操作 → Vue 组件（dispatch action）
              ↓
          Pinia Store（调用 API 层）
              ↓
          Axios 请求（自动携带 JWT Token）
              ↓
          FastAPI API（验证 JWT + user_id 过滤）
              ↓
          SQLAlchemy → SQLite / PostgreSQL
              ↓
          JSON Response
              ↓
          Pinia Store（更新响应式状态）
              ↓
          Vue 组件（自动重新渲染）
              ↓
          ECharts 图表（响应式更新）
```

### 6.3 Axios 拦截器设计

```typescript
// api/request.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',  // 默认走 Vite proxy
  timeout: 30000,
})

// 请求拦截器：自动带 Token
request.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

// 响应拦截器：统一处理 401
request.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request
```

---

## 7. API 层设计

### 7.1 API 模块化

每个资源一个文件，函数式封装，返回 Promise：

```typescript
// api/stores.ts
import request from './request'
import type { Store, StoreCreate } from '@/types/store'

export function fetchStores(): Promise<Store[]> {
  return request.get('/api/stores').then(r => r.data)
}

export function createStore(data: StoreCreate): Promise<{ id: number }> {
  return request.post('/api/stores', data).then(r => r.data)
}

export function deleteStore(id: number): Promise<void> {
  return request.delete(`/api/stores/${id}`)
}

// 使用
const stores = await fetchStores()
```

### 7.2 TypeScript 类型定义

```typescript
// types/store.ts
export interface Store {
  id: number
  name: string
  client_id: string
  is_active: boolean
  last_sync_at: string | null
  created_at: string
  product_count?: number
}

// types/analytics.ts
export interface AnalyticsRow {
  product_id: number
  offer_id: string
  date: string
  impressions_search: number
  views_pdp: number
  views_total: number
  add_to_cart: number
  revenue: number
  // ...
}

export interface AnalyticsSummary {
  total_impressions: number
  total_views: number
  total_revenue: number
  // ...
}

// types/profit.ts
export interface ProfitSummary {
  total_revenue: number
  total_cost: number
  total_fees: number
  total_profit: number
  profit_margin: number
}

// types/api.ts
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
```

### 7.3 API 接口总清单

| 模块 | 方法 | 路径 | 前端 API 文件 |
|------|------|------|-------------|
| 认证 | POST | `/api/auth/register` | `api/auth.ts` |
| 认证 | POST | `/api/auth/login` | `api/auth.ts` |
| 认证 | GET | `/api/auth/me` | `api/auth.ts` |
| 店铺 | GET/POST/PUT/DELETE | `/api/stores[/:id]` | `api/stores.ts` |
| 商品 | GET | `/api/products` | `api/products.ts` |
| 分析 | GET | `/api/analytics` | `api/analytics.ts` |
| 分析 | GET | `/api/analytics/summary` | `api/analytics.ts` |
| 同步 | POST | `/api/sync/:type` | `api/sync.ts` |
| 同步 | GET | `/api/sync/logs` | `api/sync.ts` |
| 导出 | GET | `/api/export/csv` | `api/analytics.ts` |
| 订单 | GET | `/api/orders` | `api/orders.ts` |
| 利润 | GET | `/api/profit/summary` | `api/profit.ts` |
| 利润 | GET | `/api/profit/trend` | `api/profit.ts` |
| 利润 | GET | `/api/profit/products` | `api/profit.ts` |
| 利润 | GET | `/api/profit/fees` | `api/profit.ts` |
| 利润 | GET | `/api/profit/detail` | `api/profit.ts` |
| 设置 | GET/PUT | `/api/settings/exchange-rate` | `api/settings.ts` |
| 设置 | PUT | `/api/products/:id/cost` | `api/settings.ts` |
| 设置 | GET/POST/PUT/DELETE | `/api/expenses[/:id]` | `api/settings.ts` |
| 设置 | GET | `/api/export/profit-csv` | `api/settings.ts` |
| 告警 | GET/POST/PUT/DELETE | `/api/alerts/rules[/:id]` | `api/alerts.ts` |

---

## 8. 开发工作流

### 8.1 本地开发

```bash
# 终端 1: 启动后端 API 服务
cd ozon-analytics
python backend/start_server.py
# → http://localhost:8848

# 终端 2: 启动前端开发服务
cd ozon-analytics/frontend
npm run dev
# → http://localhost:5173（自动代理 /api → :8848）
```

浏览器打开 `localhost:5173`，所有 `/api` 请求自动代理到后端。

### 8.2 开发效率对比

| 场景 | 当前模式 | 前后端分离模式 |
|------|---------|--------------|
| 改前端样式 | 刷新浏览器 | Vite HMR 即时生效 |
| 改前端逻辑 | 刷新浏览器 | Vite HMR 即时生效 |
| 改后端 | 自动 reload | 自动 reload（不变） |
| 调试 API | 看日志 | 看日志 + Axios 拦截器 + Vue Devtools |
| 查看状态 | console.log | Vue Devtools + Pinia 调试面板 |

### 8.3 推荐 VS Code 插件

- **Vue Language Features (Volar)** — Vue 3 语言支持
- **UnoCSS** — 原子化 CSS 提示
- **Axios Helper** — API 请求调试
- **ESLint + Prettier** — 代码格式化

---

## 9. 部署方案

### 9.1 方案对比

| 方案 | 后端 | 前端 | 成本 | 复杂度 | 推荐 |
|------|------|------|------|--------|------|
| **A: Vercel + Render** | Render Web Service | Vercel (免费) | 低 | 低 | ⭐ 推荐 |
| **B: 全上 Render** | Render Web Service | Render Static Site | 中 | 低 | 备选 |
| **C: 单 VPS + Nginx** | 自建服务器 | Nginx 托管 | 中 | 高 | 不推荐单人 |
| **D: 保持单服务部署** | FastAPI 同域 | Vite build 产物放后端 | 最低 | 最低 | **过渡方案** |

### 9.2 推荐方案 A 详解

```
用户浏览器
    │
    ├── https://ozon-analytics.vercel.app  ← Vercel 托管 Vue SPA
    │   (静态资源 + Vue Router history 回退)
    │
    └── /api/* → https://ozon-analytics.onrender.com/api/*
        (Vercel rewrites 配置代理)
```

**前端部署（Vercel）：**

```json
// frontend/vercel.json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://ozon-analytics.onrender.com/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**后端部署（Render）：**

删除静态文件挂载，加环境变量 `FRONTEND_URL=https://ozon-analytics.vercel.app`

### 9.3 过渡方案 D（推荐先做）

在前后端分离项目搭建完成之前，保持当前部署方式不变：

```
FastAPI 同域部署（当前模式）:
  1. Vite build → 生成 dist/
  2. FastAPI 挂载 dist/ 为静态文件
  3. 单服务部署，零架构变化
```

这样前端代码已经迁移到 Vue 工程化开发，但部署方式不变。等一切稳定后再切到独立部署。

---

## 10. 迁移路线图

### Phase 0: 基础设施（1 天）

| 任务 | 产出 |
|------|------|
| 初始化 Vue 3 + Vite 项目 | `frontend/` 目录 |
| 配置 Vite proxy → :8848 | 开发时前后端联调 |
| 搭建 Vue Router + Pinia | 路由框架 + Store 骨架 |
| 封装 Axios 实例 + 拦截器 | `api/request.ts` |
| 配置 UnoCSS / Tailwind | CSS 基础设施 |
| 提取 CSS 变量（蓝白色系） | `variables.css` |

### Phase 1: 核心页面迁移（2-3 天）

按页面复杂度排序：

| 顺序 | 页面 | 复杂度 | 说明 |
|------|------|--------|------|
| 1 | **登录/注册页** | ⭐ | 表单 + API 调用 + 路由守卫 |
| 2 | **布局框架** | ⭐⭐ | 侧栏 + 顶部栏 + 路由嵌套 |
| 3 | **分析看板** | ⭐⭐⭐⭐ | 4 个图表组件 + 数据表格 + 筛选器 |
| 4 | **设置页** | ⭐⭐ | 汇率编辑 + 成本录入 + 费用管理 |
| 5 | **订单管理** | ⭐⭐⭐ | 订单列表 + 筛选 + 详情弹窗 |
| 6 | **利润看板** | ⭐⭐⭐⭐ | 4 个 KPI + 3 个图表 + 表格 + 预测 |

**迁移策略（关键）：**

不是一次性全部重写，而是**页面级渐进迁移**：

```
1. 新建 Vue 项目
2. 保留原 index.html 不动（后端继续托管）
3. 先改造登录/注册页 → 验证开发流程通顺
4. 改造分析看板 → 验证 ECharts 集成
5. 改造剩余页面
6. 都完成后，切换前端到新项目，移除 index.html
```

### Phase 2: 组件优化（1 天，可选）

| 任务 | 说明 |
|------|------|
| 封装通用 DataTable 组件 | 排序、分页、列宽自适应 |
| 封装图表组件 | LineChart / BarChart / PieChart |
| 添加骨架屏加载状态 | 数据加载时的过渡效果 |
| 全局错误处理 | Axios 拦截器统一错误提示 |

---

## 11. 目录结构总览

完成迁移后的完整项目结构：

```
ozon-analytics/
├── backend/                     # FastAPI 后端（纯 API）
│   ├── main.py                  # 应用入口（路由注册 + 生命周期）
│   ├── config.py                # 配置管理
│   ├── database.py              # 数据库连接
│   ├── models.py                # 11 个 SQLAlchemy 模型
│   ├── auth.py                  # JWT 认证
│   ├── crypto.py                # Fernet 加密
│   ├── ozon_client.py           # Ozon API 客户端
│   ├── scheduler.py             # 同步逻辑
│   ├── scheduler_worker.py      # 定时任务独立进程
│   ├── profit_engine.py         # 利润核算引擎
│   ├── alerts.py                # 告警通知模块
│   ├── routes/                  # 路由模块
│   │   ├── orders.py
│   │   ├── profit.py
│   │   ├── settings.py
│   │   ├── profit_engine_routes.py
│   │   └── alert_routes.py
│   ├── alembic/                 # 数据库迁移
│   ├── tests/                   # （待补充）
│   ├── requirements.txt
│   └── start_server.py
│
├── frontend/                    # Vue 3 前端（纯 SPA）
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   ├── vercel.json              # Vercel 部署配置
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/
│       ├── stores/
│       ├── api/
│       ├── types/
│       ├── layouts/
│       ├── views/
│       │   ├── login/
│       │   ├── dashboard/
│       │   ├── orders/
│       │   ├── profit/
│       │   └── settings/
│       ├── components/
│       │   ├── common/
│       │   └── charts/
│       ├── composables/
│       ├── utils/
│       └── assets/styles/
│
├── deploy/                      # 部署配置
├── data/                        # SQLite 数据
├── docs/                        # 文档
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── ARCH_前端分离架构设计.md       # ← 本文件
├── DEVLOG.md
└── render.yaml
```

---

## 附录：单人开发的务实话

### 为什么选 Vue 3 而不是 React

| 维度 | Vue 3 | React |
|------|-------|-------|
| 学习曲线 | 平缓（模板语法直观） | 陡峭（JSX + Hooks 规则） |
| 项目结构 | 官方约定（`views/`、`components/`） | 自由（需要自己建立约定） |
| 中文文档 | 原生中文，社区活跃 | 翻译版，中文生态略弱 |
| 状态管理 | Pinia（原生 TS 支持） | Redux Toolkit / Zustand |
| 构建工具 | Vite 官方默认 | 也支持 Vite，但 CRA 生态碎片化 |
| 适合 | **单人小团队 → 大项目** | 大团队 → 超大项目 |

### 关键原则

1. **不要一步到位** — Phase 1 只迁移 2 个页面就可切换上线
2. **后端几乎不改** — 现有 API 接口不变，只增加 CORS origin
3. **部署先用过渡方案** — Vite build 产物放回后端，零额外费用
4. **TypeScript 非必须但强烈推荐** — 单人项目 TS 查出的 bug 可节省大量联调时间
5. **组件粒度"够用就好"** — 不必过度抽像，页面级组件先跑通，公共部分后提取
