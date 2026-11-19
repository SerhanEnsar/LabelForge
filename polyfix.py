"""Poligon doğrulama ve onarımı: kendini kesen köşe sıralarını düzeltir.

Köşeler çizim sırasına göre kaydedilir. İnce nesnelerde (kaşık) tıklamalar kenarın iki
yanında gidip gelirse poligon kendini keser. Bu modül böyle poligonları tespit eder ve
mümkünse merkez etrafında açıya göre sıralayarak onarır.
"""
import math


def _orient(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def self_intersects(pts) -> bool:
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue  # komşu kenarlar
            c, d = pts[j], pts[(j + 1) % n]
            if _orient(a, b, c) * _orient(a, b, d) < 0 and _orient(c, d, a) * _orient(c, d, b) < 0:
                return True
    return False


def repair_polygon(pts):
    """Kendini kesen poligonu açı sıralamasıyla onarır. Onarım da kendini kesiyorsa None döner."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    fixed = sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    return None if self_intersects(fixed) else fixed
