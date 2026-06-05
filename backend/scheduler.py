"""定时数据采集调度器"""
import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict

from database import SessionLocal
from models import Store, Product, AnalyticsDaily, SyncLog
from ozon_client import OzonClient
from crypto import decrypt_value

logger = logging.getLogger(__name__)


def _get_proxy_url() -> str:
    """从环境变量读取代理配置"""
    return os.environ.get("OZON_PROXY_URL", "")


def _make_ozon_client(store: Store) -> OzonClient:
    """为指定店铺创建 OzonClient（自动解密 API Key + 配置代理）"""
    return OzonClient(store.client_id, decrypt_value(store.api_key), proxy_url=_get_proxy_url())

# Ozon Analytics 可用指标映射（Ozon 限制最多 14 个）
ANALYTICS_METRICS = [
    "hits_view_search",       # 搜索曝光量
    "hits_view_pdp",          # 商品页浏览量
    "hits_view",              # 总浏览量
    "session_view",           # 会话数
    "hits_tocart",            # 加购总数
    "hits_tocart_search",     # 搜索加购数
    "hits_tocart_pdp",        # PDP加购数
    "conv_tocart",            # 加购转化率
    "revenue",                # 销售额
    "ordered_units",          # 下单件数
    "delivered_units",        # 发货件数
    "returns",                # 退货数
    "cancellations",          # 取消数
    "position_category",      # 类目排名
]


def _parse_analytics_row(row: Dict, metric_names: List[str]) -> Dict:
    """将 Ozon Analytics 返回的原始行转换为标准字段

    Ozon API 响应格式:
    {
        "dimensions": [{"id": "sku_value", "name": "product_name"}, {"id": "2026-06-03", "name": ""}],
        "metrics": [val1, val2, val3, ...]   # 按请求的 metrics 顺序排列
    }
    """
    dimensions = row.get("dimensions", [])
    metrics = row.get("metrics", [])

    result = {}

    # 解析维度（按位置映射）
    for i, d in enumerate(dimensions):
        if i == 0:  # 第一个维度 = SKU
            raw_id = d.get("id", "0")
            try:
                result["sku"] = int(raw_id)
            except (ValueError, TypeError):
                result["sku"] = 0
            result["sku_name"] = d.get("name", "")
        elif i == 1:  # 第二个维度 = 日期
            result["date"] = d.get("id", "")
        elif i == 2:
            result["spu"] = d.get("id")

    # 解析指标（按位置映射到 metric_names）
    for i, val in enumerate(metrics):
        if i < len(metric_names):
            metric_id = metric_names[i]
            if val is None:
                val = 0
            result[metric_id] = float(val) if metric_id in ("revenue", "conv_tocart", "position_category") else int(val)

    return result


def sync_products_for_store(store_id: int):
    """同步指定店铺的商品列表"""
    db = SessionLocal()
    try:
        store = db.query(Store).filter_by(id=store_id, is_active=True).first()
        if not store:
            logger.warning(f"Store {store_id} not found or inactive")
            return

        client = _make_ozon_client(store)
        if not client.health_check():
            db.add(SyncLog(store_id=store_id, sync_type="products", status="error",
                           message="API 连接失败：请检查店铺的 Client-Id 和 Api-Key 是否正确，或密钥是否已过期"))
            db.commit()
            logger.error(f"Product sync aborted for store {store_id}: API health check failed (invalid credentials or network issue)")
            return

        logger.info(f"Syncing products for store: {store.name}")

        # 1. 获取所有商品
        products_raw = client.get_all_products()
        product_ids = [p["product_id"] for p in products_raw]

        if not product_ids:
            logger.info(f"No products found for store {store.name}")
            return

        # 2. 批量获取详细信息 — V3 API 返回 {"items": [...]}
        info_data = client.get_product_info_list(product_ids)
        info_items = info_data.get("items", [])
        info_map = {item["id"]: item for item in info_items}

        # 3. 批量获取价格 — V5 API 返回 {"result": {"items": [...]}}
        prices_data = client.get_product_prices(product_ids[:1000])
        price_items = prices_data.get("result", {}).get("items", [])
        price_map = {p["product_id"]: p for p in price_items}

        # 4. 更新数据库
        updated = 0
        created = 0
        for p in products_raw:
            pid = p["product_id"]
            info = info_map.get(pid, {})
            price_info = price_map.get(pid, {}).get("price", {})

            existing = db.query(Product).filter_by(store_id=store_id, product_id=pid).first()
            price_val = float(price_info.get("price", "0") or 0)
            old_price_val = float(price_info.get("old_price", "0") or 0)

            # 从 sources 中提取 SKU（Ozon v3 API 将 SKU 放在 sources 数组里）
            sku = None
            sources = info.get("sources", [])
            if sources:
                sku = sources[0].get("sku")

            if existing:
                existing.offer_id = p.get("offer_id", "")
                existing.name = info.get("name", "")
                existing.price = price_val
                existing.old_price = old_price_val
                existing.currency = price_info.get("currency_code", "RUB")
                existing.barcode = info.get("barcode", "")
                existing.category = str(info.get("description_category_id", ""))
                existing.status = info.get("state", "")
                existing.sku = sku
                updated += 1
            else:
                db.add(Product(
                    store_id=store_id,
                    offer_id=p.get("offer_id", ""),
                    product_id=pid,
                    sku=sku,
                    name=info.get("name", ""),
                    price=price_val,
                    old_price=old_price_val,
                    currency=price_info.get("currency_code", "RUB"),
                    barcode=info.get("barcode", ""),
                    category=str(info.get("description_category_id", "")),
                    status=info.get("state", ""),
                ))
                created += 1

        store.last_sync_at = datetime.now()
        db.commit()

        # 记录同步日志
        db.add(SyncLog(store_id=store_id, sync_type="products", status="success",
                       message=f"Updated: {updated}, Created: {created}"))
        db.commit()
        logger.info(f"Product sync done for {store.name}: updated={updated}, created={created}")

    except Exception as e:
        db.rollback()
        # 检测常见错误类型，给用户更友好的提示
        error_msg = "Product sync failed, see server logs for details"
        err_str = str(e).lower()
        if "invalid" in err_str and "api-key" in err_str:
            error_msg = "API 密钥无效：请检查店铺的 Api-Key 是否正确或已过期"
        elif "proxy" in err_str or "connection" in err_str:
            error_msg = "网络连接失败：请检查网络或代理设置（OZON_PROXY_URL）"
        db.add(SyncLog(store_id=store_id, sync_type="products", status="error",
                       message=error_msg))
        db.commit()
        logger.error(f"Product sync failed for store {store_id}: {e}", exc_info=True)
    finally:
        db.close()


def sync_analytics_for_store(store_id: int, target_date=None, product_ids: List[int] = None):
    """同步指定店铺的分析数据（按天），可选指定商品ID列表"""
    # 防御：确保 target_date 是 date 对象
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    elif isinstance(target_date, str):
        from datetime import datetime as _dt
        target_date = _dt.strptime(target_date, "%Y-%m-%d").date()

    date_str = target_date.strftime("%Y-%m-%d")
    db = SessionLocal()
    try:
        store = db.query(Store).filter_by(id=store_id, is_active=True).first()
        if not store:
            return

        client = _make_ozon_client(store)
        logger.info(f"Syncing analytics for store={store.name}, date={date_str}")

        # 获取分析数据（按 SKU + 天 维度）
        raw_data = client.get_all_analytics_data(
            date_from=date_str,
            date_to=date_str,
            metrics=ANALYTICS_METRICS,
            dimensions=["sku", "day"],
        )

        # 批量预加载所有 SKU → Product 映射（避免 N+1 查询）
        all_products = db.query(Product).filter_by(store_id=store_id).all()
        sku_to_product = {p.sku: p for p in all_products if p.sku}

        # 批量预加载已有分析数据（避免逐条 UPSERT 查询）
        analytics_existing = db.query(AnalyticsDaily).filter_by(
            store_id=store_id, date=target_date
        ).all()
        analytics_map = {(a.product_id, a.date): a for a in analytics_existing}

        processed = 0
        for row in raw_data:
            parsed = _parse_analytics_row(row, ANALYTICS_METRICS)
            sku_val = parsed.get("sku")
            row_date_str = parsed.get("date", date_str)

            if not sku_val:
                continue

            # 从预加载映射中查找商品
            product = sku_to_product.get(sku_val)
            if not product:
                continue

            # 如果指定了商品ID列表，只处理匹配的商品
            if product_ids and product.product_id not in product_ids:
                continue

            try:
                row_date = datetime.strptime(row_date_str[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                row_date = target_date

            # 计算衍生指标
            views_search = parsed.get("hits_view_search", 0)
            views_pdp = parsed.get("hits_view_pdp", 0)
            views_total = parsed.get("hits_view", 0)
            add_to_cart = parsed.get("hits_tocart", 0)
            sessions = parsed.get("session_view", 0)
            ordered_units = parsed.get("ordered_units", 0)
            conversion_raw = parsed.get("conv_tocart", 0)

            # CTR: 搜索点击率（PDP浏览 / 搜索曝光）
            ctr = (views_pdp / views_search * 100) if views_search > 0 else 0.0

            # 订单转化率（下单 / 浏览）
            order_conv = (ordered_units / views_total * 100) if views_total > 0 else 0.0

            # 加购率: Ozon API conv_tocart 返回小数比例（如 0.05 = 5%），需 * 100 转百分比
            # 参考: https://docs.ozon.ru/api/seller/#operation/AnalyticsAPI_GetData
            cart_conv = conversion_raw * 100

            # UPSERT - 使用预加载映射
            existing = analytics_map.get((product.product_id, row_date))

            data = {
                "store_id": store_id,
                "product_id": product.product_id,
                "offer_id": product.offer_id,
                "sku": sku_val,
                "date": row_date,
                "impressions_search": views_search,
                "views_pdp": views_pdp,
                "views_total": views_total,
                "sessions": sessions,
                "add_to_cart": add_to_cart,
                "add_to_cart_search": parsed.get("hits_tocart_search", 0),
                "add_to_cart_pdp": parsed.get("hits_tocart_pdp", 0),
                "conversion_to_cart": round(cart_conv, 4),
                "conversion_search_to_cart": 0.0,
                "conversion_pdp_to_cart": 0.0,
                "ordered_units": ordered_units,
                "delivered_units": parsed.get("delivered_units", 0),
                "revenue": float(parsed.get("revenue", 0)),
                "returns_count": parsed.get("returns", 0),
                "cancellations": parsed.get("cancellations", 0),
                "position_avg": parsed.get("position_category"),
                "ctr": round(ctr, 4),
                "order_conversion": round(order_conv, 4),
            }

            if existing:
                for k, v in data.items():
                    if k not in ("store_id", "product_id", "date", "created_at"):
                        setattr(existing, k, v)
            else:
                db.add(AnalyticsDaily(**data))

            processed += 1

        db.commit()
        # 更新店铺最后同步时间
        store.last_sync_at = datetime.now()
        db.add(SyncLog(store_id=store_id, sync_type="analytics", status="success",
                       message=f"Processed {processed} products for {date_str}"))
        db.commit()
        logger.info(f"Analytics sync done for {store.name}: {processed} products on {date_str}")

    except Exception as e:
        db.rollback()
        err_str = str(e).lower()
        # 友好提示（前端展示）
        friendly_msg = "同步失败"
        if "invalid" in err_str and "api-key" in err_str:
            friendly_msg = "API 密钥无效：请检查店铺的 Api-Key 是否正确或已过期"
        elif "proxy" in err_str or "connection" in err_str:
            friendly_msg = "网络连接失败：请检查网络或代理设置（OZON_PROXY_URL）"
        elif "rate limit" in err_str or "429" in err_str:
            friendly_msg = "请求过于频繁：Ozon API 限流，请稍后重试或减少同步天数"
        elif "none" in err_str and "get" in err_str:
            friendly_msg = "Ozon API 返回空数据：可能是限流或该日期无数据"
        # 日志中记录完整异常（含堆栈），前端展示友好提示 + 简要异常
        detail = f"{friendly_msg} | {type(e).__name__}: {str(e)[:200]}"
        db.add(SyncLog(store_id=store_id, sync_type="analytics", status="error",
                       message=detail))
        db.commit()
        logger.error(f"Analytics sync failed for store {store_id}: {e}", exc_info=True)
    finally:
        db.close()


def sync_all_stores():
    """同步所有活跃店铺的产品和分析数据"""
    db = SessionLocal()
    try:
        stores = db.query(Store).filter_by(is_active=True).all()
        for store in stores:
            try:
                sync_products_for_store(store.id)
                sync_analytics_for_store(store.id)
            except Exception as e:
                logger.error(f"Sync failed for store {store.name}: {e}")
    finally:
        db.close()


def sync_analytics_all_stores():
    """仅同步所有活跃店铺的分析数据（每日定时任务）"""
    db = SessionLocal()
    try:
        stores = db.query(Store).filter_by(is_active=True).all()
        for store in stores:
            try:
                sync_analytics_for_store(store.id)
            except Exception as e:
                logger.error(f"Analytics sync failed for store {store.name}: {e}")
    finally:
        db.close()
