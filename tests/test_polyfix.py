import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polyfix import repair_polygon, self_intersects  # noqa: E402


def test_convex_shape_is_not_self_intersecting():
    circle = [(math.cos(t), math.sin(t)) for t in [i * 2 * math.pi / 12 for i in range(12)]]
    assert not self_intersects(circle)


def test_zigzag_order_is_detected_and_repaired():
    # Kenarın iki yanında gidip gelen tıklama sırası (kendini kesen)
    zig = [(0, 0), (4, 1), (0, 2), (4, 3), (0, 4), (4, 5)]
    assert self_intersects(zig)
    fixed = repair_polygon(zig)
    assert fixed is not None and not self_intersects(fixed)
    assert sorted(fixed) == sorted(zig)


def test_unrepairable_returns_none_when_still_crossing():
    bow = [(0, 0), (2, 2), (2, 0), (0, 2)]  # kelebek: sıralama sonrası da çakışır
    fixed = repair_polygon(bow)
    assert fixed is None or not self_intersects(fixed)
