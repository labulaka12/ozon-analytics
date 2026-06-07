# Ozon Analytics - 利润分析 & 告警管理 功能交付

## 交付概览

| 模块 | 状态 | 说明 |
|------|------|------|
| **利润分析** | ✅ 已完成 | 工具栏新增"同步报告"按钮，日期输入框已初始化 |
| **深度利润分析** | ✅ 已完成 | API 已就绪，数据源同步后自动展示 |
| **告警管理** | ✅ 已完成 | 完整 CRUD：新增/启用/禁用/删除规则，数据库持久化 |

## 变更清单

### 后端
| 文件 | 变更 |
|------|------|
| `backend/models.py` | 新增 `AlertRule` 数据表模型 |
| `backend/database.py` | 更新 `init_db` 导入 AlertRule |
| `backend/alerts.py` | 全面重写：从 DB 读取/保存规则，新增 CRUD 方法 (`create_rule`, `update_rule`, `delete_rule`, `toggle_rule`, `ensure_default_rules`) |
| `backend/routes/alert_routes.py` | 全面重写：新增完整 RESTful CRUD API 路由 |

### 前端
| 文件 | 变更 |
|------|------|
| `frontend/index.html` | **利润页**: 工具栏添加"同步报告"按钮 + `syncProfitRealization()` 函数 + 日期默认值初始化 |
| `frontend/index.html` | **告警页**: 工具栏添加"新增规则"按钮 + 创建规则弹窗 + `toggleAlertRule/deleteAlertRule/showCreateRuleModal/saveAlertRule` 函数 + 按店铺筛选 |

## 关键功能说明

### 利润分析页面
- 数据源为 **RealizationReport（销售实现报告）**，需要先同步才能展示
- 工具栏新增 **"同步报告"按钮**，一键从 Ozon API 拉取销售实现数据
- 日期输入框现在打开页面时**自动填充**最近30天

### 告警管理页面
- 新用户注册后**自动创建**3条默认规则：销量骤降预警、同步失败通知、价格异常预警
- **新增规则**：弹窗填写（规则名称、类型、阈值、通知渠道、关联店铺、通知地址）
- **启用/禁用**：一键切换状态
- **删除规则**：确认后删除
- **按店铺筛选**：支持按关联店铺过滤规则列表

## 启动方式
```bash
cd backend && C:/Users/Administrator/.workbuddy/binaries/python/envs/ozon-analytics/Scripts/python.exe start_server.py
```

打开浏览器访问 http://localhost:8848/
