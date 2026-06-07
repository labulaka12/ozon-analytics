"""关键索引和约束补充

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # subscriptions 的 user_id 复合索引（活跃订阅查询优化）
    op.create_index("idx_sub_user_status", "subscriptions", ["user_id", "status"])

    # plans 的 is_active 索引（套餐列表查询优化）
    op.create_index("idx_plans_active", "plans", ["is_active"])

    # payment_histories 的 user_id + status 索引
    op.create_index("idx_payment_user_status", "payment_histories", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("idx_payment_user_status", "payment_histories")
    op.drop_index("idx_plans_active", "plans")
    op.drop_index("idx_sub_user_status", "subscriptions")
