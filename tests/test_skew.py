import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skew import apply_h, corner_angles, homography, square_polygon, warp_image  # noqa: E402


def _skewed_quad():
    """Dik 200x100 dikdörtgenin eğik görüntüdeki karşılığı (TL, TR, BR, BL)."""
    rect = [(100, 100), (300, 100), (300, 200), (100, 200)]
    true_h = homography(rect, [(120, 90), (310, 130), (290, 230), (95, 190)])
    quad = [apply_h(true_h, p) for p in rect]
    return quad, true_h


def test_homography_maps_quad_to_rectangle():
    quad, _ = _skewed_quad()
    rect = [(0, 0), (200, 0), (200, 100), (0, 100)]
    fwd = homography(quad, rect)
    for q, r in zip(quad, rect):
        x, y = apply_h(fwd, q)
        assert abs(x - r[0]) < 1e-6 and abs(y - r[1]) < 1e-6


def test_rectangle_in_skewed_space_becomes_right_angles():
    quad, _ = _skewed_quad()
    rect = [(0, 0), (200, 0), (200, 100), (0, 100)]
    fwd = homography(quad, rect)
    # Eğik görüntüdeki, ama düzeltilince kabaca dikdörtgen olan jitterlı poligon
    jitter = [(0.6, -0.4), (-0.5, 0.7), (0.3, 0.2), (-0.4, -0.6)]
    skewed_poly = []
    for (x, y), (dx, dy) in zip(quad, jitter):
        skewed_poly.append((x + dx, y + dy))
    rectified = [apply_h(fwd, p) for p in skewed_poly]
    snapped, changed = square_polygon(rectified)
    assert changed
    for angle in corner_angles(snapped):
        assert abs(angle - 90) < 1.0


def test_free_form_polygon_is_left_alone():
    circle = [(100 + 50 * math.cos(t), 100 + 50 * math.sin(t))
              for t in [i * 2 * math.pi / 16 for i in range(16)]]
    out, changed = square_polygon(circle)
    assert not changed and out == circle


def test_warp_puts_object_at_expected_place():
    quad, _ = _skewed_quad()
    img = Image.new("RGB", (400, 300), (0, 0, 0))
    ImageDraw.Draw(img).polygon(quad, fill=(255, 255, 255))
    out, fwd, (W, H) = warp_image(img, quad)
    # Projektif dönüşümde karşıt kenarlar eşit değildir; boyut yaklaşık olmalı
    assert abs(W - 200) <= 6 and abs(H - 100) <= 6
    # Dikdörtgenin merkezi düzeltilmiş görüntüde beyaz olmalı
    r, g, b = out.getpixel((W // 2, H // 2))
    assert r > 200 and g > 200 and b > 200
