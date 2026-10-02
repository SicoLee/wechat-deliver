"""add order audit logs

Revision ID: 20261002_02
Revises: 20261002_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261002_02"
down_revision = "20261002_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("actor_openid", sa.String(80)),
        sa.Column("from_status", sa.String(40)),
        sa.Column("to_status", sa.String(40)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_order_audit_logs_order_id", "order_audit_logs", ["order_id"])


def downgrade() -> None:
    op.drop_table("order_audit_logs")
