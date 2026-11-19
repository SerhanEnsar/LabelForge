"""Poligon düzenleme yardımcıları (GUI'den bağımsız).

- Köşe seçimi ve poligon içinde tıklama testi
- Kenara yapışma (Canny kenar haritasına göre)
- GrabCut ile kutudan otomatik poligon önerisi
Koordinatlar: normalize (0-1) ya da görüntü pikseli (px) olarak belirtilir.
"""
import os

import cv2
import numpy as np


def flat_to_pairs(flat) -> list:
    return [(float(flat[i]), float(flat[i + 1])) for i in range(0, len(flat), 2)]


def pairs_to_flat(pairs) -> list:
    out = []
    for x, y in pairs:
        out += [float(x), float(y)]
    return out


def refresh_bbox(entry: list) -> None:
    """Poligon değiştiğinde entry'nin merkez ve boyut alanlarını poligondan yeniden hesaplar."""
    pts = flat_to_pairs(entry[5])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
    entry[1], entry[2] = (x1 + x2) / 2, (y1 + y2) / 2
    entry[3], entry[4] = x2 - x1, y2 - y1


def nearest_vertex(pairs, sx: float, sy: float, tol: float):
    """Ekran ya da piksel koordinatı (sx, sy) için tol içindeki en yakın köşe indeksi, yoksa None."""
    best, best_d = None, tol
    for i, (x, y) in enumerate(pairs):
        d = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
        if d <= best_d:
            best, best_d = i, d
    return best


def point_in_polygon(pairs, x: float, y: float) -> bool:
    inside = False
    n = len(pairs)
    j = n - 1
    for i in range(n):
        xi, yi = pairs[i]
        xj, yj = pairs[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def edge_map(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if img_bgr.ndim == 3 else img_bgr
    return cv2.Canny(gray, 50, 150)


def snap_to_edge(edges: np.ndarray, px: float, py: float, radius: int = 8):
    """(px, py) çevresinde radius içindeki en yakın kenar pikseline yapışır; yoksa girdiyi döndürür."""
    H, W = edges.shape[:2]
    x0, y0 = max(0, int(px) - radius), max(0, int(py) - radius)
    x1, y1 = min(W, int(px) + radius + 1), min(H, int(py) + radius + 1)
    ys, xs = np.nonzero(edges[y0:y1, x0:x1])
    if len(xs) == 0:
        return px, py
    xs = xs + x0
    ys = ys + y0
    d2 = (xs - px) ** 2 + (ys - py) ** 2
    k = int(np.argmin(d2))
    if d2[k] > radius * radius:
        return px, py
    return float(xs[k]), float(ys[k])


def grabcut_polygon(img_bgr: np.ndarray, rect, max_side: int = 700, epsilon_frac: float = 0.004):
    """rect = (x, y, w, h) piksel. Nesneyi GrabCut ile ayırıp en büyük konturun poligonunu döndürür.
    Döndürür: [(x, y), ...] piksel koordinatı ya da None (nesne bulunamadı)."""
    H, W = img_bgr.shape[:2]
    scale = min(1.0, max_side / max(H, W))
    small = cv2.resize(img_bgr, (max(1, int(W * scale)), max(1, int(H * scale))), interpolation=cv2.INTER_AREA)
    x, y, w, h = rect
    r = (int(x * scale), int(y * scale), max(2, int(w * scale)), max(2, int(h * scale)))
    mask = np.zeros(small.shape[:2], np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(small, mask, r, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 20:
        return None
    approx = cv2.approxPolyDP(c, epsilon_frac * cv2.arcLength(c, True), True).reshape(-1, 2)
    if len(approx) < 3:
        return None
    return [(float(px) / scale, float(py) / scale) for px, py in approx]


# ── Tıklama tabanlı ayıklama ─────────────────────────────────────────────────

def mask_to_polygon(mask: np.ndarray, prefer_pt=None, epsilon_frac: float = 0.004):
    """İkili maskenin poligonunu (piksel) döndürür. prefer_pt verilirse onu içeren kontur seçilir."""
    cnts, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    c = None
    if prefer_pt is not None:
        inside = [k for k in cnts if cv2.pointPolygonTest(k, (float(prefer_pt[0]), float(prefer_pt[1])), False) >= 0]
        if inside:
            c = max(inside, key=cv2.contourArea)
    if c is None:
        c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < 20:
        return None
    approx = cv2.approxPolyDP(c, epsilon_frac * cv2.arcLength(c, True), True).reshape(-1, 2)
    if len(approx) < 3:
        return None
    return [(float(x), float(y)) for x, y in approx]


def click_grabcut(img_bgr: np.ndarray, fg_pts, bg_pts, max_side: int = 700):
    """Tıklanan nesneyi ayırır. fg_pts: nesne üstüne tıklamalar, bg_pts: arka plan tıklamaları (piksel).
    İlk fg noktasının çevresinde otomatik bir çalışma kutusu kurulur. Döndürür: piksel poligonu ya da None."""
    H, W = img_bgr.shape[:2]
    scale = min(1.0, max_side / max(H, W))
    sh, sw = max(1, int(H * scale)), max(1, int(W * scale))
    small = cv2.resize(img_bgr, (sw, sh), interpolation=cv2.INTER_AREA)
    fgs = [(int(x * scale), int(y * scale)) for x, y in fg_pts]
    bgs = [(int(x * scale), int(y * scale)) for x, y in bg_pts]
    fx, fy = fgs[0]
    half = max(30, int(0.45 * min(sh, sw)))   # çalışma kutusu nesneyi içermeli
    rx, ry = max(0, fx - half), max(0, fy - half)
    rw, rh = min(sw, fx + half) - rx, min(sh, fy + half) - ry

    mask = np.full((sh, sw), cv2.GC_BGD, np.uint8)
    mask[ry:ry + rh, rx:rx + rw] = cv2.GC_PR_BGD
    # Tıklamanın çevresi olası nesne: GrabCut renk modelini buradan öğrenir
    cv2.circle(mask, (fx, fy), max(6, half // 2), cv2.GC_PR_FGD, -1)
    for x, y in fgs:
        cv2.circle(mask, (x, y), 3, cv2.GC_FGD, -1)
    for x, y in bgs:
        cv2.circle(mask, (x, y), 3, cv2.GC_BGD, -1)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(small, mask, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    pts = mask_to_polygon(fg, prefer_pt=(fx, fy))
    if pts is None:
        return None
    return [(x / scale, y / scale) for x, y in pts]


# ── SAM (isteğe bağlı) ────────────────────────────────────────────────────────

def load_sam(checkpoint: str, model_type: str = "vit_b"):
    """segment_anything ve model dosyası varsa SamPredictor döndürür; yoksa None."""
    try:
        from segment_anything import SamPredictor, sam_model_registry
    except ImportError:
        return None
    if not checkpoint or not os.path.isfile(checkpoint):
        return None
    sam = sam_model_registry[model_type](checkpoint=checkpoint)
    return SamPredictor(sam)


_sam_image_key = {"key": None}


def sam_polygon(predictor, img_rgb: np.ndarray, key: str, fg_pts, bg_pts):
    """SAM ile tıklama istemlerinden maske ve poligon. Aynı görüntü için görüntü kodlaması önbelleğe alınır."""
    if predictor is None or not fg_pts:
        return None
    if _sam_image_key["key"] != key:
        predictor.set_image(img_rgb)
        _sam_image_key["key"] = key
    coords = np.array(list(fg_pts) + list(bg_pts), dtype=np.float32)
    labels = np.array([1] * len(fg_pts) + [0] * len(bg_pts), dtype=np.int32)
    masks, _, _ = predictor.predict(point_coords=coords, point_labels=labels, multimask_output=False)
    mask = (masks[0].astype(np.uint8)) * 255
    return mask_to_polygon(mask, prefer_pt=fg_pts[0])
