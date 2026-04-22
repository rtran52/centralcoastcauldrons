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


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_barrels(barrels_delivered: List[Barrel], order_id: int):
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            gold_cost = barrel.price * barrel.quantity
            ml_gained = barrel.ml_per_barrel * barrel.quantity

            if barrel.potion_type[0] == 1:
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET gold = gold - :gold, red_ml = red_ml + :ml"
                ), {"gold": gold_cost, "ml": ml_gained})
            elif barrel.potion_type[1] == 1:
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET gold = gold - :gold, green_ml = green_ml + :ml"
                ), {"gold": gold_cost, "ml": ml_gained})
            elif barrel.potion_type[2] == 1:
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET gold = gold - :gold, blue_ml = blue_ml + :ml"
                ), {"gold": gold_cost, "ml": ml_gained})


@router.post("/plan", response_model=List[BarrelOrder])
def get_wholesale_purchase_plan(wholesale_catalog: List[Barrel]):
    print(f"barrel catalog: {wholesale_catalog}")

    with db.engine.begin() as connection:
        row = connection.execute(sqlalchemy.text(
            "SELECT gold, red_ml, green_ml, blue_ml FROM global_inventory"
        )).one()

    gold = row.gold
    colors = [
        ("red", 0, row.red_ml),
        ("green", 1, row.green_ml),
        ("blue", 2, row.blue_ml),
    ]
    random.shuffle(colors)

    for color_name, idx, current_ml in colors:
        if current_ml < 500:
            barrel = min(
                (b for b in wholesale_catalog if b.potion_type[idx] == 1),
                key=lambda b: b.price,
                default=None,
            )
            if barrel and barrel.price <= gold:
                return [BarrelOrder(sku=barrel.sku, quantity=1)]

    return []