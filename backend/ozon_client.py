"""Ozon Seller API 客户端"""
import os
import requests
import time
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

BASE_URL = "https://api-seller.ozon.ru"


class OzonClient:
    """Ozon Seller API 封装"""

    def __init__(self, client_id: str, api_key: str, proxy_url: Optional[str] = None):
        self.client_id = client_id
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        })

        # 代理配置：优先使用传入参数，其次读环境变量，默认直连
        if proxy_url:
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
        else:
            _env_proxy = os.environ.get("OZON_PROXY_URL", "")
            if _env_proxy:
                self.session.proxies = {"http": _env_proxy, "https": _env_proxy}
            else:
                # 关键：禁用系统代理，避免 requests 自动继承 http_proxy 环境变量
                self.session.proxies = {"http": None, "https": None}

        # 不信任系统代理设置（防止意外走系统代理导致连接失败）
        self.session.trust_env = False

    def _request(self, method: str, endpoint: str, body: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """统一请求方法（含自动重试）

        429 限流单独处理（不消耗重试次数），最多重试 10 次；
        其他错误最多重试 3 次。
        """
        url = f"{BASE_URL}{endpoint}"
        max_retries = 3
        rate_limit_attempts = 0
        max_rate_limit_retries = 10

        for attempt in range(max_retries):
            try:
                if method == "GET":
                    resp = self.session.get(url, params=params, timeout=30)
                else:
                    resp = self.session.post(url, json=body or {}, timeout=30)

                # 429 频率限制：单独重试，不消耗 attempt
                while resp.status_code == 429 and rate_limit_attempts < max_rate_limit_retries:
                    rate_limit_attempts += 1
                    wait = min(2 ** rate_limit_attempts, 60)
                    logger.warning(f"Rate limited ({rate_limit_attempts}/{max_rate_limit_retries}), retrying in {wait}s...")
                    time.sleep(wait)
                    if method == "GET":
                        resp = self.session.get(url, params=params, timeout=30)
                    else:
                        resp = self.session.post(url, json=body or {}, timeout=30)

                # 429 仍然超限 → 抛出异常
                if resp.status_code == 429:
                    raise RuntimeError(f"Ozon API rate limit exceeded after {max_rate_limit_retries} retries")

                # 处理业务错误（Ozon API 返回 200 但 body 中含错误码）
                if resp.status_code == 200:
                    data = resp.json()
                    # Ozon 有些端点在 200 里返回 code != 0 表示错误
                    if "code" in data and data["code"] != 0:
                        logger.warning(f"Ozon API business error on {endpoint}: code={data['code']}, message={data.get('message', '')}")
                    return data

                # 非 2xx 错误：记录详细信息并抛出可识别的异常
                if resp.status_code >= 400:
                    error_detail = resp.text[:500] if resp.text else ""
                    logger.error(f"Ozon API {resp.status_code} on {endpoint}: {error_detail}")

                    # 认证失败不重试，直接抛出
                    if "Invalid Api-Key" in error_detail or '"code":5' in error_detail:
                        raise RuntimeError(f"Invalid Api-Key: authentication failed for Client-Id {self.client_id}")

                    # 400 错误记录请求体便于调试
                    if resp.status_code == 400:
                        logger.error(f"400 Bad Request body: {body}")

                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                # 连接/代理错误不重试，直接抛出
                if isinstance(e, (requests.exceptions.ProxyError, requests.exceptions.ConnectionError)):
                    raise RuntimeError(f"Network connection failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"Ozon API request failed after {max_retries} retries")

        # 防御：循环不应正常结束；若结束则抛出异常
        raise RuntimeError(f"Ozon API request failed unexpectedly")

    # ==================== 商品管理 ====================

    def get_product_list(self, limit: int = 100, last_id: str = "") -> Dict:
        """获取商品列表"""
        return self._request("POST", "/v3/product/list", {
            "filter": {"visibility": "ALL"},
            "last_id": last_id,
            "limit": limit
        })

    def get_all_products(self) -> List[Dict]:
        """获取全部商品列表（自动翻页）"""
        items = []
        last_id = ""
        while True:
            result = self.get_product_list(limit=100, last_id=last_id)
            batch = result.get("result", {}).get("items", [])
            if not batch:
                break
            items.extend(batch)
            last_id = result.get("result", {}).get("last_id", "")
            if not last_id:
                break
            time.sleep(0.3)  # 限速
        return items

    def get_product_info_list(self, product_ids: List[int]) -> Dict:
        """批量获取商品详细信息 — 返回 {"items": [...]}"""
        return self._request("POST", "/v3/product/info/list", {
            "product_id": product_ids
        })

    def get_product_prices(self, product_ids: List[int], limit: int = 1000) -> Dict:
        """批量获取商品价格"""
        return self._request("POST", "/v5/product/info/prices", {
            "filter": {"product_id": product_ids, "visibility": "ALL"},
            "limit": limit
        })

    def get_product_stocks(self, product_ids: List[int]) -> Dict:
        """批量获取库存"""
        return self._request("POST", "/v3/product/info/stocks", {
            "filter": {"product_id": product_ids, "visibility": "ALL"},
            "last_id": "",
            "limit": 1000
        })

    # ==================== 分析数据 ====================

    def get_analytics_data(
        self,
        date_from: str,
        date_to: str,
        metrics: List[str],
        dimensions: List[str],
        limit: int = 1000,
        offset: int = 0,
        filters: Optional[List[Dict]] = None,
    ) -> Dict:
        """获取分析数据（核心接口）

        Args:
            date_from/to: 日期范围 "YYYY-MM-DD"
            metrics: 指标列表
            dimensions: 维度 ["sku", "day"] 或 ["sku"]
            limit: 每页数量，最大1000
            offset: 偏移
            filters: 筛选条件（可选，为空时不传）

        Note:
            Ozon API 文档参考: https://docs.ozon.ru/api/seller/#operation/AnalyticsAPI_GetData
            - dimension 字段名是单数 "dimension"
            - sort/filters 为空时不要传空数组，直接省略
            - Ozon 限制最多 14 个 metrics
        """
        body = {
            "date_from": date_from,
            "date_to": date_to,
            "metrics": metrics,
            "dimension": dimensions,
            "limit": limit,
        }
        # 仅在有值时添加可选字段（空值会导致 400 Bad Request）
        if offset > 0:
            body["offset"] = offset
        if filters:
            body["filters"] = filters
        return self._request("POST", "/v1/analytics/data", body)

    def get_all_analytics_data(
        self,
        date_from: str,
        date_to: str,
        metrics: List[str],
        dimensions: List[str],
    ) -> List[Dict]:
        """获取全量分析数据（自动翻页）"""
        all_rows = []
        offset = 0
        while True:
            result = self.get_analytics_data(date_from, date_to, metrics, dimensions, offset=offset)
            if result is None:
                logger.error(f"get_analytics_data returned None for {date_from}~{date_to}, offset={offset}")
                raise RuntimeError("Ozon API returned empty response")
            data = result.get("result", {}).get("data", []) if isinstance(result, dict) else []
            if not data:
                break
            all_rows.extend(data)
            if len(data) < 1000:
                break
            offset += 1000
            time.sleep(1.5)  # 翻页限速（避免429）
        return all_rows

    # ==================== 订单数据 ====================

    def get_fbo_orders(self, since: str, to: str, status: str = "", limit: int = 100) -> Dict:
        """获取FBO订单列表"""
        return self._request("POST", "/v2/posting/fbo/list", {
            "dir": "ASC",
            "filter": {"since": since, "status": status, "to": to},
            "limit": limit,
            "offset": 0,
            "with": {"analytics_data": True, "financial_data": True}
        })

    def get_fbs_orders(self, since: str, to: str, status: str = "", limit: int = 100) -> Dict:
        """获取FBS订单列表"""
        return self._request("POST", "/v3/posting/fbs/list", {
            "dir": "ASC",
            "filter": {"since": since, "status": status, "to": to},
            "limit": limit,
            "offset": 0,
            "with": {"analytics_data": True, "financial_data": True}
        })

    # ==================== 财务数据 ====================

    def get_finance_transactions(self, date_from: str, date_to: str, page: int = 1, page_size: int = 100) -> Dict:
        """获取财务交易列表"""
        return self._request("POST", "/v3/finance/transaction/list", {
            "filter": {
                "date": {"from": f"{date_from}T00:00:00.000Z", "to": f"{date_to}T23:59:59.000Z"},
                "transaction_type": "ALL"
            },
            "page": page,
            "page_size": page_size
        })

    def get_realization(self, date_from: str, date_to: str, page: int = 1, page_size: int = 100) -> Dict:
        """获取销售实现报告"""
        return self._request("POST", "/v2/finance/realization", {
            "date": {"from": date_from, "to": date_to},
            "page": page,
            "page_size": page_size
        })

    # ==================== 配额 & 健康检查 ====================

    def get_limits(self) -> Dict:
        """查询商品上传配额"""
        return self._request("POST", "/v4/product/info/limit", {})

    def health_check(self) -> bool:
        """API连通性检查"""
        try:
            self._request("POST", "/v4/product/info/limit", {})
            return True
        except Exception:
            return False
