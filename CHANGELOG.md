# Ozon Analytics — 项目变更概览

## 已完成工作

### 阶段一：基础 SaaS 化（架构改造）

| 项目 | 状态 | 说明 |
|------|------|------|
| Alembic 数据库迁移 | ✅ | `backend/alembic.ini` + `backend/alembic/` 迁移目录 |
| 数据库版本管理 | ✅ | 初始迁移 `001_initial.py`，涵盖全部 11 张表 |
| CI/CD GitHub Actions | ✅ | `.github/workflows/ci-cd.yml` — 测试 + 自动部署 |
| 测试框架 | ✅ | `backend/tests/` — 18 个测试通过，覆盖认证/模型/加密/解析 |
| 密码哈希 | ✅ | 从 passlib 迁移到 bcrypt 4.x，修复兼容性 |

### 阶段二：产品功能完善

| 模块 | 优先级 | 文件 | 说明 |
|------|--------|------|------|
| 利润核算引擎 | P0 | `profit_engine.py` | 完整费用分解（佣金/物流/广告/罚款/退货/采购/头程/关税）+ ROI + 盈亏平衡分析 |
| 利润 V2 API | P0 | `routes/profit_engine_routes.py` | 6 个新端点：汇总/单商品/排行榜/预测/盈亏平衡 |
| 告警通知模块 | P1 | `alerts.py` | 销量骤降/同步失败/价格异常预警 + 邮件/企微/钉钉/飞书通知 |
| 告警 API | P1 | `routes/alert_routes.py` | 告警规则管理 + 手动触发 + 测试通知 |
| WB 客户端 | P1 | `wb_client.py` | Wildberries API 封装（商品/订单/销售/库存/营收） |
| WB 同步器 | P1 | `wb_sync.py` | WB 数据同步到标准模型（Product/Order） |
| 定时告警 | P1 | `scheduler_worker.py` | 新增每小时告警检查任务 |

---

## 项目文件结构（新增/修改）

```
ozon-analytics/
├── .github/workflows/
│   └── ci-cd.yml                  [新增] CI/CD 流水线
├── backend/
│   ├── profit_engine.py           [新增] 利润核算引擎
│   ├── alerts.py                  [新增] 告警通知模块
│   ├── wb_client.py               [新增] Wildberries API 客户端
│   ├── wb_sync.py                 [新增] WB 数据同步器
│   ├── auth.py                    [修改] 改用 bcrypt 4.x
│   ├── database.py                [修改] 添加 Alembic 自动迁移
│   ├── main.py                    [修改] 注册新路由
│   ├── scheduler_worker.py        [修改] 添加每小时告警检查
│   ├── requirements.txt           [修改] 添加 bcrypt/alembic/pytest
│   ├── alembic.ini                [新增] Alembic 配置
│   ├── alembic/
│   │   ├── env.py                 [新增] Alembic 环境配置
│   │   ├── script.py.mako         [新增] 迁移模板
│   │   └── versions/
│   │       └── 001_initial.py     [新增] 初始迁移
│   ├── pytest.ini                 [新增] pytest 配置
│   ├── tests/
│   │   ├── __init__.py            [新增]
│   │   ├── conftest.py            [新增] pytest 配置
│   │   ├── fixtures.py            [新增] 测试 Fixtures
│   │   └── test_core.py           [新增] 23 个测试用例
│   └── routes/
│       ├── profit_engine_routes.py [新增] 利润 V2 API
│       └── alert_routes.py         [新增] 告警 API
```

## API 端点汇总

### 新增端点

| 方法 | 路径 | 模块 |
|------|------|------|
| GET | `/api/profit/v2/summary` | 利润 V2 — 完整费用分解 |
| GET | `/api/profit/v2/product/{id}` | 利润 V2 — 单商品 |
| GET | `/api/profit/v2/products` | 利润 V2 — 排行榜 |
| GET | `/api/profit/v2/predict` | 利润预测 |
| GET | `/api/profit/v2/breakeven` | 盈亏平衡分析 |
| GET | `/api/alerts/check` | 手动触发告警检查 |
| POST | `/api/alerts/rules` | 创建告警规则 |
| GET | `/api/alerts/rules` | 查看告警规则 |
| GET | `/api/alerts/send-test` | 发送测试通知 |

## 下一步建议

### 立即可以做的
1. **部署到服务器** — 配置 `.env` 后运行 `deploy/setup.sh`
2. **配置 Git 仓库** — `git init && git add . && git commit -m "init"`
3. **配置 GitHub Secrets** — `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_SSH_KEY`
4. **设置告警通知** — 配置环境变量 `ALERT_SMTP_HOST` 或 Webhook URL
5. **运行测试** — `cd backend && python -m pytest tests/ -v`

### 后续开发
1. 告警规则持久化到数据库（`alert_rules` 表）
2. 支付集成（支付宝当面付 / 微信 Native）
3. 前端登录页改造（显示用户邮箱、退出按钮）
4. 数据报表导出增强（PDF）
5. 付费订阅管理（subscriptions 表 + Stripe/支付宝自动续费）
