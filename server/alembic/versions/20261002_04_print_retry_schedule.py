"""schedule retriable receipt printing

Revision ID: 20261002_04
Revises: 20261002_03
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa


revision = "20261002_04"
down_revision = "20261002_03"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("order_events", sa.Column("next_attempt_at", sa.DateTime(), nullable=True))
    op.create_index("ix_order_events_pending_retry", "order_events", ["status", "next_attempt_at"], unique=False)


def downgrade():
    op.drop_index("ix_order_events_pending_retry", table_name="order_events")
    op.drop_column("order_events", "next_attempt_at")
