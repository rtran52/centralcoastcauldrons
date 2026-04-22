"""Version 2 potions and carts tables

Revision ID: ae7ab48b993a
Revises: 9b98c6500108
Create Date: 2026-04-22

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "ae7ab48b993a"
down_revision: Union[str, None] = "9b98c6500108"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create potions table
    op.create_table(
        "potions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sku", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("red_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("green_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blue_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dark_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("inventory", sa.Integer(), nullable=False, server_default="0"),
    )

    # Seed starting potions
    op.execute(sa.text("""
        INSERT INTO potions (sku, name, red_ml, green_ml, blue_ml, dark_ml, price) VALUES
        ('RED_POTION_0', 'Red Potion', 100, 0, 0, 0, 50),
        ('GREEN_POTION_0', 'Green Potion', 0, 100, 0, 0, 50),
        ('BLUE_POTION_0', 'Blue Potion', 0, 0, 100, 0, 50),
        ('PURPLE_POTION_0', 'Purple Potion', 50, 0, 50, 0, 60)
    """))

    # Create carts table
    op.create_table(
        "carts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_name", sa.String(), nullable=False),
        sa.Column("customer_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # Create cart_items table
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id"), nullable=False),
        sa.Column("potion_id", sa.Integer(), sa.ForeignKey("potions.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_table("potions")