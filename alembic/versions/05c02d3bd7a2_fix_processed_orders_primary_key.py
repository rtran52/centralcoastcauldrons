"""Fix processed orders primary key

Revision ID: 05c02d3bd7a2
Revises: 22d66493f7ce
Create Date: 2026-04-26

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "05c02d3bd7a2"
down_revision: Union[str, None] = "22d66493f7ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_table("processed_orders")
    op.create_table(
        "processed_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("order_id", "endpoint", name="uq_order_endpoint"),
    )


def downgrade():
    op.drop_table("processed_orders")
    op.create_table(
        "processed_orders",
        sa.Column("order_id", sa.Integer(), primary_key=True),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
