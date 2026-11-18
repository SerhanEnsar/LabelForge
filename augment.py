"""LabelForge augmentation altyapısı (YOLO detect + segment etiketleri).

Kullanım (yalnızca eğitim klasörü üzerinde çalıştırın, val/test'e uygulamayın):

    python augment.py --images DATASET/train/images --labels DATASET/train/labels \
                      --copies 3 --seed 42

Çıktılar aynı klasörlere `<ad>_aug<k>.jpg` ve `<ad>_aug<k>.txt` olarak yazılır.
Orijinal dosyalara dokunulmaz.

Poligon (segment) etiketleri köşe noktaları olarak dönüştürülür; bbox etiketleri
dört köşeli kutu olarak dönüştürülüp sonra kutu olarak geri yazılır.
"""

import argparse
import os
import random
import sys

import cv2
import numpy as np

try:
    import albumentations as A
except ImportError:  # pragma: no cover
    sys.exit("albumentations gerekli: pip install albumentations")

from labelforge import parse_label_line, format_label_line

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp")


# ── Dönüşüm tanımı ────────────────────────────────────────────────────────────
# Tüm dönüşümler burada. Yeni özellik eklemek için bu fonksiyonu değiştirin.
# Tanım, kullanıcıyla netleştirilene kadar muhafazakâr bir başlangıç setidir.

def build_transform(seed=None):
    return A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.Rotate(limit=10, border_mode=cv2.BORDER_CONSTANT, p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
            A.HueSaturationValue(hue_shift_limit=8, sat_shift_limit=20, val_shift_limit=15, p=0.3),
            A.GaussianBlur(blur_limit=(3, 5), p=0.1),
        ],
        keypoint_params=A.KeypointParams(format="xy", remove_invisible=False),
        seed=seed,
    )


# ── Yardımcılar ──────────────────────────────────────────────────────────────

def read_image(path):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def write_image(path, img):
    ext = os.path.splitext(path)[1] or ".jpg"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError(f"Görüntü yazılamadı: {path}")
    buf.tofile(path)


def entry_to_points(entry, w, h):
    """Entry'den piksel cinsinden köşe listesi (poligon yoksa bbox köşeleri)."""
    if len(entry) >= 6 and entry[5]:
        coords = entry[5]
    else:
        cx, cy, bw, bh = entry[1:5]
        coords = [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy - bh / 2,
                  cx + bw / 2, cy + bh / 2, cx - bw / 2, cy + bh / 2]
    pts = [(coords[i] * w, coords[i + 1] * h) for i in range(0, len(coords), 2)]
    return pts


def points_to_entry(cid, pts_px, w, h, was_poly):
    """Piksel köşelerinden normalize entry üretir (poligon mu bbox mu, kaynağa göre)."""
    xs = [p[0] for p in pts_px]
    ys = [p[1] for p in pts_px]
    # Görüntü dışına taşan noktaları sınırla
    x1, x2 = max(0.0, min(xs)), min(float(w), max(xs))
    y1, y2 = max(0.0, min(ys)), min(float(h), max(ys))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None  # dönüşümden sonra kaybolmuş nesne
    cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
    bw, bh = (x2 - x1) / w, (y2 - y1) / h
    if was_poly:
        norm = []
        for x, y in pts_px:
            norm += [min(max(x / w, 0.0), 1.0), min(max(y / h, 0.0), 1.0)]
        return [cid, cx, cy, bw, bh, norm]
    return [cid, cx, cy, bw, bh]


# ── Ana işlem ────────────────────────────────────────────────────────────────

def augment_pair(img_path, lbl_path, copies, seed=None):
    img = read_image(img_path)
    if img is None:
        print(f"[atla] görüntü okunamadı: {img_path}")
        return 0
    h, w = img.shape[:2]

    entries = []
    if os.path.exists(lbl_path):
        with open(lbl_path) as f:
            for line in f:
                e = parse_label_line(line)
                if e is not None:
                    entries.append(e)

    ext = os.path.splitext(img_path)[1]
    base_dir = os.path.dirname(img_path)
    lbl_dir = os.path.dirname(lbl_path)
    base = os.path.splitext(os.path.basename(img_path))[0]
    base_lbl = os.path.splitext(os.path.basename(lbl_path))[0]

    # Her nesnenin köşeleri tek bir keypoint listesinde; sıra ve sayı saklanır
    keypoints, spans = [], []
    for e in entries:
        pts = entry_to_points(e, w, h)
        spans.append((len(keypoints), len(pts)))
        keypoints.extend(pts)

    made = 0
    for k in range(1, copies + 1):
        tf = build_transform(seed=None if seed is None else seed + k)
        out = tf(image=img, keypoints=keypoints)
        new_img = out["image"]
        new_kps = out["keypoints"]

        new_lines = []
        for e, (start, count) in zip(entries, spans):
            pts = [(float(x), float(y)) for x, y in new_kps[start:start + count]]
            ne = points_to_entry(int(e[0]), pts, w, h,
                                 was_poly=(len(e) >= 6 and bool(e[5])))
            if ne is not None:
                new_lines.append(format_label_line(ne))

        out_img = os.path.join(base_dir, f"{base}_aug{k}{ext}")
        out_lbl = os.path.join(lbl_dir, f"{base_lbl}_aug{k}.txt")
        write_image(out_img, new_img)
        with open(out_lbl, "w") as f:
            f.write("\n".join(new_lines) + ("\n" if new_lines else ""))
        made += 1
    return made


def main():
    ap = argparse.ArgumentParser(description="LabelForge augmentation (yalnızca train verisi)")
    ap.add_argument("--images", required=True, help="Görüntü klasörü")
    ap.add_argument("--labels", required=True, help="Etiket (.txt) klasörü")
    ap.add_argument("--copies", type=int, default=2, help="Her görüntüden kaç kopya")
    ap.add_argument("--seed", type=int, default=None, help="Tekrarlanabilirlik için tohum")
    args = ap.parse_args()

    if not os.path.isdir(args.images) or not os.path.isdir(args.labels):
        sys.exit("Görüntü ve etiket klasörleri var olmalı.")

    random.seed(args.seed)
    files = sorted(f for f in os.listdir(args.images)
                   if f.lower().endswith(IMG_EXTS) and "_aug" not in f)
    total = 0
    for name in files:
        base = os.path.splitext(name)[0]
        img_path = os.path.join(args.images, name)
        lbl_path = os.path.join(args.labels, base + ".txt")
        total += augment_pair(img_path, lbl_path, args.copies, args.seed)
    print(f"{len(files)} görüntüden {total} kopya üretildi.")


if __name__ == "__main__":
    main()
