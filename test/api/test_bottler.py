from src.api.bottler import PotionMixes


def test_potion_mix_valid():
    mix = PotionMixes(potion_type=[100, 0, 0, 0], quantity=5)
    assert mix.potion_type == [100, 0, 0, 0]
    assert mix.quantity == 5


def test_potion_mix_green():
    mix = PotionMixes(potion_type=[0, 100, 0, 0], quantity=3)
    assert mix.potion_type == [0, 100, 0, 0]


def test_potion_mix_purple():
    mix = PotionMixes(potion_type=[50, 0, 50, 0], quantity=2)
    assert mix.potion_type == [50, 0, 50, 0]
    assert mix.quantity == 2


def test_potion_mix_invalid_sum():
    try:
        PotionMixes(potion_type=[50, 0, 0, 0], quantity=1)
        assert False, "Should have raised"
    except Exception:
        pass


def test_potion_mix_dark():
    mix = PotionMixes(potion_type=[0, 0, 0, 100], quantity=1)
    assert mix.potion_type == [0, 0, 0, 100]
