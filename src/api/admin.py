from fastapi import APIRouter, Depends, status
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset():
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("DELETE FROM processed_orders"))
        connection.execute(sqlalchemy.text("DELETE FROM ledger_entries"))
        connection.execute(sqlalchemy.text("DELETE FROM ledger_transactions"))
        connection.execute(sqlalchemy.text("DELETE FROM cart_items"))
        connection.execute(sqlalchemy.text("DELETE FROM carts"))
        connection.execute(sqlalchemy.text("UPDATE potions SET inventory = 0"))
        connection.execute(
            sqlalchemy.text(
                "UPDATE global_inventory SET gold = 100, red_ml = 0, green_ml = 0, blue_ml = 0, red_potions = 0, green_potions = 0, blue_potions = 0"
            )
        )

        # Re-seed starting gold in ledger
        txn = connection.execute(
            sqlalchemy.text(
                "INSERT INTO ledger_transactions (description) VALUES ('Reset: initial gold') RETURNING id"
            )
        ).scalar_one()
        connection.execute(
            sqlalchemy.text(
                "INSERT INTO ledger_entries (transaction_id, gold_change) VALUES (:txn, 100)"
            ),
            {"txn": txn},
        )
