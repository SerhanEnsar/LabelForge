# Copyright (c) 2026 Serhan Ensar. All rights reserved.
"""Eksik paketleri otomatik kurar. Yalnızca standart kütüphane kullanır (uygulama açılmadan önce çalışır)."""
import importlib
import importlib.util
import subprocess
import sys

# (import adı, pip paket adı)
REQUIRED = [
    ("customtkinter", "customtkinter"),
    ("PIL", "Pillow"),
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
]
# SAM otomatik etiket için; kurulamazsa uygulama OpenCV GrabCut ile çalışır.
SAM_PACKAGES = [
    ("segment_anything", "segment-anything"),
    ("torch", "torch"),
]


def missing(specs) -> list:
    """Kurulu olmayan pip paket adlarını döndürür."""
    return [pkg for mod, pkg in specs if importlib.util.find_spec(mod) is None]


def pip_install(packages, on_line=None) -> tuple:
    """pip ile kurar. Her çıktı satırı on_line'a verilir. Döndürür: (başarılı mı, son satır)."""
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *packages]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    last = ""
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        last = line
        if on_line:
            on_line(line)
    code = proc.wait()
    importlib.invalidate_caches()
    return code == 0, last


def ensure_required() -> None:
    """Uygulama başlamadan önce zorunlu paketleri konsolda kurar. Kurulamazsa çıkar."""
    todo = missing(REQUIRED)
    if not todo:
        return
    print("Eksik paketler kuruluyor: " + ", ".join(todo), flush=True)
    ok, last = pip_install(todo, on_line=lambda l: print("  " + l, flush=True))
    if not ok:
        print(f"Paket kurulumu başarısız: {last}\n"
              "Sanal ortam (venv) kullanmayı dene: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
              flush=True)
        raise SystemExit(1)
