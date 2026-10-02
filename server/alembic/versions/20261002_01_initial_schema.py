"""initial order schema

Revision ID: 20261002_01
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20261002_01"
down_revision = None
branch_labels = None
depends_on = None

order_status = sa.Enum("PENDING_PAYMENT", "PAID", "MAKING", "READY_FOR_DELIVERY", "COMPLETED", name="orderstatus")
payment_status = sa.Enum("UNPAID", "PAID", name="paymentstatus")
print_status = sa.Enum("NOT_PRINTED", "SUCCESS", "FAILED", name="printstatus")
event_status = sa.Enum("PENDING", "SUCCEEDED", "FAILED", name="eventstatus")


def upgrade() -> None:
    op.create_table("products", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(80), nullable=False, unique=True), sa.Column("price", sa.Numeric(10, 2), nullable=False), sa.Column("image", sa.String(255)), sa.Column("category", sa.String(40), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False))
    op.create_table("admins", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("openid", sa.String(80), nullable=False, unique=True), sa.Column("phone", sa.String(20), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_no", sa.String(32), nullable=False, unique=True), sa.Column("openid", sa.String(80), nullable=False), sa.Column("goods_amount", sa.Numeric(10, 2), nullable=False), sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=False), sa.Column("total_amount", sa.Numeric(10, 2), nullable=False), sa.Column("address", sa.Text(), nullable=False), sa.Column("latitude", sa.Float(), nullable=False), sa.Column("longitude", sa.Float(), nullable=False), sa.Column("delivery_distance_km", sa.Float(), nullable=False), sa.Column("phone", sa.String(20), nullable=False), sa.Column("remark", sa.Text()), sa.Column("status", order_status, nullable=False), sa.Column("payment_status", payment_status, nullable=False), sa.Column("payment_provider", sa.String(30)), sa.Column("payment_transaction_id", sa.String(80), unique=True), sa.Column("print_status", print_status, nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("paid_at", sa.DateTime()))
    op.create_index("ix_orders_order_no", "orders", ["order_no"])
    op.create_index("ix_orders_openid", "orders", ["openid"])
    op.create_table("order_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False), sa.Column("product_id", sa.Integer(), nullable=False), sa.Column("product_name", sa.String(80), nullable=False), sa.Column("unit_price", sa.Numeric(10, 2), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False))
    op.create_table("order_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False), sa.Column("event_type", sa.String(40), nullable=False), sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True), sa.Column("status", event_status, nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("last_error", sa.Text()), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("processed_at", sa.DateTime()))
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"])


def downgrade() -> None:
    op.drop_table("order_events")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("admins")
    op.drop_table("products")
    bind = op.get_bind()
    for enum in (event_status, print_status, payment_status, order_status):
        enum.drop(bind, checkfirst=True)
