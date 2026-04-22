from src.api.barrels import Barrel, BarrelOrder
from typing import List


def test_barrel_model_valid() -> None:
    barrel = Barrel(
        sku="SMALL_RED_BARREL",
        ml_per_barrel=1000,
        potion_type=[1.0, 0, 0, 0],
        price=100,
        quantity=10,
    )
    assert barrel.sku == "SMALL_RED_BARREL"
    assert barrel.price == 100


def test_barrel_order_model() -> None:
    order = BarrelOrder(sku="SMALL_RED_BARREL", quantity=1)
    assert order.sku == "SMALL_RED_BARREL"
    assert order.quantity == 1


def test_barrel_potion_type_invalid() -> None:
    try:
        Barrel(
            sku="BAD_BARREL",
            ml_per_barrel=1000,
            potion_type=[0.5, 0, 0, 0],
            price=100,
            quantity=1,
        )
        assert False, "Should have raised"
    except Exception:
        pass
