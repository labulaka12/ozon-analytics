"""数据库模型定义"""
from sqlalchemy import Column, Integer, String, Float, Numeric, Date, DateTime, Text, Boolean, UniqueConstraint, Index, JSON
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """系统用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="bcrypt 密码哈希")
    is_active = Column(Boolean, default=True, comment="用户是否激活")
    # ---- SaaS 扩展字段 ----
    email_verified = Column(Boolean, default=False, comment="邮箱是否已验证")
    role = Column(String(20), default="user", comment="角色: user/admin")
    stripe_customer_id = Column(String(100), comment="Stripe 客户 ID")
    display_name = Column(String(100), comment="显示名称")
    # ---- 验证/重置令牌 ----
    email_verify_token = Column(String(200), comment="邮箱验证令牌")
    email_verify_token_expires = Column(DateTime, comment="验证令牌过期时间")
    password_reset_token = Column(String(200), comment="密码重置令牌")
    password_reset_token_expires = Column(DateTime, comment="重置令牌过期时间")
    # ---- 时间戳 ----
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.email}>"


class Store(Base):
    """Ozon 店铺"""
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    name = Column(String(100), nullable=False, comment="店铺名称")
    client_id = Column(String(50), nullable=False, comment="Ozon Client-Id")
    api_key = Column(String(200), nullable=False, comment="Ozon Api-Key")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_sync_at = Column(DateTime, comment="最后同步时间")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Store {self.name}>"


class Product(Base):
    """商品信息"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False, comment="所属店铺ID")
    offer_id = Column(String(100), nullable=False, comment="卖家货号")
    product_id = Column(Integer, nullable=False, comment="Ozon商品ID")
    sku = Column(Integer, comment="SKU")
    name = Column(String(500), comment="商品名称")
    category = Column(String(200), comment="类目")
    price = Column(Float, comment="当前价格(RUB)")
    old_price = Column(Float, comment="原价(RUB)")
    currency = Column(String(10), default="RUB", comment="货币")
    barcode = Column(String(50), comment="条形码")
    images = Column(Text, comment="图片URL(JSON数组)")
    status = Column(String(50), comment="商品状态")
    is_archived = Column(Boolean, default=False)
    cost_price = Column(Float, default=0.0, comment="采购成本(CNY)")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", "product_id", name="uq_user_store_product"),
        Index("idx_user_store_product", "user_id", "store_id", "product_id"),
    )

    def __repr__(self):
        return f"<Product {self.offer_id}>"


class AnalyticsDaily(Base):
    """每日分析数据"""
    __tablename__ = "analytics_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False, comment="店铺ID")
    product_id = Column(Integer, nullable=False, comment="Ozon商品ID")
    offer_id = Column(String(100), comment="卖家货号")
    sku = Column(Integer, comment="SKU")
    date = Column(Date, nullable=False, comment="日期")

    # 核心指标 - 曝光与流量
    impressions_search = Column(Integer, default=0, comment="搜索曝光量 (hits_view_search)")
    views_pdp = Column(Integer, default=0, comment="商品页浏览量 (hits_view_pdp)")
    views_total = Column(Integer, default=0, comment="总浏览量 (hits_view)")
    sessions = Column(Integer, default=0, comment="会话数 (session_view)")

    # 核心指标 - 加购
    add_to_cart = Column(Integer, default=0, comment="加购数 (hits_tocart)")
    add_to_cart_search = Column(Integer, default=0, comment="搜索加购数 (hits_tocart_search)")
    add_to_cart_pdp = Column(Integer, default=0, comment="PDP加购数 (hits_tocart_pdp)")

    # 核心指标 - 转化
    conversion_to_cart = Column(Float, default=0.0, comment="整体加购率 (%)")
    conversion_search_to_cart = Column(Float, default=0.0, comment="搜索加购率 (%)")
    conversion_pdp_to_cart = Column(Float, default=0.0, comment="PDP加购率 (%)")

    # 核心指标 - 销售
    ordered_units = Column(Integer, default=0, comment="下单件数")
    delivered_units = Column(Integer, default=0, comment="发货件数")
    revenue = Column(Float, default=0.0, comment="销售额(RUB)")
    orders = Column(Integer, default=0, comment="订单数")

    # 其他指标
    returns_count = Column(Integer, default=0, comment="退货数")
    cancellations = Column(Integer, default=0, comment="取消数")
    position_avg = Column(Float, comment="平均搜索排名")

    # 计算指标（存储冗余便于快速查询）
    ctr = Column(Float, default=0.0, comment="搜索点击率 (%)")
    order_conversion = Column(Float, default=0.0, comment="订单转化率 (%)")

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", "product_id", "date", name="uq_user_analytics_daily"),
        Index("idx_analytics_daily_date", "date"),
        Index("idx_user_analytics_store_product", "user_id", "store_id", "product_id"),
    )

    def __repr__(self):
        return f"<AnalyticsDaily {self.product_id} {self.date}>"


class SyncLog(Base):
    """同步日志"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False)
    sync_type = Column(String(50), comment="同步类型: products/analytics")
    status = Column(String(20), comment="状态: success/error")
    message = Column(Text, comment="日志信息")
    created_at = Column(DateTime, server_default=func.now())


class Order(Base):
    """订单数据（FBO + FBS 统一模型）"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False, comment="所属店铺ID")
    posting_number = Column(String(100), nullable=False, comment="Ozon 订单号")

    # 订单类型
    order_type = Column(String(20), nullable=False, comment="订单类型: fbo/fbs")

    # 商品信息
    product_id = Column(Integer, nullable=False, comment="Ozon商品ID")
    offer_id = Column(String(100), comment="卖家货号")
    sku = Column(Integer, comment="SKU")
    product_name = Column(String(500), comment="商品名称")
    quantity = Column(Integer, default=1, comment="数量")
    price = Column(Float, default=0.0, comment="单价(RUB)")
    total_price = Column(Float, default=0.0, comment="总价(RUB)")

    # 订单状态
    status = Column(String(50), nullable=False, comment="订单状态")

    # 时间
    order_created_at = Column(DateTime, comment="订单创建时间")
    shipped_at = Column(DateTime, comment="发货时间")
    delivered_at = Column(DateTime, comment="交付时间")
    cancelled_at = Column(DateTime, comment="取消时间")

    # 财务（从订单接口获取）
    commission = Column(Float, default=0.0, comment="佣金(RUB)")
    payout = Column(Float, default=0.0, comment="实际结算金额(RUB)")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", "posting_number", "product_id",
                         name="uq_user_order_posting_product"),
        Index("idx_orders_user_store", "user_id", "store_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_date", "order_created_at"),
    )

    def __repr__(self):
        return f"<Order {self.posting_number}>"


class FinanceTransaction(Base):
    """Ozon 财务交易明细"""
    __tablename__ = "finance_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False, comment="所属店铺ID")

    transaction_id = Column(String(100), nullable=False, comment="Ozon 交易ID")
    transaction_type = Column(String(50), nullable=False, comment="交易类型")
    amount = Column(Float, nullable=False, comment="金额(RUB, 负数为支出)")
    currency = Column(String(10), default="RUB", comment="货币")
    transaction_date = Column(DateTime, nullable=False, comment="交易日期")

    posting_number = Column(String(100), comment="关联订单号")
    product_id = Column(Integer, comment="关联商品ID")
    description = Column(String(500), comment="交易描述")

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", "transaction_id",
                         name="uq_user_finance_transaction"),
        Index("idx_finance_user_store", "user_id", "store_id"),
        Index("idx_finance_date", "transaction_date"),
        Index("idx_finance_type", "transaction_type"),
    )

    def __repr__(self):
        return f"<FinanceTransaction {self.transaction_id}>"


class RealizationReport(Base):
    """销售实现报告（按商品的结算明细）"""
    __tablename__ = "realization_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False, comment="所属店铺ID")

    period_from = Column(Date, nullable=False, comment="期间开始")
    period_to = Column(Date, nullable=False, comment="期间结束")

    product_id = Column(Integer, nullable=False, comment="Ozon商品ID")
    offer_id = Column(String(100), comment="卖家货号")
    sku = Column(Integer, comment="SKU")
    product_name = Column(String(500), comment="商品名称")

    sold_units = Column(Integer, default=0, comment="销售数量")
    revenue = Column(Float, default=0.0, comment="销售收入(RUB)")
    commission = Column(Float, default=0.0, comment="佣金(RUB)")
    logistics_cost = Column(Float, default=0.0, comment="物流费(RUB)")
    marketing_cost = Column(Float, default=0.0, comment="广告营销费(RUB)")
    penalty = Column(Float, default=0.0, comment="罚款(RUB)")
    other_cost = Column(Float, default=0.0, comment="其他费用(RUB)")
    payout = Column(Float, default=0.0, comment="实际结算金额(RUB)")

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", "period_from", "period_to", "product_id",
                         name="uq_user_realization_product_period"),
        Index("idx_realization_user_store", "user_id", "store_id"),
    )

    def __repr__(self):
        return f"<RealizationReport {self.product_id} {self.period_from}-{self.period_to}>"


class ProductCost(Base):
    """商品采购成本（用户手动录入）"""
    __tablename__ = "product_costs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False, comment="所属店铺ID")
    product_id = Column(Integer, nullable=False, comment="Ozon商品ID")

    cost_price = Column(Float, default=0.0, comment="采购成本(CNY)")
    cost_updated_at = Column(DateTime, comment="成本最后更新时间")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", "product_id",
                         name="uq_user_product_cost"),
    )

    def __repr__(self):
        return f"<ProductCost product_id={self.product_id} cost={self.cost_price}>"


class ManualExpense(Base):
    """手动补录费用（头程物流、关税等）"""
    __tablename__ = "manual_expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, nullable=False, comment="所属店铺ID")

    product_id = Column(Integer, comment="关联商品ID（可为空，为空则计入总费用）")
    expense_type = Column(String(50), nullable=False, comment="费用类型: logistics/customs/other")
    amount_cny = Column(Float, nullable=False, comment="金额(CNY)")
    description = Column(String(500), comment="费用说明")
    expense_date = Column(Date, comment="费用发生日期")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ManualExpense {self.expense_type} {self.amount_cny}>"


class ExchangeRate(Base):
    """汇率配置（用户维护）"""
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    rate = Column(Float, nullable=False, default=12.0, comment="1 CNY = ? RUB")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ExchangeRate user_id={self.user_id} rate={self.rate}>"


class AlertRule(Base):
    """告警规则"""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="所属用户ID")
    store_id = Column(Integer, comment="关联店铺ID（为空则全局规则）")
    name = Column(String(100), nullable=False, comment="规则名称")
    rule_type = Column(String(50), nullable=False, comment="规则类型: sales_drop/stock/price_change/sync_fail")
    threshold = Column(Float, default=0.0, comment="阈值")
    channel = Column(String(50), default="email", comment="通知渠道: email/wechat_work/dingtalk/feishu")
    target = Column(String(500), default="", comment="接收地址")
    enabled = Column(Boolean, default=True, comment="是否启用")
    last_triggered = Column(DateTime, comment="最后触发时间")
    description = Column(String(500), comment="规则描述")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<AlertRule {self.name} ({self.rule_type})>"


# ==================== SaaS 订阅计费模型 ====================


class Plan(Base):
    """订阅套餐定义"""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="套餐标识: free/pro/enterprise")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    price_cents = Column(Integer, nullable=False, default=0, comment="月费(美分), 0=免费")
    currency = Column(String(10), default="usd", comment="货币")
    stripe_price_id = Column(String(100), comment="Stripe Price ID")
    limits = Column(JSON, nullable=False, comment="套餐限额 JSON")
    is_active = Column(Boolean, default=True, comment="是否可订阅")
    sort_order = Column(Integer, default=0, comment="排序权重")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_plans_name", "name"),
    )

    def __repr__(self):
        return f"<Plan {self.name}>"


class Subscription(Base):
    """用户订阅"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="用户ID")
    plan_id = Column(Integer, nullable=False, comment="套餐ID")

    status = Column(String(20), nullable=False, default="trialing", comment="状态: trialing/active/past_due/cancelled/expired")
    stripe_subscription_id = Column(String(100), comment="Stripe Subscription ID")
    stripe_customer_id = Column(String(100), comment="Stripe Customer ID")

    trial_start = Column(DateTime, comment="试用开始时间")
    trial_end = Column(DateTime, comment="试用结束时间")
    current_period_start = Column(DateTime, comment="当前计费周期开始")
    current_period_end = Column(DateTime, comment="当前计费周期结束")
    cancelled_at = Column(DateTime, comment="取消时间")
    expired_at = Column(DateTime, comment="过期时间")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_sub_user", "user_id"),
        Index("idx_sub_status", "status"),
        Index("idx_sub_stripe", "stripe_subscription_id"),
    )

    def __repr__(self):
        return f"<Subscription user={self.user_id} plan={self.plan_id} status={self.status}>"


class PaymentHistory(Base):
    """支付历史"""
    __tablename__ = "payment_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="用户ID")
    subscription_id = Column(Integer, comment="订阅ID")

    stripe_invoice_id = Column(String(100), comment="Stripe Invoice ID")
    amount_cents = Column(Integer, nullable=False, comment="金额(美分)")
    currency = Column(String(10), default="usd", comment="货币")
    status = Column(String(20), nullable=False, comment="支付状态: paid/failed/refunded")
    description = Column(String(500), comment="描述")
    paid_at = Column(DateTime, comment="支付时间")

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_payment_user", "user_id"),
        Index("idx_payment_stripe", "stripe_invoice_id"),
    )

    def __repr__(self):
        return f"<PaymentHistory user={self.user_id} amount={self.amount_cents}>"


class Usage(Base):
    """用量统计"""
    __tablename__ = "usages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, comment="用户ID")
    resource = Column(String(50), nullable=False, comment="资源类型: stores/alerts/syncs/api_calls")
    quantity = Column(Integer, nullable=False, default=0, comment="使用量")
    period = Column(String(7), nullable=False, comment="统计周期: YYYY-MM")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "resource", "period", name="uq_user_resource_period"),
        Index("idx_usage_user_period", "user_id", "period"),
    )

    def __repr__(self):
        return f"<Usage user={self.user_id} {self.resource}={self.quantity}>"


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, comment="操作用户ID（系统操作为空）")
    action = Column(String(100), nullable=False, comment="操作类型: login/register/store.create/subscription.change...")
    target_type = Column(String(50), comment="目标类型: user/store/subscription")
    target_id = Column(String(100), comment="目标ID")
    detail = Column(JSON, comment="操作详情 JSON")
    ip_address = Column(String(50), comment="IP 地址")
    user_agent = Column(String(500), comment="User-Agent")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", "created_at"),
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by user={self.user_id}>"
