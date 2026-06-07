"""Wildberries API 客户端

对接 WB 卖家 API：
  - 商品管理: /api/v3/cards/catalog, /api/v3/cards/cursor/list
  - 订单管理: /api/v3/orders, /api/v3/orders/new
  - 销售报告: /api/v3/supplier/reportDetailByPeriod
  - 库存管理: /api/v3/stocks

API 文档: https://openapi.wildberries.ru/
"""
import os
import time
import logging
from typing import Optional, Dict, List, Any

import requests

logger = logging.getLogger(__name__)

WB_BASE_URL = "https://suppliers-api.wildberries.ru"


class WBClient:
    """Wildberries API 客户端"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": api_key,
            "Content-Type": "application/json",
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """统一请求方法"""
        url = f"{WB_BASE_URL}{endpoint}"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                if method == "GET":
                    resp = self.session.get(url, params=kwargs.get("params"), timeout=30)
                else:
                    resp = self.session.post(url, json=kwargs.get("json"), timeout=30)

                if resp.status_code == 429:
                    wait = min(2 ** (attempt + 1), 30)
                    logger.warning(f"WB rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"WB API request failed: {e}")

        raise RuntimeError("WB API request failed after retries")

    def health_check(self) -> bool:
        """API 连通性检查"""
        try:
            self.get_cards_catalog(limit=1)
            return True
        except Exception:
            return False

    # ==================== 商品管理 ====================

    def get_cards_catalog(self, limit: int = 100) -> Dict:
        """获取商品列表（V3）"""
        return self._request("POST", "/api/v3/cards/catalog", json={
            "sort": {"cursor": {"limit": limit}},
        })

    def get_cards_cursor(self, limit: int = 100, cursor: str = "") -> Dict:
        """获取商品列表（游标翻页）"""
        body = {
            "sort": {"cursor": {"limit": limit}},
        }
        if cursor:
            body["sort"]["cursor"]["cursor"] = cursor
        return self._request("POST", "/api/v3/cards/cursor/list", json=body)

    # ==================== 订单管理 ====================

    def get_new_orders(self, date_from: str) -> Dict:
        """获取新订单"""
        return self._request("GET", "/api/v3/orders/new", params={
            "dateFrom": date_from,
        })

    def get_orders(self, date_from: str, date_to: str) -> Dict:
        """获取订单列表"""
        return self._request("GET", "/api/v3/orders", params={
            "dateFrom": date_from,
            "dateTo": date_to,
        })

    # ==================== 销售报告 ====================

    def get_sales_report(self, date_from: str, date_to: str, limit: int = 10000) -> Dict:
        """获取销售报告"""
        return self._request("GET", "/api/v3/supplier/reportDetailByPeriod", params={
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": limit,
        })

    # ==================== 库存 ====================

    def get_stocks(self) -> Dict:
        """获取库存信息"""
        return self._request("GET", "/api/v3/stocks")

    # ==================== 营收 ====================

    def get_income(self, date_from: str) -> Dict:
        """获取收入数据"""
        return self._request("GET", "/api/v3/supplier/incomes", params={
            "dateFrom": date_from,
        })

    def get_sales(self, date_from: str, date_to: str) -> Dict:
        """获取销售数据"""
        return self._request("GET", "/api/v3/supplier/sales", params={
            "dateFrom": date_from,
            "dateTo": date_to,
        })
