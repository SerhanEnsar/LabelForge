"""Eğik mod geometrisi: perspektif düzeltme ve poligonu dik açıya oturtma.

GUI'den bağımsızdır (saf Python + PIL). Koordinatlar piksel cinsindendir.
Quad köşe sırası: sol-üst, sağ-üst, sağ-alt, sol-alt.
"""
import math

from PIL import Image


# ── Homografi ─────────────────────────────────────────────────────────────────

def _solve(A: list, b: list) -> list:
    """Küçük doğrusal sistemi kısmi pivotlu Gauss eliminasyonu ile çözer."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            raise ValueError("Köşeler doğrusal veya tekil; perspektif tanımlanamadı")
        M[col], M[piv] = M[piv], M[col]
        for r in range(n):
            if r != col and M[r][col] != 0:
                f = M[r][col] / M[col][col]
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def homography(src: list, dst: list) -> list:
    """src'deki 4 noktayı dst'deki 4 noktaya eşleyen H (h33=1) katsayıları.
    Dönüş: [h11, h12, h13, h21, h22, h23, h31, h32]."""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)
    return _solve(A, b)


def apply_h(h: list, pt) -> tuple:
    h11, h12, h13, h21, h22, h23, h31, h32 = h
    x, y = pt
    d = h31 * x + h32 * y + 1
    return ((h11 * x + h12 * y + h13) / d, (h21 * x + h22 * y + h23) / d)


def _dist(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def rectified_size(quad: list) -> tuple:
    tl, tr, br, bl = quad
    w = max(_dist(tl, tr), _dist(bl, br))
    h = max(_dist(tl, bl), _dist(tr, br))
    return max(2, int(round(w))), max(2, int(round(h)))


def warp_image(img: Image.Image, quad: list) -> tuple:
    """Quad'ı dikdörtgene düzeltir. Dönüş: (düzeltilmiş görüntü, H_ileri, (W, H))."""
    W, H = rectified_size(quad)
    rect = [(0, 0), (W, 0), (W, H), (0, H)]
    fwd = homography(quad, rect)        # kaynak -> düzeltilmiş
    inv = homography(rect, quad)        # PIL: çıktı -> kaynak
    out = img.transform((W, H), Image.Transform.PERSPECTIVE, inv, Image.Resampling.BICUBIC)
    return out, fwd, (W, H)


# ── Poligonu dik açıya oturtma ───────────────────────────────────────────────

def _line_of_edge(p, q, kind):
    """Kenarı a*x + b*y = c doğrusuna çevirir. kind: 'H' yatay, 'V' dikey, 'O' serbest."""
    if kind == "H":
        return (0.0, 1.0, (p[1] + q[1]) / 2)
    if kind == "V":
        return (1.0, 0.0, (p[0] + q[0]) / 2)
    a, b = q[1] - p[1], -(q[0] - p[0])
    return (a, b, a * p[0] + b * p[1])


def _intersect(l1, l2):
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-9:
        return None
    return ((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det)


def _area(pts) -> float:
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def square_polygon(pts: list, tol_deg: float = 8.0, min_aligned: float = 0.5) -> tuple:
    """Düzeltilmiş (dik) uzayda poligonu dik açıya oturtur.

    Yalnızca yatay/dikey yaklaşan kenarlar (±tol_deg) hizalanır: yatay kenarlar ortak
    y'ye, dikey kenarlar ortak x'e çekilir. Köşeler komşu doğruların kesişimi olarak
    yeniden hesaplanır; kenarlar gerektiğinde uzar ya da kısalır. Serbest kenarlar
    olduğu gibi kalır.

    Çevrenin en az min_aligned oranı hizalı değilse (yuvarlak/organik şekil) hiç
    dokunulmaz; bu, daireye benzer yemeklerin bozulmasını önler.

    Dönüş: (yeni noktalar, değişti_mi).
    """
    n = len(pts)
    if n < 4:
        return pts, False
    kinds = []
    aligned_len = total_len = 0.0
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        length = _dist(p, q)
        total_len += length
        ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 180
        if min(ang, 180 - ang) <= tol_deg:
            kinds.append("H")
        elif abs(ang - 90) <= tol_deg:
            kinds.append("V")
        else:
            kinds.append("O")
        if kinds[-1] != "O":
            aligned_len += length
    if total_len == 0 or aligned_len / total_len < min_aligned:
        return pts, False

    lines = [_line_of_edge(pts[i], pts[(i + 1) % n], kinds[i]) for i in range(n)]
    new = []
    for i in range(n):
        # Köşe i: kenar i-1 ile kenar i'nin kesişimi
        hit = _intersect(lines[(i - 1) % n], lines[i])
        new.append(hit if hit is not None else pts[i])

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    for p, q in zip(pts, new):
        if _dist(p, q) > 0.25 * diag:
            return pts, False  # aşırı kayma: güvenli tarafta kal
    a0, a1 = _area(pts), _area(new)
    if a0 > 0 and not (0.75 <= a1 / a0 <= 1.25):
        return pts, False
    return new, True


def corner_angles(pts: list) -> list:
    """Her köşedeki iç açı (derece). Test ve doğrulama için."""
    out = []
    n = len(pts)
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        v1 = (a[0] - b[0], a[1] - b[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2) + 1e-12)
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, cos)))))
    return out
