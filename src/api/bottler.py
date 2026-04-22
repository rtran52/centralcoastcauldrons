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
            qty = potion.quantity
            r, g, b, d = potion.potion_type

            red_ml_used = r * qty
            green_ml_used = g * qty
            blue_ml_used = b * qty

            if r == 100:
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET red_ml = red_ml - :ml, red_potions = red_potions + :qty"
                ), {"ml": red_ml_used, "qty": qty})
            elif g == 100:
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET green_ml = green_ml - :ml, green_potions = green_potions + :qty"
                ), {"ml": green_ml_used, "qty": qty})
            elif b == 100:
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET blue_ml = blue_ml - :ml, blue_potions = blue_potions + :qty"
                ), {"ml": blue_ml_used, "qty": qty})


@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    with db.engine.begin() as connection:
        row = connection.execute(sqlalchemy.text(
            "SELECT red_ml, green_ml, blue_ml FROM global_inventory"
        )).one()

    plan = []

    if row.red_ml >= 100:
        plan.append(PotionMixes(potion_type=[100, 0, 0, 0], quantity=row.red_ml // 100))
    if row.green_ml >= 100:
        plan.append(PotionMixes(potion_type=[0, 100, 0, 0], quantity=row.green_ml // 100))
    if row.blue_ml >= 100:
        plan.append(PotionMixes(potion_type=[0, 0, 100, 0], quantity=row.blue_ml // 100))

    return plan