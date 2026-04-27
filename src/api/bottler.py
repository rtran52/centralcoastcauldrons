from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)


class PotionMixes(BaseModel):
    potion_type: List[int] = Field(..., min_length=4, max_length=4)
    quantity: int = Field(..., ge=1, le=10000)

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[int]) -> List[int]:
        if sum(potion_type) != 100:
            raise ValueError("Sum of potion_type values must be exactly 100")
        return potion_type


def get_current_inventory(connection):
    return connection.execute(
        sqlalchemy.text(
            """
        SELECT
            COALESCE(SUM(red_ml_change), 0) AS red_ml,
            COALESCE(SUM(green_ml_change), 0) AS green_ml,
            COALESCE(SUM(blue_ml_change), 0) AS blue_ml,
            COALESCE(SUM(dark_ml_change), 0) AS dark_ml
        FROM ledger_entries
        """
        )
    ).one()


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        existing = connection.execute(
            sqlalchemy.text(
                "SELECT id FROM processed_orders WHERE order_id = :oid AND endpoint = 'bottler_deliver'"
            ),
            {"oid": order_id},
        ).fetchone()
        if existing:
            return

        connection.execute(
            sqlalchemy.text(
                "INSERT INTO processed_orders (order_id, endpoint) VALUES (:oid, 'bottler_deliver')"
            ),
            {"oid": order_id},
        )

        for potion in potions_delivered:
            r, g, b, d = potion.potion_type
            qty = potion.quantity

            potion_row = connection.execute(
                sqlalchemy.text(
                    "SELECT id FROM potions WHERE red_ml = :r AND green_ml = :g AND blue_ml = :b AND dark_ml = :d"
                ),
                {"r": r, "g": g, "b": b, "d": d},
            ).fetchone()

            if not potion_row:
                continue

            txn = connection.execute(
                sqlalchemy.text(
                    "INSERT INTO ledger_transactions (description) VALUES (:desc) RETURNING id"
                ),
                {"desc": f"Bottling order {order_id}: {qty}x [{r},{g},{b},{d}]"},
            ).scalar_one()

            connection.execute(
                sqlalchemy.text(
                    """
                INSERT INTO ledger_entries
                (transaction_id, red_ml_change, green_ml_change, blue_ml_change, dark_ml_change, potion_id, potion_change)
                VALUES (:txn, :red, :green, :blue, :dark, :pid, :pchange)
                """
                ),
                {
                    "txn": txn,
                    "red": -(r * qty),
                    "green": -(g * qty),
                    "blue": -(b * qty),
                    "dark": -(d * qty),
                    "pid": potion_row.id,
                    "pchange": qty,
                },
            )


@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    with db.engine.begin() as connection:
        inv = get_current_inventory(connection)
        potions = connection.execute(
            sqlalchemy.text("SELECT red_ml, green_ml, blue_ml, dark_ml FROM potions")
        ).fetchall()

    available = {
        "red": inv.red_ml,
        "green": inv.green_ml,
        "blue": inv.blue_ml,
        "dark": inv.dark_ml,
    }

    plan = []
    for potion in potions:
        r, g, b, d = potion.red_ml, potion.green_ml, potion.blue_ml, potion.dark_ml
        if r + g + b + d == 0:
            continue

        max_qty = float("inf")
        if r > 0:
            max_qty = min(max_qty, available["red"] // r)
        if g > 0:
            max_qty = min(max_qty, available["green"] // g)
        if b > 0:
            max_qty = min(max_qty, available["blue"] // b)
        if d > 0:
            max_qty = min(max_qty, available["dark"] // d)

        max_qty = int(max_qty)
        if max_qty > 0:
            plan.append(PotionMixes(potion_type=[r, g, b, d], quantity=max_qty))
            available["red"] -= r * max_qty
            available["green"] -= g * max_qty
            available["blue"] -= b * max_qty
            available["dark"] -= d * max_qty

    return plan
