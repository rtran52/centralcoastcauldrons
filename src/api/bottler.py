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


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        for potion in potions_delivered:
            r, g, b, d = potion.potion_type
            qty = potion.quantity

            # Add potion inventory
            connection.execute(sqlalchemy.text(
                """
                UPDATE potions
                SET inventory = inventory + :qty
                WHERE red_ml = :r AND green_ml = :g AND blue_ml = :b AND dark_ml = :d
                """
            ), {"qty": qty, "r": r, "g": g, "b": b, "d": d})

            # Subtract ml used
            connection.execute(sqlalchemy.text(
                """
                UPDATE global_inventory SET
                red_ml = red_ml - :red_used,
                green_ml = green_ml - :green_used,
                blue_ml = blue_ml - :blue_used
                """
            ), {
                "red_used": r * qty,
                "green_used": g * qty,
                "blue_used": b * qty,
            })


@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text(
            "SELECT red_ml, green_ml, blue_ml, dark_ml FROM global_inventory"
        )).one()

        potions = connection.execute(sqlalchemy.text(
            "SELECT red_ml, green_ml, blue_ml, dark_ml FROM potions"
        )).fetchall()

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

        # How many can we brew given available ml?
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
            # Deduct from available so we don't double-allocate
            available["red"] -= r * max_qty
            available["green"] -= g * max_qty
            available["blue"] -= b * max_qty
            available["dark"] -= d * max_qty

    return plan