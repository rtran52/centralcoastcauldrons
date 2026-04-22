from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)


class InventoryAudit(BaseModel):
    number_of_potions: int
    ml_in_barrels: int
    gold: int


class CapacityPlan(BaseModel):
    potion_capacity: int = Field(ge=0, le=10)
    ml_capacity: int = Field(ge=0, le=10)


@router.get("/audit", response_model=InventoryAudit)
def get_inventory():
    with db.engine.begin() as connection:
        inv = connection.execute(sqlalchemy.text(
            """
            SELECT
                COALESCE(SUM(gold_change), 0) AS gold,
                COALESCE(SUM(red_ml_change) + SUM(green_ml_change) + SUM(blue_ml_change) + SUM(dark_ml_change), 0) AS ml_in_barrels
            FROM ledger_entries
            """
        )).one()

        potions = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(potion_change), 0) AS total_potions
            FROM ledger_entries
            """
        )).one()

    return InventoryAudit(
        number_of_potions=potions.total_potions,
        ml_in_barrels=inv.ml_in_barrels,
        gold=inv.gold,
    )


@router.post("/plan", response_model=CapacityPlan)
def get_capacity_plan():
    return CapacityPlan(potion_capacity=0, ml_capacity=0)


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def deliver_capacity_plan(capacity_purchase: CapacityPlan, order_id: int):
    print(f"capacity delivered: {capacity_purchase} order_id: {order_id}")
    pass