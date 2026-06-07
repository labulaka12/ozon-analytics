"""金额字段 Float→Numeric 修复（精度保障）

Revision ID: 004
Revises: 003
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

# 需要转换的金额字段列表（表名, 列名）
MONEY_COLUMNS = [
    ("products", "price"),
    ("products", "old_price"),
    ("products", "cost_price"),
    ("analytics_daily", "conversion_to_cart"),
    ("analytics_daily", "conversion_search_to_cart"),
    ("analytics_daily", "conversion_pdp_to_cart"),
    ("analytics_daily", "revenue"),
    ("analytics_daily", "ctr"),
    ("analytics_daily", "order_conversion"),
    ("analytics_daily", "position_avg"),
    ("orders", "price"),
    ("orders", "total_price"),
    ("orders", "commission"),
    ("orders", "payout"),
    ("finance_transactions", "amount"),
    ("realization_reports", "revenue"),
    ("realization_reports", "commission"),
    ("realization_reports", "logistics_cost"),
    ("realization_reports", "marketing_cost"),
    ("realization_reports", "penalty"),
    ("realization_reports", "other_cost"),
    ("realization_reports", "payout"),
    ("product_costs", "cost_price"),
    ("manual_expenses", "amount_cny"),
    ("exchange_rates", "rate"),
    ("alert_rules", "threshold"),
]


def upgrade() -> None:
    # 使用 batch_alter_table 兼容 SQLite
    for table, column in MONEY_COLUMNS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                type_=sa.Numeric(precision=12, scale=2),
                existing_type=sa.Float(),
            )


def downgrade() -> None:
    for table, column in MONEY_COLUMNS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                column,
                type_=sa.Float(),
                existing_type=sa.Numeric(precision=12, scale=2),
            )
