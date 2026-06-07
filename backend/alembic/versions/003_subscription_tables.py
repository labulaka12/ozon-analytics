"""订阅计费相关表 — Plan, Subscription, PaymentHistory, Usage, AuditLog

Revision ID: 003
Revises: 002
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # plans 表
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True, comment="套餐标识"),
        sa.Column("display_name", sa.String(100), nullable=False, comment="显示名称"),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0", comment="月费(美分)"),
        sa.Column("currency", sa.String(10), server_default="usd", comment="货币"),
        sa.Column("stripe_price_id", sa.String(100), comment="Stripe Price ID"),
        sa.Column("limits", sa.JSON(), nullable=False, comment="套餐限额 JSON"),
        sa.Column("is_active", sa.Boolean(), server_default="1", comment="是否可订阅"),
        sa.Column("sort_order", sa.Integer(), server_default="0", comment="排序权重"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_plans_name", "plans", ["name"])

    # subscriptions 表
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("plan_id", sa.Integer(), nullable=False, comment="套餐ID"),
        sa.Column("status", sa.String(20), nullable=False, server_default="trialing", comment="状态"),
        sa.Column("stripe_subscription_id", sa.String(100), comment="Stripe Subscription ID"),
        sa.Column("stripe_customer_id", sa.String(100), comment="Stripe Customer ID"),
        sa.Column("trial_start", sa.DateTime(), comment="试用开始时间"),
        sa.Column("trial_end", sa.DateTime(), comment="试用结束时间"),
        sa.Column("current_period_start", sa.DateTime(), comment="当前计费周期开始"),
        sa.Column("current_period_end", sa.DateTime(), comment="当前计费周期结束"),
        sa.Column("cancelled_at", sa.DateTime(), comment="取消时间"),
        sa.Column("expired_at", sa.DateTime(), comment="过期时间"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_sub_user", "subscriptions", ["user_id"])
    op.create_index("idx_sub_status", "subscriptions", ["status"])
    op.create_index("idx_sub_stripe", "subscriptions", ["stripe_subscription_id"])

    # payment_histories 表
    op.create_table(
        "payment_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("subscription_id", sa.Integer(), comment="订阅ID"),
        sa.Column("stripe_invoice_id", sa.String(100), comment="Stripe Invoice ID"),
        sa.Column("amount_cents", sa.Integer(), nullable=False, comment="金额(美分)"),
        sa.Column("currency", sa.String(10), server_default="usd", comment="货币"),
        sa.Column("status", sa.String(20), nullable=False, comment="支付状态"),
        sa.Column("description", sa.String(500), comment="描述"),
        sa.Column("paid_at", sa.DateTime(), comment="支付时间"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_payment_user", "payment_histories", ["user_id"])
    op.create_index("idx_payment_stripe", "payment_histories", ["stripe_invoice_id"])

    # usages 表
    op.create_table(
        "usages",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("resource", sa.String(50), nullable=False, comment="资源类型"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0", comment="使用量"),
        sa.Column("period", sa.String(7), nullable=False, comment="统计周期"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("user_id", "resource", "period", name="uq_user_resource_period"),
    )
    op.create_index("idx_usage_user_period", "usages", ["user_id", "period"])

    # audit_logs 表
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), comment="操作用户ID"),
        sa.Column("action", sa.String(100), nullable=False, comment="操作类型"),
        sa.Column("target_type", sa.String(50), comment="目标类型"),
        sa.Column("target_id", sa.String(100), comment="目标ID"),
        sa.Column("detail", sa.JSON(), comment="操作详情 JSON"),
        sa.Column("ip_address", sa.String(50), comment="IP 地址"),
        sa.Column("user_agent", sa.String(500), comment="User-Agent"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_user", "audit_logs", ["user_id"])
    op.create_index("idx_audit_action", "audit_logs", ["action"])
    op.create_index("idx_audit_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("usages")
    op.drop_table("payment_histories")
    op.drop_table("subscriptions")
    op.drop_table("plans")
