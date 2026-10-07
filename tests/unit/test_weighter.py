"""Unit tests for pipeline/weighter.py — PerspectiveWeighter."""

from solution_tradeoff.pipeline.weighter import PerspectiveWeighter

_CFG = {"budget": {"multiplier": 2.5, "round_to": 5, "minimum": 15}}


def _w() -> PerspectiveWeighter:
    return PerspectiveWeighter(_CFG)


def test_known_input_12():
    assert _w().calculate(12) == 30


def test_minimum_enforced():
    assert _w().calculate(4) == 15


def test_minimum_enforced_zero():
    assert _w().calculate(0) == 15


def test_rounds_to_nearest_5():
    assert _w().calculate(7) == 20  # 7 * 2.5 = 17.5 → round(3.5) * 5 = 20


def test_exact_multiple_unchanged():
    # 8 * 2.5 = 20.0 → already a multiple of 5
    assert _w().calculate(8) == 20


def test_large_count():
    # 100 * 2.5 = 250
    assert _w().calculate(100) == 250
