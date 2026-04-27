from src.api.barrels import Barrel, BarrelOrder, best_barrel_for_color


def test_barrel_model_valid():
    barrel = Barrel(
        sku="SMALL_RED_BARREL",
        ml_per_barrel=500,
        potion_type=[1.0, 0, 0, 0],
        price=100,
        quantity=10,
    )
    assert barrel.sku == "SMALL_RED_BARREL"
    assert barrel.price == 100


def test_barrel_order_model():
    order = BarrelOrder(sku="SMALL_RED_BARREL", quantity=1)
    assert order.sku == "SMALL_RED_BARREL"
    assert order.quantity == 1


def test_barrel_potion_type_invalid():
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


def test_best_barrel_for_color_picks_best_value():
    catalog = [
        Barrel(
            sku="SMALL_RED_BARREL",
            ml_per_barrel=500,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            sku="MEDIUM_RED_BARREL",
            ml_per_barrel=2500,
            potion_type=[1.0, 0, 0, 0],
            price=250,
            quantity=10,
        ),
    ]
    best = best_barrel_for_color(catalog, 0, 500)
    assert best.sku == "MEDIUM_RED_BARREL"  # better ml per gold


def test_best_barrel_returns_none_if_cant_afford():
    catalog = [
        Barrel(
            sku="LARGE_RED_BARREL",
            ml_per_barrel=10000,
            potion_type=[1.0, 0, 0, 0],
            price=500,
            quantity=10,
        ),
    ]
    best = best_barrel_for_color(catalog, 0, 100)
    assert best is None


def test_best_barrel_returns_none_if_empty_catalog():
    best = best_barrel_for_color([], 0, 500)
    assert best is None
