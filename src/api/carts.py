from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from enum import Enum
from typing import List, Optional
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class SearchSortOptions(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"


class SearchSortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class LineItem(BaseModel):
    line_item_id: int
    item_sku: str
    customer_name: str
    line_item_total: int
    timestamp: str


class SearchResponse(BaseModel):
    previous: Optional[str] = None
    next: Optional[str] = None
    results: List[LineItem]


@router.get("/search/", response_model=SearchResponse, tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: SearchSortOptions = SearchSortOptions.timestamp,
    sort_order: SearchSortOrder = SearchSortOrder.desc,
):
    return SearchResponse(previous=None, next=None, results=[])


class Customer(BaseModel):
    customer_id: str
    customer_name: str
    character_class: str
    character_species: str
    level: int = Field(ge=1, le=20)


@router.post("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_visits(visit_id: int, customers: List[Customer]):
    print(customers)
    pass


class CartCreateResponse(BaseModel):
    cart_id: int


@router.post("/", response_model=CartCreateResponse)
def create_cart(new_cart: Customer):
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            """
            INSERT INTO carts (customer_name, customer_id)
            VALUES (:name, :cid)
            RETURNING id
            """
        ), {"name": new_cart.customer_name, "cid": new_cart.customer_id})
        cart_id = result.scalar_one()

    return CartCreateResponse(cart_id=cart_id)


class CartItem(BaseModel):
    quantity: int = Field(ge=1)


@router.post("/{cart_id}/items/{item_sku}", status_code=status.HTTP_204_NO_CONTENT)
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    with db.engine.begin() as connection:
        cart = connection.execute(sqlalchemy.text(
            "SELECT id FROM carts WHERE id = :cart_id"
        ), {"cart_id": cart_id}).fetchone()

        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        potion = connection.execute(sqlalchemy.text(
            "SELECT id FROM potions WHERE sku = :sku"
        ), {"sku": item_sku}).fetchone()

        if not potion:
            raise HTTPException(status_code=404, detail="Potion not found")

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO cart_items (cart_id, potion_id, quantity)
            VALUES (:cart_id, :potion_id, :quantity)
            ON CONFLICT DO NOTHING
            """
        ), {"cart_id": cart_id, "potion_id": potion.id, "quantity": cart_item.quantity})


class CheckoutResponse(BaseModel):
    total_potions_bought: int
    total_gold_paid: int


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout", response_model=CheckoutResponse)
def checkout(cart_id: int, cart_checkout: CartCheckout):
    with db.engine.begin() as connection:
        cart = connection.execute(sqlalchemy.text(
            "SELECT id FROM carts WHERE id = :cart_id"
        ), {"cart_id": cart_id}).fetchone()

        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        items = connection.execute(sqlalchemy.text(
            """
            SELECT ci.quantity, p.price, p.sku, p.id as potion_id
            FROM cart_items ci
            JOIN potions p ON ci.potion_id = p.id
            WHERE ci.cart_id = :cart_id
            """
        ), {"cart_id": cart_id}).fetchall()

        total_potions = 0
        total_gold = 0

        for item in items:
            total_potions += item.quantity
            total_gold += item.quantity * item.price

            connection.execute(sqlalchemy.text(
                "UPDATE potions SET inventory = inventory - :qty WHERE id = :id"
            ), {"qty": item.quantity, "id": item.potion_id})

        connection.execute(sqlalchemy.text(
            "UPDATE global_inventory SET gold = gold + :gold"
        ), {"gold": total_gold})

    return CheckoutResponse(total_potions_bought=total_potions, total_gold_paid=total_gold)