"""Initial migration — create all tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-06-05

完整表结构：
  - users (系统用户)
  - stores (Ozon 店铺)
  - products (商品信息)
  - analytics_daily (每日分析数据)
  - sync_logs (同步日志)
  - orders (订单数据 FBO+FBS)
  - finance_transactions (财务交易明细)
  - realization_reports (销售实现报告)
  - product_costs (商品采购成本)
  - manual_expenses (手动补录费用)
  - exchange_rates (汇率配置)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== users ====================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ==================== stores ====================
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("client_id", sa.String(50), nullable=False),
        sa.Column("api_key", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("last_sync_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== products ====================
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.String(100), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.Integer()),
        sa.Column("name", sa.String(500)),
        sa.Column("category", sa.String(200)),
        sa.Column("price", sa.Float()),
        sa.Column("old_price", sa.Float()),
        sa.Column("currency", sa.String(10), server_default="RUB"),
        sa.Column("barcode", sa.String(50)),
        sa.Column("images", sa.Text()),
        sa.Column("status", sa.String(50)),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("cost_price", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", "product_id", name="uq_user_store_product"),
    )
    op.create_index("idx_user_store_product", "products", ["user_id", "store_id", "product_id"])

    # ==================== analytics_daily ====================
    op.create_table(
        "analytics_daily",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.String(100)),
        sa.Column("sku", sa.Integer()),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("impressions_search", sa.Integer(), server_default=sa.text("0")),
        sa.Column("views_pdp", sa.Integer(), server_default=sa.text("0")),
        sa.Column("views_total", sa.Integer(), server_default=sa.text("0")),
        sa.Column("sessions", sa.Integer(), server_default=sa.text("0")),
        sa.Column("add_to_cart", sa.Integer(), server_default=sa.text("0")),
        sa.Column("add_to_cart_search", sa.Integer(), server_default=sa.text("0")),
        sa.Column("add_to_cart_pdp", sa.Integer(), server_default=sa.text("0")),
        sa.Column("conversion_to_cart", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("conversion_search_to_cart", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("conversion_pdp_to_cart", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("ordered_units", sa.Integer(), server_default=sa.text("0")),
        sa.Column("delivered_units", sa.Integer(), server_default=sa.text("0")),
        sa.Column("revenue", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("orders", sa.Integer(), server_default=sa.text("0")),
        sa.Column("returns_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("cancellations", sa.Integer(), server_default=sa.text("0")),
        sa.Column("position_avg", sa.Float()),
        sa.Column("ctr", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("order_conversion", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", "product_id", "date", name="uq_user_analytics_daily"),
    )
    op.create_index("idx_analytics_daily_date", "analytics_daily", ["date"])
    op.create_index("idx_user_analytics_store_product", "analytics_daily", ["user_id", "store_id", "product_id"])

    # ==================== sync_logs ====================
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("sync_type", sa.String(50)),
        sa.Column("status", sa.String(20)),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== orders ====================
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("posting_number", sa.String(100), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.String(100)),
        sa.Column("sku", sa.Integer()),
        sa.Column("product_name", sa.String(500)),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("1")),
        sa.Column("price", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("total_price", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("order_created_at", sa.DateTime()),
        sa.Column("shipped_at", sa.DateTime()),
        sa.Column("delivered_at", sa.DateTime()),
        sa.Column("cancelled_at", sa.DateTime()),
        sa.Column("commission", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("payout", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", "posting_number", "product_id", name="uq_user_order_posting_product"),
    )
    op.create_index("idx_orders_user_store", "orders", ["user_id", "store_id"])
    op.create_index("idx_orders_status", "orders", ["status"])
    op.create_index("idx_orders_date", "orders", ["order_created_at"])

    # ==================== finance_transactions ====================
    op.create_table(
        "finance_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.String(100), nullable=False),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="RUB"),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("posting_number", sa.String(100)),
        sa.Column("product_id", sa.Integer()),
        sa.Column("description", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", "transaction_id", name="uq_user_finance_transaction"),
    )
    op.create_index("idx_finance_user_store", "finance_transactions", ["user_id", "store_id"])
    op.create_index("idx_finance_date", "finance_transactions", ["transaction_date"])
    op.create_index("idx_finance_type", "finance_transactions", ["transaction_type"])

    # ==================== realization_reports ====================
    op.create_table(
        "realization_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        sa.Column("period_to", sa.Date(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("offer_id", sa.String(100)),
        sa.Column("sku", sa.Integer()),
        sa.Column("product_name", sa.String(500)),
        sa.Column("sold_units", sa.Integer(), server_default=sa.text("0")),
        sa.Column("revenue", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("commission", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("logistics_cost", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("marketing_cost", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("penalty", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("other_cost", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("payout", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", "period_from", "period_to", "product_id", name="uq_user_realization_product_period"),
    )
    op.create_index("idx_realization_user_store", "realization_reports", ["user_id", "store_id"])

    # ==================== product_costs ====================
    op.create_table(
        "product_costs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("cost_price", sa.Float(), server_default=sa.text("0.0")),
        sa.Column("cost_updated_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "store_id", "product_id", name="uq_user_product_cost"),
    )

    # ==================== manual_expenses ====================
    op.create_table(
        "manual_expenses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer()),
        sa.Column("expense_type", sa.String(50), nullable=False),
        sa.Column("amount_cny", sa.Float(), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("expense_date", sa.Date()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== exchange_rates ====================
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False, server_default=sa.text("12.0")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exchange_rates")
    op.drop_table("manual_expenses")
    op.drop_table("product_costs")
    op.drop_table("realization_reports")
    op.drop_table("finance_transactions")
    op.drop_table("orders")
    op.drop_table("sync_logs")
    op.drop_table("analytics_daily")
    op.drop_table("products")
    op.drop_table("stores")
    op.drop_table("users")
