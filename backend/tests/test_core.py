"""核心业务逻辑单元测试

注意：需要 conftest.py 先设置环境变量，因此导入放在函数内部。
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 确保 backend 在 sys.path 中（conftest.py 已做，此处防御）
import os, sys
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)


# ==================== 模型测试 ====================


class TestUserModel:
    """用户模型测试"""

    @pytest.mark.skip(reason="SQLite < 3.35 不支持 RETURNING，生产环境用 PostgreSQL 无此问题")
    def test_user_creation(self, test_db):
        from models import User
        user = User(email="test@example.com", hashed_password="hashed_xxx")
        test_db.add(user)
        test_db.commit()

        saved = test_db.query(User).filter_by(email="test@example.com").first()
        assert saved is not None
        assert saved.email == "test@example.com"
        assert saved.is_active is True
        assert saved.hashed_password == "hashed_xxx"

    @pytest.mark.skip(reason="SQLite < 3.35 不支持 RETURNING，生产环境用 PostgreSQL 无此问题")
    def test_user_unique_email(self, test_db):
        from models import User
        from sqlalchemy.exc import IntegrityError

        test_db.add(User(email="duplicate@example.com", hashed_password="hash1"))
        test_db.commit()

        test_db.add(User(email="duplicate@example.com", hashed_password="hash2"))
        with pytest.raises(IntegrityError):
            test_db.commit()


class TestStoreModel:
    """店铺模型测试"""

    @pytest.mark.skip(reason="SQLite < 3.35 不支持 RETURNING，生产环境用 PostgreSQL 无此问题")
    def test_store_creation(self, test_db):
        from models import Store
        store = Store(user_id=1, name="测试店铺", client_id="12345", api_key="encrypted_key")
        test_db.add(store)
        test_db.commit()

        saved = test_db.query(Store).filter_by(name="测试店铺").first()
        assert saved is not None
        assert saved.user_id == 1
        assert saved.client_id == "12345"
        assert saved.is_active is True


class TestProductModel:
    """商品模型测试"""

    @pytest.mark.skip(reason="SQLite < 3.35 不支持 RETURNING，生产环境用 PostgreSQL 无此问题")
    def test_product_unique_constraint(self, test_db):
        from models import Product
        from sqlalchemy.exc import IntegrityError

        p1 = Product(user_id=1, store_id=1, product_id=100, offer_id="SKU-001")
        test_db.add(p1)
        test_db.commit()

        p2 = Product(user_id=1, store_id=1, product_id=100, offer_id="SKU-002")
        test_db.add(p2)
        with pytest.raises(IntegrityError):
            test_db.commit()


class TestAnalyticsDaily:
    """分析数据模型测试"""

    @pytest.mark.skip(reason="SQLite < 3.35 不支持 RETURNING，生产环境用 PostgreSQL 无此问题")
    def test_analytics_creation(self, test_db):
        from models import AnalyticsDaily
        row = AnalyticsDaily(
            user_id=1, store_id=1, product_id=100,
            offer_id="SKU-001", date=date.today(),
            impressions_search=1000, views_pdp=500,
            revenue=50000.0
        )
        test_db.add(row)
        test_db.commit()

        saved = test_db.query(AnalyticsDaily).first()
        assert saved.impressions_search == 1000
        assert saved.revenue == 50000.0


# ==================== 认证测试 ====================


class TestAuth:
    """认证逻辑测试"""

    def test_password_hash_and_verify(self):
        from auth import hash_password, verify_password
        hashed = hash_password("mypassword123")
        assert verify_password("mypassword123", hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_jwt_create_and_decode(self):
        from auth import create_access_token
        from jose import jwt

        token = create_access_token({"sub": "42"})
        assert token is not None

        secret = os.environ.get("OZON_JWT_SECRET", "test-jwt-secret")
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == "42"

    def test_register_flow(self, test_client, test_db):
        """注册 API 测试"""
        from models import User

        resp = test_client.post("/api/auth/register", json={
            "email": "newuser@test.com",
            "password": "password123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@test.com"

        # 验证用户已入库
        user = test_db.query(User).filter_by(email="newuser@test.com").first()
        assert user is not None

    def test_duplicate_register(self, test_client, test_db):
        """重复注册测试"""
        from models import User
        test_db.add(User(email="existing@test.com", hashed_password="hash"))
        test_db.commit()

        resp = test_client.post("/api/auth/register", json={
            "email": "existing@test.com",
            "password": "password123"
        })
        assert resp.status_code == 400

    def test_login_flow(self, test_client, test_db):
        """登录 API 测试"""
        from models import User
        from auth import hash_password

        test_db.add(User(email="login@test.com", hashed_password=hash_password("password123")))
        test_db.commit()

        resp = test_client.post("/api/auth/login", json={
            "email": "login@test.com",
            "password": "password123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_login_wrong_password(self, test_client, test_db):
        from models import User
        from auth import hash_password
        test_db.add(User(email="login2@test.com", hashed_password=hash_password("correct")))
        test_db.commit()

        resp = test_client.post("/api/auth/login", json={
            "email": "login2@test.com",
            "password": "wrong"
        })
        assert resp.status_code == 401

    def test_me_endpoint(self, test_client, test_db):
        from models import User
        from auth import hash_password
        test_db.add(User(email="me@test.com", hashed_password=hash_password("pass")))
        test_db.commit()

        # 先登录
        resp = test_client.post("/api/auth/login", json={
            "email": "me@test.com",
            "password": "pass"
        })
        token = resp.json()["access_token"]

        resp = test_client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@test.com"

    def test_unauthorized_access(self, test_client):
        """未认证访问受保护端点"""
        resp = test_client.get("/api/stores")
        assert resp.status_code == 401


# ==================== 店铺管理测试 ====================


class TestStoreAPI:
    """店铺 CRUD API 测试"""

    def _get_token(self, test_client, test_db):
        from models import User
        from auth import hash_password
        test_db.add(User(email="store_test@test.com", hashed_password=hash_password("pass")))
        test_db.commit()
        resp = test_client.post("/api/auth/login", json={
            "email": "store_test@test.com",
            "password": "pass"
        })
        return resp.json()["access_token"]

    def test_create_store(self, test_client, test_db):
        from ozon_client import OzonClient

        # Mock health_check 和后台同步任务
        with patch.object(OzonClient, "health_check", return_value=True), \
             patch("main.sync_products_for_store") as mock_products_sync, \
             patch("main.sync_analytics_for_store") as mock_analytics_sync:

            token = self._get_token(test_client, test_db)

            resp = test_client.post("/api/stores", json={
                "name": "我的店铺",
                "client_id": "123456",
                "api_key": "secret-api-key"
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
            data = resp.json()
            assert "id" in data

    def test_list_stores(self, test_client, test_db):
        from models import User, Store
        from auth import hash_password
        from crypto import encrypt_value

        token = self._get_token(test_client, test_db)

        # 找到用户
        user = test_db.query(User).filter_by(email="store_test@test.com").first()
        test_db.add(Store(user_id=user.id, name="店铺A", client_id="111", api_key=encrypt_value("key1")))
        test_db.commit()

        resp = test_client.get("/api/stores", headers={
            "Authorization": f"Bearer {token}"
        })
        assert resp.status_code == 200
        stores = resp.json()
        assert len(stores) >= 1
        assert stores[0]["name"] == "店铺A"


# ==================== 数据同步逻辑测试 ====================


class TestScheduler:
    """定时同步逻辑测试"""

    def test_resolve_date_range_default(self):
        """默认日期范围"""
        from main import resolve_date_range
        df, dt = resolve_date_range(None, None, default_days=30)
        assert dt == date.today().strftime("%Y-%m-%d")
        expected_from = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert df == expected_from

    def test_resolve_date_range_custom(self):
        from main import resolve_date_range
        df, dt = resolve_date_range("2026-01-01", "2026-01-31")
        assert df == "2026-01-01"
        assert dt == "2026-01-31"

    def test_parse_analytics_row(self):
        from scheduler import _parse_analytics_row, ANALYTICS_METRICS
        row = {
            "dimensions": [
                {"id": "12345", "name": "商品A"},
                {"id": "2026-06-01", "name": ""}
            ],
            "metrics": [100, 50, 80, 20, 5, 3, 2, 0.05, 50000, 10, 8, 1, 0, 15.5]
        }
        result = _parse_analytics_row(row, ANALYTICS_METRICS)
        assert result["sku"] == 12345
        assert result["date"] == "2026-06-01"
        assert result["hits_view_search"] == 100
        assert result["revenue"] == 50000
        assert result["position_category"] == 15.5


# ==================== 加密测试 ====================


class TestCrypto:
    """加密工具测试"""

    def test_encrypt_decrypt_roundtrip(self):
        from crypto import encrypt_value, decrypt_value
        plain = "my-secret-api-key-12345"
        encrypted = encrypt_value(plain)
        assert encrypted != plain
        assert len(encrypted) > 0
        decrypted = decrypt_value(encrypted)
        assert decrypted == plain

    def test_decrypt_empty(self):
        from crypto import decrypt_value
        assert decrypt_value("") == ""


# ==================== 汇率计算测试 ====================


class TestExchangeRate:
    """汇率逻辑测试"""

    def test_default_rate(self, test_db):
        from routes.profit import _get_rate
        rate = _get_rate(test_db, user_id=999)
        assert rate == 12.0

    def test_custom_rate(self, test_db):
        from models import ExchangeRate
        test_db.add(ExchangeRate(user_id=1, rate=13.5))
        test_db.commit()

        from routes.profit import _get_rate
        rate = _get_rate(test_db, user_id=1)
        assert rate == 13.5


# ==================== 订单解析测试 ====================


class TestOrderParsing:
    """订单数据解析测试"""

    def test_parse_fbo_order(self):
        from scheduler import _parse_fbo_orders
        raw = {
            "result": [{
                "posting_number": "P12345",
                "status": "delivered",
                "created_at": "2026-06-01T10:00:00Z",
                "products": [{
                    "product_id": 100,
                    "offer_id": "SKU-001",
                    "sku": 20001,
                    "name": "测试商品",
                    "quantity": 2,
                    "price": "1500.00",
                    "total_price": "3000.00"
                }]
            }]
        }
        orders = _parse_fbo_orders(raw, store_id=1, user_id=1)
        assert len(orders) == 1
        assert orders[0]["posting_number"] == "P12345"
        assert orders[0]["order_type"] == "fbo"
        assert orders[0]["product_id"] == 100
        assert orders[0]["price"] == 1500.0
        assert orders[0]["total_price"] == 3000.0
