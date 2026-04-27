import random
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int = Field(gt=0)
    potion_type: List[float] = Field(..., min_length=4, max_length=4)
    price: int = Field(ge=0)
    quantity: int = Field(ge=0)

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[float]) -> List[float]:
        if not abs(sum(potion_type) - 1.0) < 1e-6:
            raise ValueError("Sum of potion_type values must be exactly 1.0")
        return potion_type


class BarrelOrder(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


def get_current_inventory(connection):
    return connection.execute(
        sqlalchemy.text(
            """
        SELECT
            COALESCE(SUM(gold_change), 0) AS gold,
            COALESCE(SUM(red_ml_change), 0) AS red_ml,
            COALESCE(SUM(green_ml_change), 0) AS green_ml,
            COALESCE(SUM(blue_ml_change), 0) AS blue_ml,
            COALESCE(SUM(dark_ml_change), 0) AS dark_ml
        FROM ledger_entries
        """
        )
    ).one()


def best_barrel_for_color(catalog: List[Barrel], color_idx: int, gold: int):
    """Pick the best barrel for a color — biggest ml per gold we can afford."""
    candidates = [
        b
        for b in catalog
        if b.potion_type[color_idx] == 1 and b.price <= gold and b.quantity > 0
    ]
    if not candidates:
        return None
    # Best value = most ml per gold
    return max(candidates, key=lambda b: b.ml_per_barrel / b.price)


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_barrels(barrels_delivered: List[Barrel], order_id: int):
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        existing = connection.execute(
            sqlalchemy.text(
                "SELECT id FROM processed_orders WHERE order_id = :oid AND endpoint = 'barrels_deliver'"
            ),
            {"oid": order_id},
        ).fetchone()
        if existing:
            return

        connection.execute(
            sqlalchemy.text(
                "INSERT INTO processed_orders (order_id, endpoint) VALUES (:oid, 'barrels_deliver')"
            ),
            {"oid": order_id},
        )

        for barrel in barrels_delivered:
            gold_cost = barrel.price * barrel.quantity
            ml_gained = barrel.ml_per_barrel * barrel.quantity

            txn = connection.execute(
                sqlalchemy.text(
                    "INSERT INTO ledger_transactions (description) VALUES (:desc) RETURNING id"
                ),
                {"desc": f"Barrel delivery order {order_id}: {barrel.sku}"},
            ).scalar_one()

            red_ml = green_ml = blue_ml = dark_ml = 0
            if barrel.potion_type[0] == 1:
                red_ml = ml_gained
            elif barrel.potion_type[1] == 1:
                green_ml = ml_gained
            elif barrel.potion_type[2] == 1:
                blue_ml = ml_gained
            elif barrel.potion_type[3] == 1:
                dark_ml = ml_gained

            connection.execute(
                sqlalchemy.text(
                    """
                INSERT INTO ledger_entries
                (transaction_id, gold_change, red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
                VALUES (:txn, :gold, :red, :green, :blue, :dark)
                """
                ),
                {
                    "txn": txn,
                    "gold": -gold_cost,
                    "red": red_ml,
                    "green": green_ml,
                    "blue": blue_ml,
                    "dark": dark_ml,
                },
            )


@router.post("/plan", response_model=List[BarrelOrder])
def get_wholesale_purchase_plan(wholesale_catalog: List[Barrel]):
    print(f"barrel catalog: {wholesale_catalog}")

    with db.engine.begin() as connection:
        inv = get_current_inventory(connection)

    gold = inv.gold
    orders = []
    ML_TARGET = 1000  # try to keep at least 1000ml of each color

    colors = [
        ("red", 0, inv.red_ml),
        ("green", 1, inv.green_ml),
        ("blue", 2, inv.blue_ml),
    ]

    # Randomize so we don't always prioritize same color
    random.shuffle(colors)

    for color_name, idx, current_ml in colors:
        if current_ml >= ML_TARGET:
            continue

        barrel = best_barrel_for_color(wholesale_catalog, idx, gold)
        if not barrel:
            continue

        # Buy as many as we can afford (up to available quantity)
        max_afford = gold // barrel.price
        qty = min(max_afford, barrel.quantity)

        if qty > 0:
            orders.append(BarrelOrder(sku=barrel.sku, quantity=qty))
            gold -= barrel.price * qty

        if gold <= 0:
            break

    return orders
