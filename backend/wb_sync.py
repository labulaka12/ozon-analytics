"""Wildberries 数据同步器

负责将 WB 数据同步到本系统的标准模型（Product / AnalyticsDaily / Order）。

数据映射：
  WB 商品 ↔ Product（platform = 'wb'）
  WB 订单 ↔ Order（order_type = 'wb'）
  WB 销售报告 ↔ RealizationReport

多平台方案：
  本系统用 user_id 和 store_id 做多租户隔离，
  WB 店铺也作为 Store 创建，type='wb' 区分。
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict

from database import SessionLocal
from models import Store, Product, SyncLog
from wb_client import WBClient
from crypto import decrypt_value

logger = logging.getLogger(__name__)


def sync_wb_products(store_id: int):
    """同步 WB 商品"""
    db = SessionLocal()
    try:
        store = db.query(Store).filter_by(id=store_id, is_active=True).first()
        if not store:
            logger.warning(f"Store {store_id} not found or inactive")
            return

        client = WBClient(decrypt_value(store.api_key))  # WB 用 api_key 字段存 token
        logger.info(f"Syncing WB products for store: {store.name}")

        # 获取商品列表
        catalog = client.get_cards_catalog()
        cards = catalog.get("cards", [])

        updated = 0
        created = 0
        for card in cards:
            nm_id = card.get("nmID")
            if not nm_id:
                continue

            # 从 card 中提取信息
            sizes = card.get("sizes", [])
            price = 0
            if sizes:
                price = float(sizes[0].get("price", 0) or 0)

            photos = card.get("photos", [])
            images = [p.get("big", "") for p in photos if p.get("big")] if photos else []

            existing = db.query(Product).filter_by(
                store_id=store_id, product_id=nm_id
            ).first()

            if existing:
                existing.offer_id = card.get("vendorCode", "")
                existing.name = card.get("title", "")
                existing.price = price
                existing.images = str(images) if images else None
                existing.status = card.get("status", {}).get("wb", "")
                updated += 1
            else:
                db.add(Product(
                    store_id=store_id,
                    user_id=store.user_id,
                    offer_id=card.get("vendorCode", ""),
                    product_id=nm_id,
                    name=card.get("title", ""),
                    price=price,
                    images=str(images) if images else None,
                    status=card.get("status", {}).get("wb", ""),
                ))
                created += 1

        store.last_sync_at = datetime.now()
        db.add(SyncLog(store_id=store_id, sync_type="wb_products", status="success",
                       message=f"Updated: {updated}, Created: {created}"))
        db.commit()
        logger.info(f"WB product sync done for {store.name}: updated={updated}, created={created}")

    except Exception as e:
        db.rollback()
        db.add(SyncLog(store_id=store_id, sync_type="wb_products", status="error",
                       message=f"Sync failed: {str(e)[:200]}"))
        db.commit()
        logger.error(f"WB product sync failed for store {store_id}: {e}", exc_info=True)
    finally:
        db.close()


def sync_wb_orders(store_id: int, date_from: str, date_to: str):
    """同步 WB 订单"""
    db = SessionLocal()
    try:
        store = db.query(Store).filter_by(id=store_id, is_active=True).first()
        if not store:
            return

        client = WBClient(decrypt_value(store.api_key))
        logger.info(f"Syncing WB orders for store: {store.name}, {date_from} ~ {date_to}")

        from models import Order
        orders_data = client.get_orders(date_from, date_to)
        orders_list = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])

        processed = 0
        for o in orders_list:
            posting_number = str(o.get("id", ""))
            if not posting_number:
                continue

            products = o.get("products", [o])
            for p in products:
                pid = p.get("nmId", p.get("product_id", 0))
                existing = db.query(Order).filter_by(
                    store_id=store_id,
                    posting_number=posting_number,
                    product_id=pid,
                ).first()

                row = {
                    "user_id": store.user_id,
                    "store_id": store_id,
                    "posting_number": posting_number,
                    "order_type": "wb",
                    "product_id": pid,
                    "offer_id": p.get("vendorCode", ""),
                    "product_name": p.get("productName", ""),
                    "quantity": int(p.get("quantity", 1)),
                    "price": float(p.get("price", "0") or 0),
                    "total_price": float(p.get("totalPrice", "0") or 0),
                    "status": o.get("status", ""),
                    "order_created_at": _parse_wb_dt(o.get("dateCreated") or o.get("createdAt")),
                }

                if existing:
                    for k, v in row.items():
                        if k not in ("id", "created_at"):
                            setattr(existing, k, v)
                else:
                    db.add(Order(**row))
                processed += 1

        db.commit()
        db.add(SyncLog(store_id=store_id, sync_type="wb_orders", status="success",
                       message=f"Processed {processed} orders"))
        db.commit()
        logger.info(f"WB orders sync done for {store.name}: {processed} orders")

    except Exception as e:
        db.rollback()
        db.add(SyncLog(store_id=store_id, sync_type="wb_orders", status="error",
                       message=f"Sync failed: {str(e)[:200]}"))
        db.commit()
        logger.error(f"WB orders sync failed for store {store_id}: {e}", exc_info=True)
    finally:
        db.close()


def _parse_wb_dt(val) -> Optional[datetime]:
    """解析 WB 日期时间"""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.strptime(str(val)[:19], "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        try:
            return datetime.strptime(str(val)[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None
