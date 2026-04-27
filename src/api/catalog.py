from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Annotated
import sqlalchemy
from src import database as db

router = APIRouter()


class CatalogItem(BaseModel):
    sku: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_]{1,20}$")]
    name: str
    quantity: Annotated[int, Field(ge=1, le=10000)]
    price: Annotated[int, Field(ge=1, le=500)]
    potion_type: List[int] = Field(..., min_length=4, max_length=4)


@router.get("/catalog/", tags=["catalog"], response_model=List[CatalogItem])
def get_catalog() -> List[CatalogItem]:
    with db.engine.begin() as connection:
        rows = connection.execute(
            sqlalchemy.text(
                """
            SELECT p.sku, p.name, p.price, p.red_ml, p.green_ml, p.blue_ml, p.dark_ml,
                   COALESCE(SUM(le.potion_change), 0) AS inventory
            FROM potions p
            LEFT JOIN ledger_entries le ON le.potion_id = p.id
            GROUP BY p.id, p.sku, p.name, p.price, p.red_ml, p.green_ml, p.blue_ml, p.dark_ml
            HAVING COALESCE(SUM(le.potion_change), 0) > 0
            LIMIT 6
            """
            )
        ).fetchall()

    catalog = []
    for row in rows:
        catalog.append(
            CatalogItem(
                sku=row.sku,
                name=row.name,
                quantity=row.inventory,
                price=row.price,
                potion_type=[row.red_ml, row.green_ml, row.blue_ml, row.dark_ml],
            )
        )

    return catalog
