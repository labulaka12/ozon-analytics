"""Ozon 数据分析系统 - FastAPI 后端"""
import os
import logging
from datetime import date, timedelta, datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import asyncio

# 加载 .env 环境变量（需在 import 其他模块之前）
from dotenv import load_dotenv
_load_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_load_path, override=False)

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, get_db
from models import Store, Product, AnalyticsDaily, SyncLog
from ozon_client import OzonClient
from crypto import encrypt_value, decrypt_value
from scheduler import sync_all_stores, sync_analytics_all_stores, sync_products_for_store, sync_analytics_for_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化DB & 定时器，关闭时停止定时器"""
    init_db()
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(sync_analytics_all_stores, "cron", hour=8, minute=0, id="daily_sync")
    scheduler.start()
    logger.info("Scheduler started: daily analytics sync at 08:00")

    app.state.scheduler = scheduler
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Ozon Analytics",
    description="Ozon 店铺数据分析系统",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置：从环境变量读取允许的源，未配置则默认仅允许本地访问
_cors_origins_str = os.environ.get("CORS_ORIGINS", "")
if _cors_origins_str:
    CORS_ORIGINS = [o.strip() for o in _cors_origins_str.split(",") if o.strip()]
else:
    # 开发模式默认值
    CORS_ORIGINS = ["http://localhost:8848", "http://127.0.0.1:8848"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 工具函数 ====================

def resolve_date_range(date_from: Optional[str], date_to: Optional[str], default_days: int = 30) -> tuple:
    """统一处理日期范围默认值

    Args:
        date_from: 起始日期字符串 (YYYY-MM-DD)，为空时默认为 default_days 天前
        date_to: 结束日期字符串 (YYYY-MM-DD)，为空时默认为今天
        default_days: date_from 缺省时回溯天数

    Returns:
        (date_from, date_to) 元组，格式为 YYYY-MM-DD 字符串
    """
    if not date_to:
        date_to = date.today().strftime("%Y-%m-%d")
    if not date_from:
        date_from = (date.today() - timedelta(days=default_days)).strftime("%Y-%m-%d")
    return date_from, date_to


# ==================== Pydantic 模型 ====================

class StoreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    client_id: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)


class StoreUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    client_id: Optional[str] = Field(None, min_length=1)
    api_key: Optional[str] = Field(None, min_length=1)


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    client_id: str
    is_active: bool
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    product_count: Optional[int] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    offer_id: str
    product_id: int
    sku: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None


class AnalyticsRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    offer_id: str
    sku: Optional[int]
    name: Optional[str]
    date: str
    impressions_search: int
    views_pdp: int
    views_total: int
    sessions: int
    add_to_cart: int
    conversion_to_cart: float
    ctr: float
    order_conversion: float
    ordered_units: int
    revenue: float
    returns_count: int
    cancellations: int
    position_avg: Optional[float]


class SyncRequest(BaseModel):
    store_id: int
    target_date: Optional[str] = None  # YYYY-MM-DD
    target_dates: Optional[List[str]] = None  # 多日期同步
    product_ids: Optional[List[int]] = None  # 指定商品ID列表


class SyncLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    sync_type: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    created_at: Optional[datetime] = None


# ==================== 店铺管理 ====================

@app.get("/api/stores", response_model=List[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    """获取所有店铺列表"""
    stores = db.query(Store).all()
    result = []
    for s in stores:
        p_count = db.query(func.count(Product.id)).filter_by(store_id=s.id).scalar()
        result.append(StoreOut(
            id=s.id, name=s.name, client_id=s.client_id[:8] + "***",
            is_active=s.is_active, last_sync_at=s.last_sync_at,
            created_at=s.created_at, product_count=p_count
        ))
    return result


@app.post("/api/stores")
def create_store(data: StoreCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """绑定新店铺"""
    # 校验 API 连通性（使用用户提交的明文密钥，尚未加密存储）
    _proxy_url = os.environ.get("OZON_PROXY_URL", "")
    client = OzonClient(data.client_id, data.api_key, proxy_url=_proxy_url)
    if not client.health_check():
        raise HTTPException(400, "API 连接失败：请检查 Client-Id 和 Api-Key")

    existing = db.query(Store).filter_by(client_id=data.client_id).first()
    if existing:
        raise HTTPException(400, "该店铺已存在")
    store = Store(name=data.name, client_id=data.client_id, api_key=encrypt_value(data.api_key))
    db.add(store)
    db.commit()
    db.refresh(store)

    # 后台异步同步商品和分析数据（避免阻塞 HTTP 请求）
    store_id = store.id
    background_tasks.add_task(sync_products_for_store, store_id)
    background_tasks.add_task(sync_analytics_for_store, store_id)

    return {"id": store.id, "message": "店铺创建成功，正在后台同步商品和分析数据..."}


@app.put("/api/stores/{store_id}")
def update_store(store_id: int, data: StoreUpdate, db: Session = Depends(get_db)):
    """更新店铺信息（支持部分更新）"""
    store = db.query(Store).filter_by(id=store_id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")
    if data.name is not None:
        store.name = data.name
    if data.client_id is not None:
        store.client_id = data.client_id
    if data.api_key is not None:
        store.api_key = encrypt_value(data.api_key)
    db.commit()
    return {"message": "更新成功"}


@app.delete("/api/stores/{store_id}")
def delete_store(store_id: int, db: Session = Depends(get_db)):
    """删除店铺（及关联数据）"""
    store = db.query(Store).filter_by(id=store_id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")
    db.query(AnalyticsDaily).filter_by(store_id=store_id).delete()
    db.query(Product).filter_by(store_id=store_id).delete()
    db.delete(store)
    db.commit()
    return {"message": "删除成功"}


# ==================== 商品管理 ====================

@app.get("/api/products", response_model=List[ProductOut])
def list_products(store_id: int = Query(...), db: Session = Depends(get_db)):
    """获取指定店铺的商品列表"""
    return db.query(Product).filter_by(store_id=store_id).order_by(Product.id).all()


@app.get("/api/products/{product_id}")
def get_product(store_id: int, product_id: int, db: Session = Depends(get_db)):
    """获取单个商品详情"""
    p = db.query(Product).filter_by(store_id=store_id, product_id=product_id).first()
    if not p:
        raise HTTPException(404, "商品不存在")
    return {
        "id": p.id, "store_id": p.store_id, "offer_id": p.offer_id,
        "product_id": p.product_id, "sku": p.sku, "name": p.name,
        "category": p.category, "price": p.price, "old_price": p.old_price,
        "currency": p.currency, "barcode": p.barcode, "status": p.status,
    }


# ==================== 分析数据 ====================

@app.get("/api/analytics")
def get_analytics(
    store_id: int = Query(...),
    product_ids: Optional[str] = Query(None, description="逗号分隔商品ID"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """获取分析数据（支持多商品、日期范围）

    返回格式:
    {
        "items": [{...}, ...],
        "dates": ["2026-06-01", "2026-06-02", ...],
        "products": [{"product_id": 123, "offer_id": "xxx", "name": "xxx"}, ...]
    }
    """
    date_from, date_to = resolve_date_range(date_from, date_to, default_days=30)

    query = db.query(AnalyticsDaily).filter(
        AnalyticsDaily.store_id == store_id,
        AnalyticsDaily.date >= date_from,
        AnalyticsDaily.date <= date_to,
    )

    if product_ids:
        pids = [int(x.strip()) for x in product_ids.split(",") if x.strip()]
        query = query.filter(AnalyticsDaily.product_id.in_(pids))

    rows = query.order_by(AnalyticsDaily.date.asc(), AnalyticsDaily.product_id).all()

    # 构建响应
    items = []
    seen_dates = set()
    seen_products = {}

    for r in rows:
        items.append({
            "product_id": r.product_id,
            "offer_id": r.offer_id,
            "sku": r.sku,
            "date": r.date.strftime("%Y-%m-%d"),
            "impressions_search": r.impressions_search,
            "views_pdp": r.views_pdp,
            "views_total": r.views_total,
            "sessions": r.sessions,
            "add_to_cart": r.add_to_cart,
            "conversion_to_cart": r.conversion_to_cart,
            "ctr": r.ctr,
            "order_conversion": r.order_conversion,
            "ordered_units": r.ordered_units,
            "revenue": round(r.revenue, 2),
            "returns_count": r.returns_count,
            "cancellations": r.cancellations,
            "position_avg": r.position_avg,
        })
        seen_dates.add(r.date.strftime("%Y-%m-%d"))

    # 获取商品信息
    if product_ids:
        pid_list = [int(x.strip()) for x in product_ids.split(",") if x.strip()]
    else:
        pid_list = list(set(r.product_id for r in rows))

    products_info = db.query(Product).filter(
        Product.store_id == store_id, Product.product_id.in_(pid_list) if pid_list else True
    ).all()
    for p in products_info:
        seen_products[p.product_id] = {"product_id": p.product_id, "offer_id": p.offer_id, "name": p.name or p.offer_id}

    return {
        "items": items,
        "dates": sorted(list(seen_dates)),
        "products": list(seen_products.values()),
    }


@app.get("/api/analytics/summary")
def get_analytics_summary(
    store_id: int = Query(...),
    product_ids: Optional[str] = Query(None, description="逗号分隔商品ID"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """获取分析数据汇总（支持按商品过滤）"""
    date_from, date_to = resolve_date_range(date_from, date_to, default_days=7)

    filters = [
        AnalyticsDaily.store_id == store_id,
        AnalyticsDaily.date >= date_from,
        AnalyticsDaily.date <= date_to,
    ]
    if product_ids:
        pids = [int(x.strip()) for x in product_ids.split(",") if x.strip()]
        filters.append(AnalyticsDaily.product_id.in_(pids))

    query = db.query(
        func.sum(AnalyticsDaily.impressions_search).label("total_impressions"),
        func.sum(AnalyticsDaily.views_pdp).label("total_views_pdp"),
        func.sum(AnalyticsDaily.views_total).label("total_views"),
        func.sum(AnalyticsDaily.sessions).label("total_sessions"),
        func.sum(AnalyticsDaily.add_to_cart).label("total_add_to_cart"),
        func.sum(AnalyticsDaily.ordered_units).label("total_ordered"),
        func.sum(AnalyticsDaily.revenue).label("total_revenue"),
        func.sum(AnalyticsDaily.returns_count).label("total_returns"),
        func.sum(AnalyticsDaily.cancellations).label("total_cancellations"),
        func.count(func.distinct(AnalyticsDaily.date)).label("days_with_data"),
    ).filter(*filters).first()

    return {
        "total_impressions": query.total_impressions or 0,
        "total_views_pdp": query.total_views_pdp or 0,
        "total_views": query.total_views or 0,
        "total_sessions": query.total_sessions or 0,
        "total_add_to_cart": query.total_add_to_cart or 0,
        "total_ordered": query.total_ordered or 0,
        "total_revenue": round(query.total_revenue or 0, 2),
        "total_returns": query.total_returns or 0,
        "total_cancellations": query.total_cancellations or 0,
        "days_with_data": query.days_with_data or 0,
        "date_from": date_from,
        "date_to": date_to,
    }


# ==================== 数据同步 ====================

@app.post("/api/sync/{sync_type}")
def trigger_sync(
    sync_type: str,
    data: SyncRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """手动触发数据同步

    sync_type: products | analytics | all
    """
    store = db.query(Store).filter_by(id=data.store_id).first()
    if not store:
        raise HTTPException(404, "店铺不存在")

    try:
        target_date = None
        if data.target_date:
            target_date = datetime.strptime(data.target_date, "%Y-%m-%d").date()

        if sync_type == "products":
            background_tasks.add_task(sync_products_for_store, data.store_id)
        elif sync_type == "analytics":
            dates_to_sync = []
            if data.target_dates:
                dates_to_sync = [datetime.strptime(d, "%Y-%m-%d").date() for d in data.target_dates]
            elif data.target_date:
                dates_to_sync = [datetime.strptime(data.target_date, "%Y-%m-%d").date()]
            else:
                dates_to_sync = [date.today() - timedelta(days=1)]

            for d in dates_to_sync:
                background_tasks.add_task(sync_analytics_for_store, data.store_id, d, data.product_ids)
            return {"message": f"后台同步已触发: {len(dates_to_sync)} 天分析数据"}
        elif sync_type == "all":
            background_tasks.add_task(sync_products_for_store, data.store_id)
            dates_to_sync = []
            if data.target_dates:
                dates_to_sync = [datetime.strptime(d, "%Y-%m-%d").date() for d in data.target_dates]
            elif data.target_date:
                dates_to_sync = [datetime.strptime(data.target_date, "%Y-%m-%d").date()]
            else:
                dates_to_sync = [date.today() - timedelta(days=1)]
            for d in dates_to_sync:
                background_tasks.add_task(sync_analytics_for_store, data.store_id, d, data.product_ids)
            return {"message": f"后台同步已触发: 商品 + {len(dates_to_sync)} 天分析数据"}
        else:
            raise HTTPException(400, "不支持的操作类型: " + sync_type)

        return {"message": f"后台同步任务已触发: {sync_type}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync trigger failed: {e}")
        raise HTTPException(500, "同步任务触发失败，请查看日志")


@app.get("/api/sync/logs", response_model=List[SyncLogOut])
def get_sync_logs(store_id: Optional[int] = None, limit: int = 20, db: Session = Depends(get_db)):
    """获取同步日志"""
    q = db.query(SyncLog)
    if store_id:
        q = q.filter_by(store_id=store_id)
    return q.order_by(SyncLog.created_at.desc()).limit(limit).all()


# ==================== 数据导出 ====================

import csv
import io

@app.get("/api/export/csv")
def export_csv(
    store_id: int = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出分析数据为 CSV（使用标准 csv 模块，安全处理特殊字符）"""
    date_from, date_to = resolve_date_range(date_from, date_to, default_days=30)

    rows = db.query(AnalyticsDaily).filter(
        AnalyticsDaily.store_id == store_id,
        AnalyticsDaily.date >= date_from,
        AnalyticsDaily.date <= date_to,
    ).order_by(AnalyticsDaily.date.asc()).all()

    # 获取商品名称映射
    pid_list = list(set(r.product_id for r in rows))
    products = db.query(Product).filter(Product.store_id == store_id, Product.product_id.in_(pid_list)).all()
    name_map = {p.product_id: p.name or p.offer_id for p in products}

    # 使用标准 csv 模块写入（自动处理引号、逗号、换行等特殊字符）
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["offer_id", "product_id", "sku", "名称", "日期", "搜索曝光", "PDP浏览", "总浏览", "会话数", "加购数", "加购率(%)", "点击率(%)", "订单转化率(%)", "下单件数", "销售额(RUB)", "退货数", "取消数", "平均排名"])
    for r in rows:
        writer.writerow([
            r.offer_id, r.product_id, r.sku, name_map.get(r.product_id, ""),
            r.date, r.impressions_search, r.views_pdp, r.views_total, r.sessions,
            r.add_to_cart, r.conversion_to_cart, r.ctr, r.order_conversion,
            r.ordered_units, r.revenue, r.returns_count, r.cancellations,
            r.position_avg or "",
        ])

    from fastapi.responses import Response
    # UTF-8 BOM 确保 Excel 正确识别编码
    bom = "\ufeff"
    return Response(
        content=bom + output.getvalue(),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=ozon_analytics_{date_from}_{date_to}.csv"}
    )


# ==================== 静态文件 ====================

import os
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
os.makedirs(FRONTEND_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    """首页重定向到看板"""
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8848, reload=True)
