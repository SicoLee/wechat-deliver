"""add client retry key to orders

Revision ID: 20261002_03
Revises: 20261002_02
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa


revision = "20261002_03"
down_revision = "20261002_02"
branch_labels = None
depends_on = None


def upgrade():
    # batch mode also works on SQLite, which needs a table rebuild for constraints.
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("client_request_id", sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint("uq_orders_openid_client_request_id", ["openid", "client_request_id"])


def downgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("uq_orders_openid_client_request_id", type_="unique")
        batch_op.drop_column("client_request_id")
