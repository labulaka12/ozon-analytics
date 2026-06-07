"""User 表扩展字段 — email_verified, role, stripe_customer_id, 验证/重置令牌

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 SaaS 扩展字段
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default="0", comment="邮箱是否已验证"))
    op.add_column("users", sa.Column("role", sa.String(20), server_default="user", comment="角色: user/admin"))
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(100), comment="Stripe 客户 ID"))
    op.add_column("users", sa.Column("display_name", sa.String(100), comment="显示名称"))
    op.add_column("users", sa.Column("email_verify_token", sa.String(200), comment="邮箱验证令牌"))
    op.add_column("users", sa.Column("email_verify_token_expires", sa.DateTime(), comment="验证令牌过期时间"))
    op.add_column("users", sa.Column("password_reset_token", sa.String(200), comment="密码重置令牌"))
    op.add_column("users", sa.Column("password_reset_token_expires", sa.DateTime(), comment="重置令牌过期时间"))

    # 为已有用户设置默认值
    op.execute("UPDATE users SET email_verified = 1, role = 'user' WHERE email_verified IS NULL")


def downgrade() -> None:
    op.drop_column("users", "password_reset_token_expires")
    op.drop_column("users", "password_reset_token")
    op.drop_column("users", "email_verify_token_expires")
    op.drop_column("users", "email_verify_token")
    op.drop_column("users", "display_name")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "role")
    op.drop_column("users", "email_verified")
