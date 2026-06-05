"""数据库模型定义"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Boolean, UniqueConstraint, Index
from sqlalchemy.sql import func
from database import Base


class Store(Base):
    """Ozon 店铺"""
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
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
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_store_product"),
        Index("idx_store_product", "store_id", "product_id"),
    )

    def __repr__(self):
        return f"<Product {self.offer_id}>"


class AnalyticsDaily(Base):
    """每日分析数据"""
    __tablename__ = "analytics_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
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
        UniqueConstraint("store_id", "product_id", "date", name="uq_analytics_daily"),
        Index("idx_analytics_daily_date", "date"),
        Index("idx_analytics_daily_store_product", "store_id", "product_id"),
    )

    def __repr__(self):
        return f"<AnalyticsDaily {self.product_id} {self.date}>"


class SyncLog(Base):
    """同步日志"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, nullable=False)
    sync_type = Column(String(50), comment="同步类型: products/analytics")
    status = Column(String(20), comment="状态: success/error")
    message = Column(Text, comment="日志信息")
    created_at = Column(DateTime, server_default=func.now())
