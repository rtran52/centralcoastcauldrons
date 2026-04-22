"""Version 3 ledger and idempotency

Revision ID: 22d66493f7ce
Revises: ae7ab48b993a
Create Date: 2026-04-22

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "22d66493f7ce"
down_revision: Union[str, None] = "ae7ab48b993a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Ledger transactions table - one row per event
    op.create_table(
        "ledger_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("description", sa.String(), nullable=False),
    )

    # Ledger entries - actual balance changes
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("ledger_transactions.id"), nullable=False),
        sa.Column("gold_change", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("red_ml_change", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("green_ml_change", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blue_ml_change", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dark_ml_change", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("potion_id", sa.Integer(), sa.ForeignKey("potions.id"), nullable=True),
        sa.Column("potion_change", sa.Integer(), nullable=False, server_default="0"),
    )

    # Processed orders for idempotency
    op.create_table(
        "processed_orders",
        sa.Column("order_id", sa.Integer(), primary_key=True),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # Add customer/time tracking to cart_items
    op.add_column("carts", sa.Column("character_class", sa.String(), nullable=True))
    op.add_column("carts", sa.Column("character_species", sa.String(), nullable=True))
    op.add_column("carts", sa.Column("level", sa.Integer(), nullable=True))
    op.add_column("cart_items", sa.Column("sold_at", sa.DateTime(), server_default=sa.text("now()")))
    op.add_column("cart_items", sa.Column("day_of_week", sa.String(), nullable=True))
    op.add_column("cart_items", sa.Column("hour", sa.Integer(), nullable=True))

    # Seed initial gold ledger entry (starting 100 gold)
    op.execute(sa.text("""
        INSERT INTO ledger_transactions (description) VALUES ('Initial gold') RETURNING id
    """))
    op.execute(sa.text("""
        INSERT INTO ledger_entries (transaction_id, gold_change)
        SELECT id, 100 FROM ledger_transactions WHERE description = 'Initial gold'
        ORDER BY id DESC LIMIT 1
    """))


def downgrade():
    op.drop_column("cart_items", "hour")
    op.drop_column("cart_items", "day_of_week")
    op.drop_column("cart_items", "sold_at")
    op.drop_column("carts", "level")
    op.drop_column("carts", "character_species")
    op.drop_column("carts", "character_class")
    op.drop_table("processed_orders")
    op.drop_table("ledger_entries")
    op.drop_table("ledger_transactions")