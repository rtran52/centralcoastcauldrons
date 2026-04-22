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


cart_id_counter = 1
carts: dict[int, dict[str, int]] = {}


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
    global cart_id_counter
    cart_id = cart_id_counter
    cart_id_counter += 1
    carts[cart_id] = {}
    return CartCreateResponse(cart_id=cart_id)


class CartItem(BaseModel):
    quantity: int = Field(ge=1)


@router.post("/{cart_id}/items/{item_sku}", status_code=status.HTTP_204_NO_CONTENT)
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    if cart_id not in carts:
        raise HTTPException(status_code=404, detail="Cart not found")
    carts[cart_id][item_sku] = cart_item.quantity


class CheckoutResponse(BaseModel):
    total_potions_bought: int
    total_gold_paid: int


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout", response_model=CheckoutResponse)
def checkout(cart_id: int, cart_checkout: CartCheckout):
    if cart_id not in carts:
        raise HTTPException(status_code=404, detail="Cart not found")

    total_potions_bought = 0
    total_gold_paid = 0

    with db.engine.begin() as connection:
        for sku, quantity in carts[cart_id].items():
            total_potions_bought += quantity
            total_gold_paid += quantity * 50

            if sku == "RED_POTION_0":
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET red_potions = red_potions - :qty, gold = gold + :gold"
                ), {"qty": quantity, "gold": quantity * 50})
            elif sku == "GREEN_POTION_0":
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET green_potions = green_potions - :qty, gold = gold + :gold"
                ), {"qty": quantity, "gold": quantity * 50})
            elif sku == "BLUE_POTION_0":
                connection.execute(sqlalchemy.text(
                    "UPDATE global_inventory SET blue_potions = blue_potions - :qty, gold = gold + :gold"
                ), {"qty": quantity, "gold": quantity * 50})

    del carts[cart_id]

    return CheckoutResponse(total_potions_bought=total_potions_bought, total_gold_paid=total_gold_paid)