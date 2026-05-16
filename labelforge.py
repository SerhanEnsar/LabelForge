"""
LabelForge — YOLO Dataset Editor  (Tactical Edition)
"""
import os, json, subprocess, platform, datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
from typing import Optional

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

APP_NAME     = "LabelForge — YOLO Dataset Editor"
SESSION_FILE = os.path.expanduser("~/.labelforge_session.json")
IMG_EXT      = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
IS_MAC       = platform.system() == "Darwin"

# ── Tactical Palette ──────────────────────────────────────────────────────────
class T:
    BG0  = "#050c08"   # deepest bg
    BG1  = "#091410"   # panel
    BG2  = "#0d1c14"   # surface
    BG3  = "#122018"   # card
    ACC  = "#2de880"   # primary accent (phosphor green)
    ACC2 = "#28c8d0"   # secondary (cyan)
    WARN = "#d4b824"   # amber
    ERR  = "#d44040"   # red
    OK   = "#30c860"   # success
    TX1  = "#70c890"   # primary text
    TX2  = "#365c44"   # secondary text
    TX3  = "#1a3024"   # muted
    BDR  = "#182c1c"   # border
    SEL  = "#122a18"   # selected item bg
    HLBX = "#e8e020"   # highlighted box outline (selected bbox)

PALETTE = [
    "#e85050", "#e8c428", "#40e880", "#40d0e8",
    "#8070e8", "#e870a0", "#e89040", "#50e8c0",
    "#d070e8", "#e8e050", "#50a0e8", "#e87050",
]

LOG_COLORS = {
    "info":    T.TX2,
    "success": T.OK,
    "warning": T.WARN,
    "error":   T.ERR,
    "action":  T.ACC,
}


def get_color(cid: int) -> str:
    return PALETTE[int(cid) % len(PALETTE)]

def read_classes_txt(path: str) -> dict:
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                name = line.strip()
                if name:
                    out[i] = name
    except Exception:
        pass
    return out

def write_classes_txt(path: str, class_names: dict):
    if not class_names:
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        max_id = max(class_names.keys())
        with open(path, "w", encoding="utf-8") as f:
            for i in range(max_id + 1):
                f.write(class_names.get(i, f"class_{i}") + "\n")
    except Exception:
        pass

def fit_pil(img: Image.Image, mw: int, mh: int) -> Image.Image:
    iw, ih = img.size
    if iw == 0 or ih == 0:
        return img
    sc = min(mw / iw, mh / ih)
    return img.resize((max(1, int(iw * sc)), max(1, int(ih * sc))), Image.LANCZOS)

def draw_boxes(pil_img: Image.Image, entries: list, class_names: dict,
               selected: set = None) -> Image.Image:
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    sel = selected or set()
    for idx, entry in enumerate(entries):
        cid = int(entry[0])
        cx, cy, bw, bh = float(entry[1]), float(entry[2]), float(entry[3]), float(entry[4])
        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)
        is_sel = idx in sel
        color  = T.HLBX if is_sel else get_color(cid)
        thick  = 4 if is_sel else 2
        for t in range(thick):
            draw.rectangle([x1 - t, y1 - t, x2 + t, y2 + t], outline=color)
        name = class_names.get(cid, f"#{cid}")
        lbl  = f"{cid}: {name}"
        try:
            tb = draw.textbbox((x1, max(0, y1 - 17)), lbl)
        except AttributeError:
            tw, th = draw.textsize(lbl)
            tb = (x1, max(0, y1 - 17), x1 + tw, max(0, y1 - 17) + th)
        draw.rectangle(tb, fill=color)
        draw.text((tb[0], tb[1]), lbl, fill="#000000")
    return img


# ── FullscreenWindow ──────────────────────────────────────────────────────────

class FullscreenWindow(ctk.CTkToplevel):

    def __init__(self, app: "LabelForgeApp", mode: str):
        super().__init__(app)
        self.app   = app
        self.mode  = mode
        self.title(f"LabelForge  //  {'ORIGINAL' if mode == 'original' else 'ANNOTATED'}")

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.configure(bg=T.BG0)

        # View state
        self._scale = 1.0
        self._ox    = 0.0
        self._oy    = 0.0
        self._img_w = 1
        self._img_h = 1

        # Interaction state
        self._pan_start  = None   # (x,y) at press
        self._rect_start = None   # start of rect-select drag
        self._rect_id    = None
        self._is_panning = False
        self._box_clicked = False # whether press landed on a box
        self._rjob       = None   # deferred render job

        # Selection (local copy, synced on destroy)
        self._sel: set[int] = set(app.selected_indices)

        self._build()
        self.after(120, self._initial_fit)
        self.bind("<Destroy>", self._on_destroy)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Toolbar
        tb = tk.Frame(self, bg=T.BG1, height=40)
        tb.grid(row=0, column=0, sticky="ew")
        tb.pack_propagate(False)

        fname = self.app.image_files[self.app.selected_index] \
                if self.app.selected_index >= 0 else ""
        tk.Label(tb, text=f"//  {fname}", bg=T.BG1, fg=T.TX2,
                 font=("Courier", 10)).pack(side="left", padx=12, pady=8)

        ctk.CTkButton(tb, text="KAPAT  ✕", width=80, height=28,
                      fg_color=T.BG2, hover_color=T.BG3, text_color=T.TX1,
                      font=("Courier", 9), corner_radius=3,
                      command=self.destroy).pack(side="right", padx=8, pady=6)

        # Zoom controls
        ctk.CTkButton(tb, text="FIT", width=36, height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.TX2, font=("Courier", 8),
                      corner_radius=3, command=self._fit_view
                      ).pack(side="right", padx=(0, 2), pady=7)
        ctk.CTkButton(tb, text="+", width=26, height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.ACC, font=("Courier", 11, "bold"),
                      corner_radius=3, command=lambda: self._zoom_step(1)
                      ).pack(side="right", padx=1, pady=7)
        ctk.CTkButton(tb, text="−", width=26, height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.ACC, font=("Courier", 11, "bold"),
                      corner_radius=3, command=lambda: self._zoom_step(-1)
                      ).pack(side="right", padx=(4, 1), pady=7)

        if self.mode == "annotated":
            ctk.CTkButton(tb, text="⌫  SEÇİLENLERİ SİL", width=150, height=28,
                          fg_color=T.ERR, hover_color="#b83030",
                          text_color="#fff", font=("Courier", 9, "bold"),
                          corner_radius=3, command=self._delete_selected
                          ).pack(side="right", padx=4, pady=6)
            tk.Label(tb,
                     text="TIKLA: Seç  |  SHIFT+TIKLA: Çoklu  |  SÜRÜKLE: Alan  |  ←→↑↓: Kaydır",
                     bg=T.BG1, fg=T.TX3, font=("Courier", 8)).pack(side="right", padx=16)

        # Canvas
        self.cv = tk.Canvas(self, bg=T.BG0, highlightthickness=0, cursor="crosshair")
        self.cv.grid(row=1, column=0, sticky="nsew")

        # Status
        self._st = tk.Label(self, text="", bg=T.BG1, fg=T.TX3, font=("Courier", 8))
        self._st.grid(row=2, column=0, sticky="ew")

        self._bind_events()

    def _bind_events(self):
        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._motion)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<MouseWheel>",      self._scroll)
        self.cv.bind("<Configure>",       lambda e: self._schedule_render())
        # Arrow key pan
        self.bind("<Left>",  lambda e: self._pan_key(-24, 0))
        self.bind("<Right>", lambda e: self._pan_key(24, 0))
        self.bind("<Up>",    lambda e: self._pan_key(0, -24))
        self.bind("<Down>",  lambda e: self._pan_key(0, 24))
        # Keyboard zoom shortcuts
        self.bind("<equal>", lambda e: self._zoom_step(1))
        self.bind("<minus>", lambda e: self._zoom_step(-1))
        self.bind("<0>",     lambda e: self._fit_view())
        if IS_MAC:
            try:
                self.cv.bind("<Magnify>", self._pinch)
            except Exception:
                pass
            self.bind("<Command-BackSpace>", lambda e: self._delete_selected())
        else:
            self.bind("<Delete>", lambda e: self._delete_selected())

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def _box_coords(self, entry: list, nw: int, nh: int):
        cx, cy, bw, bh = float(entry[1]), float(entry[2]), float(entry[3]), float(entry[4])
        ox, oy = int(self._ox), int(self._oy)
        x1 = int(cx * nw - bw * nw / 2) + ox
        y1 = int(cy * nh - bh * nh / 2) + oy
        x2 = int(cx * nw + bw * nw / 2) + ox
        y2 = int(cy * nh + bh * nh / 2) + oy
        return x1, y1, x2, y2

    def _find_box_at(self, ex: int, ey: int) -> Optional[int]:
        """Return index of topmost bbox under (ex, ey), or None."""
        nw = max(1, int(self._img_w * self._scale))
        nh = max(1, int(self._img_h * self._scale))
        result = None
        for idx, entry in enumerate(self.app.label_entries):
            x1, y1, x2, y2 = self._box_coords(entry, nw, nh)
            if x1 <= ex <= x2 and y1 <= ey <= y2:
                result = idx   # take topmost (last drawn)
        return result

    def _all_boxes_in_rect(self, rx1, ry1, rx2, ry2) -> set:
        nw = max(1, int(self._img_w * self._scale))
        nh = max(1, int(self._img_h * self._scale))
        found = set()
        for idx, entry in enumerate(self.app.label_entries):
            bx1, by1, bx2, by2 = self._box_coords(entry, nw, nh)
            if bx1 < rx2 and bx2 > rx1 and by1 < ry2 and by2 > ry1:
                found.add(idx)
        return found

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _schedule_render(self, delay: int = 14):
        if self._rjob:
            try:
                self.after_cancel(self._rjob)
            except Exception:
                pass
        self._rjob = self.after(delay, self._render)

    def _initial_fit(self):
        cw, ch = self.cv.winfo_width(), self.cv.winfo_height()
        if cw < 10 or self.app._orig_pil is None:
            self.after(80, self._initial_fit)
            return
        iw, ih = self.app._orig_pil.size
        self._img_w, self._img_h = iw, ih
        self._scale = min(cw / iw, ch / ih) * 0.96
        self._ox = (cw - iw * self._scale) / 2
        self._oy = (ch - ih * self._scale) / 2
        self._render()

    def _render(self):
        self._rjob = None
        cw, ch = self.cv.winfo_width(), self.cv.winfo_height()
        if cw < 10 or self.app._orig_pil is None:
            return
        iw, ih = self.app._orig_pil.size
        self._img_w, self._img_h = iw, ih
        nw = max(1, int(iw * self._scale))
        nh = max(1, int(ih * self._scale))

        resized  = self.app._orig_pil.resize((nw, nh), Image.LANCZOS)
        self._base_tk = ImageTk.PhotoImage(resized)
        self.cv.delete("all")
        self.cv.create_image(int(self._ox), int(self._oy), anchor="nw", image=self._base_tk)

        if self.mode == "annotated":
            for idx, entry in enumerate(self.app.label_entries):
                self._draw_box(idx, entry, nw, nh)

        n_sel = len(self._sel)
        self._st.configure(
            text=f"  ZOOM {self._scale:.2f}x  //  {len(self.app.label_entries)} BOX  //  "
                 f"{n_sel} SEÇİLİ  //  "
                 f"{'SCROLL/PINCH: Zoom  |  DRAG: Pan' if n_sel == 0 else 'DEL: Seçilenleri Sil'}"
        )

    def _draw_box(self, idx: int, entry: list, nw: int, nh: int):
        x1, y1, x2, y2 = self._box_coords(entry, nw, nh)
        cid   = int(entry[0])
        is_sel = idx in self._sel
        color = T.HLBX if is_sel else get_color(cid)
        width = 3 if is_sel else 2
        # Outline only — no fill (fixes the "#ffffff18" invalid color crash)
        self.cv.create_rectangle(x1, y1, x2, y2, outline=color, width=width)
        name = self.app.class_names.get(cid, f"#{cid}")
        lbl  = f"{cid}: {name}"
        llen = max(8, len(lbl)) * 7
        lbl_y = max(0, y1 - 16)
        self.cv.create_rectangle(x1, lbl_y, x1 + llen, lbl_y + 16, fill=color, outline="")
        self.cv.create_text(x1 + 2, lbl_y + 8, text=lbl, anchor="w",
                            fill=T.BG0, font=("Courier", 8, "bold"))

    # ── Events ────────────────────────────────────────────────────────────────

    def _scroll(self, event):
        if event.delta == 0:
            return
        if IS_MAC:
            # Trackpad gives continuous small deltas (3-10 per tick), NOT ±120
            factor = 1.0 + min(max(event.delta * 0.007, -0.25), 0.25)
        else:
            factor = 1.12 if event.delta > 0 else 1 / 1.12
        self._zoom_at(event.x, event.y, factor)

    def _pinch(self, event):
        delta = getattr(event, 'delta', 0)
        if delta == 0:
            return
        factor = 1.0 + min(max(delta, -0.3), 0.3)
        self._zoom_at(event.x, event.y, factor)

    def _zoom_at(self, cx: float, cy: float, factor: float):
        self._ox = cx - (cx - self._ox) * factor
        self._oy = cy - (cy - self._oy) * factor
        self._scale = max(0.03, min(100.0, self._scale * factor))
        self._schedule_render(delay=12)

    def _zoom_step(self, direction: int):
        factor = 1.25 if direction > 0 else 1 / 1.25
        cw, ch = self.cv.winfo_width(), self.cv.winfo_height()
        self._zoom_at(cw / 2, ch / 2, factor)

    def _fit_view(self):
        cw, ch = self.cv.winfo_width(), self.cv.winfo_height()
        if cw < 10 or self.app._orig_pil is None:
            return
        iw, ih = self.app._orig_pil.size
        self._scale = min(cw / iw, ch / ih) * 0.96
        self._ox = (cw - iw * self._scale) / 2
        self._oy = (ch - ih * self._scale) / 2
        self._render()

    def _pan_key(self, dx: int, dy: int):
        self._ox += dx
        self._oy += dy
        self._schedule_render(delay=8)

    def _press(self, event):
        if self.mode == "annotated":
            hit = self._find_box_at(event.x, event.y)
            if hit is not None:
                self._box_clicked = True
                shift = bool(event.state & 0x0001)
                if shift:
                    self._sel.discard(hit) if hit in self._sel else self._sel.add(hit)
                else:
                    self._sel = set() if self._sel == {hit} else {hit}
                self.app.selected_indices = set(self._sel)
                self.app._populate_label_entries()
                self._render()
                self._pan_start  = None
                self._rect_start = None
                return

        self._box_clicked = False
        self._pan_start   = (event.x, event.y)
        self._rect_start  = None
        self._is_panning  = False

    def _motion(self, event):
        if self._box_clicked or self._pan_start is None:
            return

        dx = event.x - self._pan_start[0]
        dy = event.y - self._pan_start[1]

        if not self._is_panning and self._rect_start is None:
            if abs(dx) > 4 or abs(dy) > 4:
                if self.mode == "annotated":
                    # Start rect-select
                    self._rect_start = self._pan_start
                    self._is_panning = False
                else:
                    self._is_panning = True

        if self._rect_start is not None:
            if self._rect_id:
                self.cv.delete(self._rect_id)
            self._rect_id = self.cv.create_rectangle(
                self._rect_start[0], self._rect_start[1], event.x, event.y,
                outline=T.ACC, width=1, dash=(4, 3))
        elif self._is_panning:
            self._ox += dx
            self._oy += dy
            self._pan_start = (event.x, event.y)
            self._schedule_render(delay=8)

    def _release(self, event):
        if self._box_clicked:
            self._box_clicked = False
            return

        if self._rect_id:
            self.cv.delete(self._rect_id)
            self._rect_id = None

        if self._rect_start and self.mode == "annotated":
            rx1 = min(self._rect_start[0], event.x)
            ry1 = min(self._rect_start[1], event.y)
            rx2 = max(self._rect_start[0], event.x)
            ry2 = max(self._rect_start[1], event.y)
            if rx2 - rx1 > 5 and ry2 - ry1 > 5:
                shift = bool(event.state & 0x0001)
                if not shift:
                    self._sel.clear()
                self._sel.update(self._all_boxes_in_rect(rx1, ry1, rx2, ry2))
                self.app.selected_indices = set(self._sel)
                self.app._populate_label_entries()
                self._render()

        self._pan_start   = None
        self._rect_start  = None
        self._is_panning  = False

    def _delete_selected(self):
        if not self._sel:
            return
        n = len(self._sel)
        if not messagebox.askyesno("Silme Onayı",
                                    f"{n} BBox silinsin mi? Bu işlem geri alınabilir.",
                                    parent=self):
            return
        self.app._push_undo()
        self.app.label_entries = [e for i, e in enumerate(self.app.label_entries)
                                   if i not in self._sel]
        self.app.selected_indices.clear()
        self._sel.clear()
        self.app._commit_labels()
        self.app._populate_label_entries()
        self.app._refresh_images()
        self.app.log.log(f"{n} BBox silindi (tam ekran).", "action")
        self._render()

    def _on_destroy(self, event):
        if event.widget is self:
            self.app.selected_indices = set(self._sel)
            self.app._populate_label_entries()
            self.app._refresh_images()


# ── DrawModeWindow ────────────────────────────────────────────────────────────

class DrawModeWindow(ctk.CTkToplevel):

    def __init__(self, app: "LabelForgeApp"):
        super().__init__(app)
        self.app = app
        self.title("LabelForge  //  MANUEL BBOX ÇİZ")
        self.geometry("1120x760")
        self.configure(fg_color=T.BG0)
        self.grab_set()

        self.pil_image    = app._orig_pil.copy()
        self.label_entries = [list(e) for e in app.label_entries]
        self.class_names  = dict(app.class_names)

        self._scale  = 1.0
        self._ox = self._oy = 0.0
        self._fitted   = False   # first render auto-fits; after that scale is preserved
        self._drawing  = False
        self._sx = self._sy = 0
        self._rect_id  = None
        self._pan_pos  = None    # right-click pan start
        self._sel_cid = tk.IntVar(value=next(iter(sorted(app.class_names)), 0))
        self._rjob = None

        self._build()
        self.after(130, self._render)

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Class palette ──
        pal = tk.Frame(self, bg=T.BG1, width=162)
        pal.grid(row=0, column=0, rowspan=3, sticky="nsew")
        pal.pack_propagate(False)

        tk.Label(pal, text="// SINIF", bg=T.BG1, fg=T.ACC,
                 font=("Courier", 10, "bold")).pack(pady=(12, 6), padx=8)

        self._pal_inner = tk.Frame(pal, bg=T.BG1)
        self._pal_inner.pack(fill="both", expand=True, padx=4)
        self._build_palette()

        ctk.CTkButton(pal, text="+ YENİ SINIF", height=28,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.ACC2, font=("Courier", 9),
                      corner_radius=3, command=self._add_class
                      ).pack(fill="x", padx=8, pady=8)

        # ── Toolbar ──
        tb = tk.Frame(self, bg=T.BG1, height=42)
        tb.grid(row=0, column=1, sticky="ew")
        tb.pack_propagate(False)

        tk.Label(tb, text="SOL: Çiz  |  SAĞ: Kaydır  |  ←→↑↓: Pan  |  ±: Zoom",
                 bg=T.BG1, fg=T.TX3, font=("Courier", 8)).pack(side="left", padx=12, pady=8)

        ctk.CTkButton(tb, text="✕ İPTAL", width=70, height=28,
                      fg_color=T.ERR, hover_color="#b83030",
                      text_color="#fff", font=("Courier", 9),
                      corner_radius=3, command=self.destroy
                      ).pack(side="right", padx=4, pady=7)
        ctk.CTkButton(tb, text="✓ UYGULA", width=80, height=28,
                      fg_color=T.BG3, hover_color="#1e3820",
                      text_color=T.ACC, font=("Courier", 9, "bold"),
                      corner_radius=3, command=self._apply
                      ).pack(side="right", padx=4, pady=7)
        ctk.CTkButton(tb, text="↩ GERİ AL", width=80, height=28,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.TX1, font=("Courier", 9),
                      corner_radius=3, command=self._undo_last
                      ).pack(side="right", padx=4, pady=7)
        # Zoom buttons
        ctk.CTkButton(tb, text="FIT", width=36, height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.TX2, font=("Courier", 8),
                      corner_radius=3, command=self._fit_view
                      ).pack(side="right", padx=(0, 2), pady=7)
        ctk.CTkButton(tb, text="+", width=26, height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.ACC, font=("Courier", 11, "bold"),
                      corner_radius=3, command=lambda: self._zoom_step(1)
                      ).pack(side="right", padx=1, pady=7)
        ctk.CTkButton(tb, text="−", width=26, height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.ACC, font=("Courier", 11, "bold"),
                      corner_radius=3, command=lambda: self._zoom_step(-1)
                      ).pack(side="right", padx=(6, 1), pady=7)

        # ── Canvas ──
        self.cv = tk.Canvas(self, bg=T.BG0, cursor="crosshair", highlightthickness=0)
        self.cv.grid(row=1, column=1, sticky="nsew")
        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        # Right-click pan
        self.cv.bind("<ButtonPress-3>",   self._pan_press)
        self.cv.bind("<B3-Motion>",       self._pan_move)
        self.cv.bind("<ButtonRelease-3>", self._pan_end)
        self.cv.bind("<ButtonPress-2>",   self._pan_press)
        self.cv.bind("<B2-Motion>",       self._pan_move)
        self.cv.bind("<ButtonRelease-2>", self._pan_end)
        self.cv.bind("<MouseWheel>",      self._scroll)
        self.cv.bind("<Configure>",       lambda e: self._schedule_render())
        # Arrow key pan & keyboard zoom
        self.bind("<Left>",  lambda e: self._pan_key(-24, 0))
        self.bind("<Right>", lambda e: self._pan_key(24, 0))
        self.bind("<Up>",    lambda e: self._pan_key(0, -24))
        self.bind("<Down>",  lambda e: self._pan_key(0, 24))
        self.bind("<equal>", lambda e: self._zoom_step(1))
        self.bind("<minus>", lambda e: self._zoom_step(-1))
        self.bind("<0>",     lambda e: self._fit_view())
        if IS_MAC:
            try:
                self.cv.bind("<Magnify>", self._pinch)
            except Exception:
                pass

        # ── Status ──
        self._st_var = tk.StringVar(value="Çizmek için tıklayıp sürükleyin")
        tk.Label(self, textvariable=self._st_var, bg=T.BG1, fg=T.TX3,
                 font=("Courier", 8)).grid(row=2, column=1, sticky="ew", padx=10, pady=3)

    def _build_palette(self):
        for w in self._pal_inner.winfo_children():
            w.destroy()
        for cid in sorted(self.class_names.keys()):
            name   = self.class_names[cid]
            color  = get_color(cid)
            is_sel = (self._sel_cid.get() == cid)
            ctk.CTkButton(
                self._pal_inner,
                text=f"{cid}: {name}", height=28,
                fg_color=color if is_sel else T.BG2,
                hover_color=color,
                text_color=T.BG0 if is_sel else T.TX1,
                font=("Courier", 9), corner_radius=3, anchor="w",
                command=lambda c=cid: self._sel_class(c)
            ).pack(fill="x", pady=2)

    def _sel_class(self, cid: int):
        self._sel_cid.set(cid)
        self._build_palette()

    def _add_class(self):
        name = simpledialog.askstring("Yeni Sınıf", "Yeni sınıf adı:", parent=self)
        if not (name and name.strip()):
            return
        new_id = (max(self.class_names.keys()) + 1) if self.class_names else 0
        self.class_names[new_id] = name.strip()
        self.app.class_names[new_id] = name.strip()
        if self.app.classes_file:
            write_classes_txt(self.app.classes_file, self.app.class_names)
        self.app._populate_class_legend()
        self.app.save_session()
        self.app.log.log(f"Yeni sınıf: {new_id}: {name.strip()}", "success")
        self._sel_class(new_id)

    def _schedule_render(self):
        if self._rjob:
            try:
                self.after_cancel(self._rjob)
            except Exception:
                pass
        self._rjob = self.after(14, self._render)

    def _render(self):
        self._rjob = None
        cw, ch = self.cv.winfo_width(), self.cv.winfo_height()
        if cw < 10:
            return
        iw, ih = self.pil_image.size
        if not self._fitted:
            self._scale = min(cw / iw, ch / ih)
            nw = max(1, int(iw * self._scale))
            nh = max(1, int(ih * self._scale))
            self._ox = (cw - nw) / 2
            self._oy = (ch - nh) / 2
            self._fitted = True
        nw = max(1, int(iw * self._scale))
        nh = max(1, int(ih * self._scale))
        base = draw_boxes(self.pil_image.resize((nw, nh), Image.LANCZOS),
                          self.label_entries, self.class_names)
        self._tk = ImageTk.PhotoImage(base)
        self.cv.delete("all")
        self.cv.create_image(int(self._ox), int(self._oy), anchor="nw", image=self._tk)

    def _scroll(self, event):
        if event.delta == 0:
            return
        if IS_MAC:
            factor = 1.0 + min(max(event.delta * 0.007, -0.25), 0.25)
        else:
            factor = 1.12 if event.delta > 0 else 1 / 1.12
        self._zoom_at(event.x, event.y, factor)

    def _pinch(self, event):
        delta = getattr(event, 'delta', 0)
        if delta == 0:
            return
        factor = 1.0 + min(max(delta, -0.3), 0.3)
        self._zoom_at(event.x, event.y, factor)

    def _zoom_at(self, cx: float, cy: float, factor: float):
        self._ox = cx - (cx - self._ox) * factor
        self._oy = cy - (cy - self._oy) * factor
        self._scale = max(0.03, min(100.0, self._scale * factor))
        self._schedule_render()

    def _zoom_step(self, direction: int):
        factor = 1.25 if direction > 0 else 1 / 1.25
        cw, ch = self.cv.winfo_width(), self.cv.winfo_height()
        self._zoom_at(cw / 2, ch / 2, factor)

    def _fit_view(self):
        cw, ch = self.cv.winfo_width(), self.cv.winfo_height()
        if cw < 10:
            return
        iw, ih = self.pil_image.size
        self._scale = min(cw / iw, ch / ih)
        nw = max(1, int(iw * self._scale))
        nh = max(1, int(ih * self._scale))
        self._ox = (cw - nw) / 2
        self._oy = (ch - nh) / 2
        self._render()

    def _pan_key(self, dx: int, dy: int):
        self._ox += dx
        self._oy += dy
        self._schedule_render()

    def _pan_press(self, event):
        self._pan_pos = (event.x, event.y)

    def _pan_move(self, event):
        if self._pan_pos is None:
            return
        self._ox += event.x - self._pan_pos[0]
        self._oy += event.y - self._pan_pos[1]
        self._pan_pos = (event.x, event.y)
        self._schedule_render()

    def _pan_end(self, event):
        self._pan_pos = None

    def _press(self, event):
        self._drawing = True
        self._sx, self._sy = event.x, event.y
        if self._rect_id:
            self.cv.delete(self._rect_id)

    def _drag(self, event):
        if not self._drawing:
            return
        if self._rect_id:
            self.cv.delete(self._rect_id)
        color = get_color(self._sel_cid.get())
        self._rect_id = self.cv.create_rectangle(
            self._sx, self._sy, event.x, event.y,
            outline=color, width=2, dash=(5, 3))

    def _release(self, event):
        if not self._drawing:
            return
        self._drawing = False
        if self._rect_id:
            self.cv.delete(self._rect_id)
            self._rect_id = None
        iw, ih = self.pil_image.size
        def cl(v, lo, hi): return max(lo, min(hi, v))
        ix1 = cl((self._sx    - self._ox) / self._scale, 0, iw)
        iy1 = cl((self._sy    - self._oy) / self._scale, 0, ih)
        ix2 = cl((event.x - self._ox) / self._scale, 0, iw)
        iy2 = cl((event.y - self._oy) / self._scale, 0, ih)
        if abs(ix2 - ix1) < 5 or abs(iy2 - iy1) < 5:
            self._st_var.set("Kutu çok küçük, tekrar deneyin.")
            return
        if ix2 < ix1: ix1, ix2 = ix2, ix1
        if iy2 < iy1: iy1, iy2 = iy2, iy1
        cid = self._sel_cid.get()
        self.label_entries.append([cid, (ix1+ix2)/2/iw, (iy1+iy2)/2/ih,
                                    (ix2-ix1)/iw, (iy2-iy1)/ih])
        name = self.class_names.get(cid, f"#{cid}")
        self._st_var.set(f"Eklendi → [{cid}] {name}  //  Toplam: {len(self.label_entries)}")
        self._render()

    def _undo_last(self):
        if self.label_entries:
            self.label_entries.pop()
            self._st_var.set(f"Geri alındı. Kalan: {len(self.label_entries)}")
            self._render()

    def _apply(self):
        prev = len(self.app.label_entries)
        self.app._push_undo()
        self.app.label_entries = self.label_entries
        self.app._commit_labels()
        self.app._populate_label_entries()
        self.app._refresh_images()
        added = len(self.label_entries) - prev
        self.app.log.log(f"{added} manuel BBox eklendi.", "action")
        self.destroy()


# ── LogManager ────────────────────────────────────────────────────────────────

class LogManager:

    def __init__(self, app: "LabelForgeApp"):
        self.app      = app
        self.entries: list[tuple[str, str]] = []
        self._toast_job = None

    def log(self, msg: str, level: str = "info"):
        self.entries.append((level, msg))
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        t = self.app._log_text
        t.configure(state="normal")
        t.insert(tk.END, line, level)
        t.see(tk.END)
        t.configure(state="disabled")
        if not self.app._log_open:
            self._show_toast(msg, level)

    def _show_toast(self, msg: str, level: str):
        if self._toast_job:
            try:
                self.app.after_cancel(self._toast_job)
            except Exception:
                pass
        color = LOG_COLORS.get(level, T.TX1)
        # Truncate long messages
        display = msg if len(msg) <= 55 else msg[:52] + "..."
        self.app._toast_lbl.configure(text=f"  {display}  ", fg=color)
        self.app._toast_bar.lift()
        self.app._toast_bar.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)
        self._toast_job = self.app.after(5000, self._hide_toast)

    def _hide_toast(self):
        self.app._toast_bar.place_forget()
        self._toast_job = None


# ── Main Application ──────────────────────────────────────────────────────────

class LabelForgeApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1500x920")
        self.minsize(1100, 680)
        self.configure(fg_color=T.BG0)

        # Persistent
        self.dataset_root = tk.StringVar()
        self.img_dir_var  = tk.StringVar()
        self.lbl_dir_var  = tk.StringVar()
        self.classes_file = ""

        # Runtime
        self.image_files:      list[str]      = []
        self.selected_index:   int            = -1
        self.label_entries:    list[list]     = []
        self.class_names:      dict[int, str] = {}
        self.selected_indices: set[int]       = set()
        self.reviewed:         set[str]       = set()

        self._orig_pil: Optional[Image.Image] = None
        self.current_img_path = ""
        self.current_lbl_path = ""
        self._session_selected = ""
        self._orig_tk = None
        self._ann_tk  = None
        self._log_open = False

        self._undo_stack: list[list] = []
        self._redo_stack: list[list] = []

        self.load_session()
        self._build_ui()
        self.log = LogManager(self)
        self._bind_keys()

        if self.img_dir_var.get() and os.path.isdir(self.img_dir_var.get()):
            self.after(200, self.scan_directories)

    # ── Session ───────────────────────────────────────────────────────────────

    def load_session(self):
        try:
            with open(SESSION_FILE) as f:
                d = json.load(f)
            self.dataset_root.set(d.get("dataset_root", ""))
            self.img_dir_var.set(d.get("img_dir", ""))
            self.lbl_dir_var.set(d.get("lbl_dir", ""))
            self.classes_file = d.get("classes_file", "")
            self.class_names  = {int(k): v for k, v in d.get("class_names", {}).items()}
            self.reviewed     = set(d.get("reviewed", []))
            self._session_selected = d.get("selected_file", "")
        except Exception:
            pass

    def save_session(self):
        sel = (self.image_files[self.selected_index]
               if 0 <= self.selected_index < len(self.image_files) else "")
        try:
            with open(SESSION_FILE, "w") as f:
                json.dump({
                    "dataset_root": self.dataset_root.get(),
                    "img_dir":      self.img_dir_var.get(),
                    "lbl_dir":      self.lbl_dir_var.get(),
                    "classes_file": self.classes_file,
                    "class_names":  {str(k): v for k, v in self.class_names.items()},
                    "reviewed":     list(self.reviewed),
                    "selected_file": sel,
                }, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_content()
        self._build_log_panel()
        self._build_toast()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=T.BG1, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.pack_propagate(False)

        # Left: branding
        brand = tk.Frame(hdr, bg=T.BG1)
        brand.pack(side="left", padx=14, pady=8)
        tk.Label(brand, text="⚡ LABELFORGE", bg=T.BG1, fg=T.ACC,
                 font=("Courier", 16, "bold")).pack(side="left")
        tk.Label(brand, text="  //  YOLO DATASET EDITOR", bg=T.BG1, fg=T.TX3,
                 font=("Courier", 9)).pack(side="left", pady=4)

        tk.Frame(hdr, bg=T.BDR, width=1).pack(side="left", fill="y", padx=10, pady=10)

        # Dataset root
        self._mk_entry_group(hdr, "DATASET:", self.dataset_root, 20, self._sel_dataset_root)
        tk.Frame(hdr, bg=T.BDR, width=1).pack(side="left", fill="y", padx=6, pady=10)
        self._mk_entry_group(hdr, "GÖRSELLER:", self.img_dir_var, 16, self._sel_img_dir)
        self._mk_entry_group(hdr, "ETİKETLER:", self.lbl_dir_var, 16, self._sel_lbl_dir)

        ctk.CTkButton(hdr, text="TARA ▶", width=72, height=28,
                      fg_color=T.BG3, hover_color="#1e3020",
                      text_color=T.ACC, font=("Courier", 10, "bold"),
                      border_width=1, border_color=T.ACC,
                      corner_radius=3, command=self.scan_directories
                      ).pack(side="left", padx=(8, 4), pady=12)

    def _mk_entry_group(self, parent, label: str, var: tk.StringVar, w: int, cmd):
        tk.Label(parent, text=label, bg=T.BG1, fg=T.TX2,
                 font=("Courier", 8)).pack(side="left", padx=(4, 2))
        tk.Entry(parent, textvariable=var, bg=T.BG2, fg=T.TX1,
                 insertbackground=T.ACC, relief="flat",
                 font=("Courier", 9), width=w).pack(side="left", padx=(0, 2), ipady=3)
        ctk.CTkButton(parent, text="SEÇ", width=38, height=22,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.TX2, font=("Courier", 8),
                      corner_radius=3, command=cmd
                      ).pack(side="left", padx=(0, 6), pady=14)

    # ── Content ───────────────────────────────────────────────────────────────

    def _build_content(self):
        self._pw_outer = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                         sashwidth=5, bg=T.BDR, handlesize=0)
        self._pw_outer.grid(row=1, column=0, sticky="nsew")

        left = self._build_left()
        self._pw_outer.add(left, minsize=150, width=218, stretch="never")

        self._pw_inner = tk.PanedWindow(self._pw_outer, orient=tk.HORIZONTAL,
                                         sashwidth=5, bg=T.BDR, handlesize=0)
        self._pw_outer.add(self._pw_inner, stretch="always")

        self._pw_center = tk.PanedWindow(self._pw_inner, orient=tk.HORIZONTAL,
                                          sashwidth=4, bg=T.BDR, handlesize=0)
        self._pw_inner.add(self._pw_center, stretch="always")

        self._pw_center.add(self._build_img_panel("ORIGINAL", "image"), minsize=120, stretch="always")
        self._pw_center.add(self._build_img_panel("ANNOTATED", "label"), minsize=120, stretch="always")

        right = self._build_right()
        self._pw_inner.add(right, minsize=180, width=252, stretch="never")

    # ── Left Panel ────────────────────────────────────────────────────────────

    def _build_left(self) -> tk.Frame:
        left = tk.Frame(self._pw_outer, bg=T.BG1)

        # Image list header
        ih = tk.Frame(left, bg=T.BG0, height=28)
        ih.pack(fill="x")
        ih.pack_propagate(False)
        self._img_count_var = tk.StringVar(value="// GÖRSELLER (0)")
        tk.Label(ih, textvariable=self._img_count_var, bg=T.BG0, fg=T.ACC,
                 font=("Courier", 9, "bold")).pack(side="left", padx=8, pady=5)
        tk.Label(ih, text="2x: ✓", bg=T.BG0, fg=T.TX3,
                 font=("Courier", 7)).pack(side="right", padx=6, pady=5)

        # Listbox
        lf = tk.Frame(left, bg=T.BG1)
        lf.pack(fill="both", expand=True)
        self.img_listbox = tk.Listbox(
            lf, bg=T.BG1, fg=T.TX1,
            selectbackground=T.SEL, selectforeground=T.ACC,
            font=("Courier", 10), borderwidth=0, highlightthickness=0,
            activestyle="none", relief="flat"
        )
        self.img_listbox.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(lf, command=self.img_listbox.yview, bg=T.BG0, relief="flat", width=6)
        sb.pack(side="right", fill="y")
        self.img_listbox.configure(yscrollcommand=sb.set)
        self.img_listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.img_listbox.bind("<Double-Button-1>",  self._toggle_reviewed)

        # Divider
        tk.Frame(left, bg=T.BDR, height=1).pack(fill="x")

        # Class legend header
        ch = tk.Frame(left, bg=T.BG0, height=28)
        ch.pack(fill="x")
        ch.pack_propagate(False)
        tk.Label(ch, text="// SINIF ETİKETLERİ", bg=T.BG0, fg=T.ACC,
                 font=("Courier", 9, "bold")).pack(side="left", padx=8, pady=5)

        cls_wrap = tk.Frame(left, bg=T.BG1)
        cls_wrap.pack(fill="both", expand=True)
        self._cls_cv = tk.Canvas(cls_wrap, bg=T.BG1, highlightthickness=0)
        cls_sb = tk.Scrollbar(cls_wrap, command=self._cls_cv.yview, bg=T.BG0,
                               relief="flat", width=6)
        self._cls_inner = tk.Frame(self._cls_cv, bg=T.BG1)
        self._cls_cv.pack(side="left", fill="both", expand=True)
        cls_sb.pack(side="right", fill="y")
        self._cls_cv.configure(yscrollcommand=cls_sb.set)
        self._cls_cv.create_window((0, 0), window=self._cls_inner, anchor="nw")
        self._cls_inner.bind("<Configure>", lambda e: self._cls_cv.configure(
            scrollregion=self._cls_cv.bbox("all")))

        return left

    # ── Image Panel ───────────────────────────────────────────────────────────

    def _build_img_panel(self, title: str, target: str) -> tk.Frame:
        frame = tk.Frame(self._pw_center, bg=T.BG0)
        hdr   = tk.Frame(frame, bg=T.BG1, height=26)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text=f"// {title}", bg=T.BG1, fg=T.TX2,
                 font=("Courier", 8, "bold")).pack(side="left", padx=8, pady=4)

        ctk.CTkButton(hdr, text="⛶", width=26, height=20,
                      fg_color="transparent", hover_color=T.BG2,
                      text_color=T.TX2, font=("Arial", 12),
                      corner_radius=3,
                      command=lambda: self._open_fs(target)
                      ).pack(side="right", padx=2, pady=3)
        ctk.CTkButton(hdr, text="FINDER", width=52, height=18,
                      fg_color="transparent", hover_color=T.BG2,
                      text_color=T.TX3, font=("Courier", 7),
                      corner_radius=3,
                      command=lambda t=target: self.show_in_finder(t)
                      ).pack(side="right", padx=2, pady=4)

        cv = tk.Canvas(frame, bg=T.BG0, highlightthickness=0)
        cv.pack(fill="both", expand=True)
        if target == "image":
            self.orig_canvas = cv
            cv.bind("<Configure>", lambda e: self._refresh_images())
        else:
            self.ann_canvas = cv
            cv.bind("<Configure>", lambda e: self._refresh_images())
        return frame

    # ── Right Panel ───────────────────────────────────────────────────────────

    def _build_right(self) -> tk.Frame:
        right = tk.Frame(self._pw_inner, bg=T.BG1)

        # Header
        rh = tk.Frame(right, bg=T.BG0, height=28)
        rh.pack(fill="x")
        rh.pack_propagate(False)
        self._lbl_count_var = tk.StringVar(value="// LABEL İÇERİĞİ")
        tk.Label(rh, textvariable=self._lbl_count_var, bg=T.BG0, fg=T.ACC,
                 font=("Courier", 9, "bold")).pack(side="left", padx=8, pady=5)

        # Undo / Redo
        ur = tk.Frame(right, bg=T.BG1)
        ur.pack(fill="x", padx=5, pady=(5, 2))
        ur.grid_columnconfigure(0, weight=1)
        ur.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(ur, text="↩ GERİ AL", height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.TX1, font=("Courier", 8),
                      corner_radius=3, command=self.undo
                      ).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ctk.CTkButton(ur, text="YİNELE ↪", height=26,
                      fg_color=T.BG2, hover_color=T.BG3,
                      text_color=T.TX1, font=("Courier", 8),
                      corner_radius=3, command=self.redo
                      ).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        # Draw button
        ctk.CTkButton(right, text="✏  MANUEL BBOX ÇİZ", height=36,
                      fg_color=T.BG3, hover_color="#1e3020",
                      text_color=T.ACC, font=("Courier", 10, "bold"),
                      border_width=1, border_color=T.BDR,
                      corner_radius=3, command=self.open_draw_mode
                      ).pack(fill="x", padx=5, pady=(2, 5))

        # Label scroll area
        lbl_wrap = tk.Frame(right, bg=T.BG1)
        lbl_wrap.pack(fill="both", expand=True)
        self._lbl_cv = tk.Canvas(lbl_wrap, bg=T.BG1, highlightthickness=0)
        lbl_sb = tk.Scrollbar(lbl_wrap, command=self._lbl_cv.yview, bg=T.BG1,
                               troughcolor=T.BG0, activebackground=T.ACC,
                               relief="flat", width=10)
        self._lbl_inner = tk.Frame(self._lbl_cv, bg=T.BG1)
        self._lbl_cv.pack(side="left", fill="both", expand=True)
        lbl_sb.pack(side="right", fill="y")
        self._lbl_cv.configure(yscrollcommand=lbl_sb.set)
        self._lbl_cv.create_window((0, 0), window=self._lbl_inner, anchor="nw")
        self._lbl_inner.bind("<Configure>", lambda e: self._lbl_cv.configure(
            scrollregion=self._lbl_cv.bbox("all")))
        # Mousewheel scroll activates while cursor is inside the label panel
        lbl_wrap.bind("<Enter>", lambda e: self._lbl_cv.bind_all("<MouseWheel>", self._lbl_mousewheel))
        lbl_wrap.bind("<Leave>", lambda e: self._lbl_cv.unbind_all("<MouseWheel>"))

        return right

    def _lbl_mousewheel(self, event):
        step = -1 if event.delta > 0 else 1
        self._lbl_cv.yview_scroll(step, "units")

    # ── Floating Log Panel (bottom-right) ─────────────────────────────────────

    def _build_log_panel(self):
        # Container placed bottom-right
        self._log_container = tk.Frame(self, bg=T.BG0)

        # Toggle button row
        toggle_row = tk.Frame(self._log_container, bg=T.BG0)
        toggle_row.pack(fill="x")

        self._log_btn = tk.Label(
            toggle_row,
            text="▲ LOG", bg=T.BG0, fg=T.TX3,
            font=("Courier", 8, "bold"), cursor="hand2",
            padx=10, pady=4
        )
        self._log_btn.pack(side="right")
        self._log_btn.bind("<Button-1>", lambda e: self._toggle_log())

        ctk.CTkButton(toggle_row, text="CLR", width=34, height=18,
                      fg_color="transparent", hover_color=T.BG2,
                      text_color=T.TX3, font=("Courier", 7),
                      corner_radius=2, command=self._clear_log
                      ).pack(side="right", padx=2, pady=2)

        # Log body (hidden initially)
        self._log_body = tk.Frame(self._log_container, bg=T.BG0,
                                   bd=1, relief="flat",
                                   highlightthickness=1,
                                   highlightbackground=T.BDR)
        self._log_text = tk.Text(
            self._log_body, bg=T.BG0, fg=T.TX3,
            font=("Courier", 8), relief="flat", bd=0,
            state="disabled", height=7, width=52, wrap="word",
            highlightthickness=0
        )
        self._log_text.pack(fill="both", padx=6, pady=4)
        for level, color in LOG_COLORS.items():
            self._log_text.tag_configure(level, foreground=color)

        # Place the container
        self._log_container.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

    def _toggle_log(self):
        self._log_open = not self._log_open
        if self._log_open:
            self._log_body.pack(fill="x", before=self._log_btn.master)
            self._log_btn.configure(text="▼ LOG")
        else:
            self._log_body.pack_forget()
            self._log_btn.configure(text="▲ LOG")

    def _clear_log(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state="disabled")

    # ── Toast ─────────────────────────────────────────────────────────────────

    def _build_toast(self):
        self._toast_bar = tk.Frame(self, bg=T.BG2,
                                    highlightthickness=1,
                                    highlightbackground=T.BDR)
        self._toast_lbl = tk.Label(self._toast_bar, text="", bg=T.BG2,
                                    fg=T.TX1, font=("Courier", 9),
                                    padx=12, pady=5)
        self._toast_lbl.pack()
        # Initially hidden (don't place it yet)

    # ── Key Bindings ──────────────────────────────────────────────────────────

    def _bind_keys(self):
        self.bind("<Up>",   self._key_up)
        self.bind("<Down>", self._key_down)
        self.bind("<Control-z>",       lambda e: self.undo())
        self.bind("<Command-z>",       lambda e: self.undo())
        self.bind("<Control-y>",       lambda e: self.redo())
        self.bind("<Command-Shift-z>", lambda e: self.redo())
        self.img_listbox.bind("<Up>",   self._key_up)
        self.img_listbox.bind("<Down>", self._key_down)
        if IS_MAC:
            self.bind("<Command-BackSpace>", self._delete_selected_key)
        else:
            self.bind("<Delete>", self._delete_selected_key)

    def _delete_selected_key(self, event=None):
        if self.selected_indices:
            self._delete_entries(list(self.selected_indices))

    # ── Directory Selection ───────────────────────────────────────────────────

    def _sel_dataset_root(self):
        p = filedialog.askdirectory(title="Dataset Ana Klasörü (classes.txt içeren)")
        if not p:
            return
        self.dataset_root.set(p)
        img = os.path.join(p, "images")
        lbl = os.path.join(p, "labels")
        cls = os.path.join(p, "classes.txt")
        if os.path.isdir(img): self.img_dir_var.set(img)
        if os.path.isdir(lbl): self.lbl_dir_var.set(lbl)
        self.classes_file = cls
        if os.path.exists(cls):
            names = read_classes_txt(cls)
            if names:
                self.class_names = names
        self.save_session()
        self.log.log(f"Dataset: {p}", "info")

    def _sel_img_dir(self):
        p = filedialog.askdirectory(title="Görsel Klasörü")
        if p:
            self.img_dir_var.set(p)
            self.save_session()

    def _sel_lbl_dir(self):
        p = filedialog.askdirectory(title="Label Klasörü")
        if p:
            self.lbl_dir_var.set(p)
            self.save_session()

    # ── Scanning ──────────────────────────────────────────────────────────────

    def scan_directories(self):
        img_d = self.img_dir_var.get()
        if not img_d or not os.path.isdir(img_d):
            messagebox.showwarning("Uyarı", "Geçerli bir görsel klasörü seçin.", parent=self)
            return
        files = sorted(f for f in os.listdir(img_d)
                       if os.path.splitext(f)[1].lower() in IMG_EXT)
        self.image_files = files
        self.img_listbox.delete(0, tk.END)
        for f in files:
            self.img_listbox.insert(tk.END, ("✓ " if f in self.reviewed else "  ") + f)
        self._img_count_var.set(f"// GÖRSELLER ({len(files)})")

        lbl_d = self.lbl_dir_var.get()
        if lbl_d and os.path.isdir(lbl_d):
            self._scan_class_ids(lbl_d)
        if not self.class_names and self.classes_file and os.path.exists(self.classes_file):
            self.class_names = read_classes_txt(self.classes_file)
        self._populate_class_legend()

        restore = self._session_selected
        idx = files.index(restore) if restore in files else (0 if files else -1)
        if idx >= 0:
            self.img_listbox.selection_set(idx)
            self.img_listbox.see(idx)
            self._select_image(idx)

        self.log.log(f"{len(files)} görsel tarandı.", "success")
        self.save_session()

    def _scan_class_ids(self, lbl_d: str):
        for fname in os.listdir(lbl_d):
            if not fname.endswith(".txt"):
                continue
            try:
                with open(os.path.join(lbl_d, fname)) as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            cid = int(parts[0])
                            if cid not in self.class_names:
                                self.class_names[cid] = f"Sınıf {cid}"
            except Exception:
                pass
        self.save_session()

    # ── Image List ────────────────────────────────────────────────────────────

    def _on_list_select(self, event):
        sel = self.img_listbox.curselection()
        if sel:
            self._select_image(sel[0])

    def _toggle_reviewed(self, event=None):
        if not (0 <= self.selected_index < len(self.image_files)):
            return
        fname = self.image_files[self.selected_index]
        if fname in self.reviewed:
            self.reviewed.discard(fname)
            prefix = "  "
            self.log.log(f"İnceleme işareti kaldırıldı: {fname}", "info")
        else:
            self.reviewed.add(fname)
            prefix = "✓ "
            self.log.log(f"İncelendi: {fname}", "success")
        self.img_listbox.delete(self.selected_index)
        self.img_listbox.insert(self.selected_index, prefix + fname)
        self.img_listbox.selection_set(self.selected_index)
        self.save_session()

    def _select_image(self, index: int):
        if not (0 <= index < len(self.image_files)):
            return
        self.selected_index = index
        self.selected_indices.clear()
        fname    = self.image_files[index]
        img_path = os.path.join(self.img_dir_var.get(), fname)
        base     = os.path.splitext(fname)[0]
        lbl_d    = self.lbl_dir_var.get()
        lbl_path = os.path.join(lbl_d, base + ".txt") if lbl_d else ""
        self.current_img_path = img_path
        self.current_lbl_path = (lbl_path if lbl_path and os.path.exists(lbl_path) else "")
        self._load_image(img_path)
        self._load_labels(self.current_lbl_path)
        self._refresh_images()
        self._populate_label_entries()
        self.save_session()

    def _key_up(self, event):
        if self.selected_index > 0:
            ni = self.selected_index - 1
            self.img_listbox.selection_clear(0, tk.END)
            self.img_listbox.selection_set(ni)
            self.img_listbox.see(ni)
            self._select_image(ni)

    def _key_down(self, event):
        if self.selected_index < len(self.image_files) - 1:
            ni = self.selected_index + 1
            self.img_listbox.selection_clear(0, tk.END)
            self.img_listbox.selection_set(ni)
            self.img_listbox.see(ni)
            self._select_image(ni)

    # ── Image Display ─────────────────────────────────────────────────────────

    def _load_image(self, path: str):
        try:
            self._orig_pil = Image.open(path).convert("RGB")
        except Exception:
            self._orig_pil = None

    def _load_labels(self, path: str):
        self.label_entries = []
        self._undo_stack.clear()
        self._redo_stack.clear()
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            self.label_entries.append(
                                [int(parts[0])] + [float(x) for x in parts[1:5]])
            except Exception:
                pass

    def _put_on_canvas(self, canvas: tk.Canvas, pil_img, attr: str):
        cw, ch = canvas.winfo_width(), canvas.winfo_height()
        if cw < 10:
            return
        if pil_img is None:
            canvas.delete("all")
            canvas.create_text(cw // 2, ch // 2, text="—", fill=T.TX3, font=("Courier", 16))
            return
        resized = fit_pil(pil_img, cw, ch)
        tk_img  = ImageTk.PhotoImage(resized)
        setattr(self, attr, tk_img)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, anchor="center", image=tk_img)

    def _refresh_images(self):
        self._put_on_canvas(self.orig_canvas, self._orig_pil, "_orig_tk")
        ann = draw_boxes(self._orig_pil, self.label_entries,
                         self.class_names, self.selected_indices) if self._orig_pil else None
        self._put_on_canvas(self.ann_canvas, ann, "_ann_tk")

    # ── Label Entries ─────────────────────────────────────────────────────────

    def _populate_label_entries(self):
        for w in self._lbl_inner.winfo_children():
            w.destroy()
        n = len(self.label_entries)
        self._lbl_count_var.set(f"// LABEL İÇERİĞİ  ({n})")
        if n == 0:
            tk.Label(self._lbl_inner, text="—  boş  —", bg=T.BG1, fg=T.TX3,
                     font=("Courier", 9)).pack(pady=14)
            return

        for i, entry in enumerate(self.label_entries):
            cid    = int(entry[0])
            cx, cy, bw, bh = float(entry[1]), float(entry[2]), float(entry[3]), float(entry[4])
            color  = get_color(cid)
            name   = self.class_names.get(cid, f"#{cid}")
            sel    = i in self.selected_indices
            bg     = T.SEL if sel else T.BG2
            border = T.HLBX if sel else T.BDR

            card = tk.Frame(self._lbl_inner, bg=bg, highlightthickness=1,
                            highlightbackground=border)
            card.pack(fill="x", padx=4, pady=2)
            card.bind("<Button-1>", lambda e, idx=i: self._click_entry(idx, e))

            row = tk.Frame(card, bg=bg)
            row.pack(fill="x", padx=5, pady=3)

            dot = tk.Canvas(row, width=9, height=9, bg=bg, highlightthickness=0)
            dot.pack(side="left", padx=(0, 4))
            dot.create_oval(1, 1, 8, 8, fill=color, outline="")
            dot.bind("<Button-1>", lambda e, idx=i: self._click_entry(idx, e))

            tk.Label(row, text=f"[{cid}] {name}", bg=bg,
                     fg=T.HLBX if sel else color,
                     font=("Courier", 9, "bold")).pack(side="left", padx=(0, 4))

            tk.Label(row, text=f"cx{cx:.3f} cy{cy:.3f} {bw:.3f}×{bh:.3f}",
                     bg=bg, fg=T.TX3, font=("Courier", 7)
                     ).pack(side="left", fill="x", expand=True)

            ctk.CTkButton(row, text="✕", width=22, height=20,
                          fg_color="transparent", hover_color="#3a0808",
                          text_color=T.TX3, font=("Arial", 10),
                          corner_radius=3,
                          command=lambda idx=i: self._delete_entry(idx)
                          ).pack(side="right", padx=1)

        self._lbl_inner.update_idletasks()
        self._lbl_cv.configure(scrollregion=self._lbl_cv.bbox("all"))

    def _click_entry(self, idx: int, event):
        shift = bool(event.state & 0x0001)
        if shift:
            self.selected_indices.discard(idx) if idx in self.selected_indices \
                else self.selected_indices.add(idx)
        else:
            self.selected_indices = set() if self.selected_indices == {idx} else {idx}
        self._populate_label_entries()
        self._refresh_images()

    def _delete_entry(self, index: int):
        self._delete_entries([index])

    def _delete_entries(self, indices: list):
        if not indices:
            return
        n = len(indices)
        details = "\n".join(
            f"  [{int(self.label_entries[i][0])}] "
            f"{self.class_names.get(int(self.label_entries[i][0]), '?')}"
            for i in sorted(indices) if i < len(self.label_entries)
        )
        if not messagebox.askyesno("Silme Onayı",
                                    f"{n} BBox silinsin mi?\n{details}\n\nGeri alınabilir.",
                                    parent=self):
            return
        self._push_undo()
        s = set(indices)
        self.label_entries = [e for i, e in enumerate(self.label_entries) if i not in s]
        self.selected_indices.clear()
        self._commit_labels()
        self._populate_label_entries()
        self._refresh_images()
        self.log.log(f"{n} BBox silindi.", "action")

    # ── Class Legend ──────────────────────────────────────────────────────────

    def _populate_class_legend(self):
        for w in self._cls_inner.winfo_children():
            w.destroy()
        if not self.class_names:
            tk.Label(self._cls_inner, text="—  boş  —", bg=T.BG1, fg=T.TX3,
                     font=("Courier", 8)).pack(pady=8)
            return
        for cid in sorted(self.class_names.keys()):
            name  = self.class_names[cid]
            color = get_color(cid)
            row   = tk.Frame(self._cls_inner, bg=T.BG1)
            row.pack(fill="x", padx=2, pady=1)
            dot = tk.Canvas(row, width=9, height=9, bg=T.BG1, highlightthickness=0)
            dot.pack(side="left", padx=(4, 3), pady=2)
            dot.create_oval(1, 1, 8, 8, fill=color, outline="")
            tk.Label(row, text=f"{cid}: {name}", bg=T.BG1, fg=T.TX1,
                     font=("Courier", 9), anchor="w"
                     ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="⋯", width=22, height=18,
                          fg_color="transparent", hover_color=T.BG2,
                          text_color=T.TX2, font=("Arial", 10),
                          corner_radius=2,
                          command=lambda c=cid: self._class_menu(c)
                          ).pack(side="right", padx=2)
        self._cls_inner.update_idletasks()
        self._cls_cv.configure(scrollregion=self._cls_cv.bbox("all"))

    def _class_menu(self, cid: int):
        menu = tk.Menu(self, tearoff=0, bg=T.BG2, fg=T.TX1,
                       activebackground=T.SEL, activeforeground=T.ACC,
                       font=("Courier", 10))
        menu.add_command(label="  ✏  Yeniden Adlandır",
                          command=lambda: self._rename_class(cid))
        menu.add_separator()
        menu.add_command(label="  ✕  Bu görseldeki girdileri sil",
                          command=lambda: self._delete_class_entries_current(cid))
        menu.add_command(label="  🗑  Sınıfı tamamen sil (classes.txt)",
                          command=lambda: self._remove_class_definition(cid))
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _rename_class(self, cid: int):
        current = self.class_names.get(cid, f"Sınıf {cid}")
        new_name = simpledialog.askstring("Yeniden Adlandır",
                                           f"Sınıf {cid} için yeni isim:",
                                           initialvalue=current, parent=self)
        if not (new_name and new_name.strip()):
            return
        old = self.class_names.get(cid, "")
        self.class_names[cid] = new_name.strip()
        if self.classes_file:
            write_classes_txt(self.classes_file, self.class_names)
        self.save_session()
        self._populate_class_legend()
        self._populate_label_entries()
        self._refresh_images()
        self.log.log(f"Sınıf {cid}: '{old}' → '{new_name.strip()}'", "action")

    def _delete_class_entries_current(self, cid: int):
        count = sum(1 for e in self.label_entries if int(e[0]) == cid)
        if count == 0:
            messagebox.showinfo("Bilgi", f"Sınıf {cid}: Bu görselde giriş yok.", parent=self)
            return
        name = self.class_names.get(cid, f"Sınıf {cid}")
        if not messagebox.askyesno("Silme Onayı",
                                    f"'{name}' sınıfına ait {count} giriş silinsin mi?\n"
                                    f"Geri alınabilir.", parent=self):
            return
        self._push_undo()
        self.label_entries = [e for e in self.label_entries if int(e[0]) != cid]
        self.selected_indices.clear()
        self._commit_labels()
        self._populate_label_entries()
        self._refresh_images()
        self.log.log(f"{count} giriş silindi (Sınıf {cid}: {name}).", "action")

    def _remove_class_definition(self, cid: int):
        name = self.class_names.get(cid, f"Sınıf {cid}")
        if not messagebox.askyesno("Sınıf Tanımını Sil",
                                    f"Sınıf {cid} ('{name}') classes.txt'den silinsin mi?\n"
                                    f"Bu işlem bu görseldeki girdileri silmez, sadece ismi kaldırır.",
                                    parent=self):
            return
        del self.class_names[cid]
        if self.classes_file:
            write_classes_txt(self.classes_file, self.class_names)
        self.save_session()
        self._populate_class_legend()
        self._populate_label_entries()
        self._refresh_images()
        self.log.log(f"Sınıf {cid} ('{name}') classes.txt'den kaldırıldı.", "warning")

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    def _push_undo(self):
        self._undo_stack.append([list(e) for e in self.label_entries])
        self._redo_stack.clear()
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)

    def undo(self):
        if not self._undo_stack:
            if hasattr(self, "log"):
                self.log.log("Geri alınacak işlem yok.", "warning")
            return
        self._redo_stack.append([list(e) for e in self.label_entries])
        self.label_entries = self._undo_stack.pop()
        self.selected_indices.clear()
        self._commit_labels()
        self._populate_label_entries()
        self._refresh_images()
        self.log.log("Geri alındı.", "action")

    def redo(self):
        if not self._redo_stack:
            if hasattr(self, "log"):
                self.log.log("Yinelenecek işlem yok.", "warning")
            return
        self._undo_stack.append([list(e) for e in self.label_entries])
        self.label_entries = self._redo_stack.pop()
        self.selected_indices.clear()
        self._commit_labels()
        self._populate_label_entries()
        self._refresh_images()
        self.log.log("Yinelendi.", "action")

    # ── Label File I/O ────────────────────────────────────────────────────────

    def _commit_labels(self):
        if not self.current_lbl_path:
            if not (self.lbl_dir_var.get() and 0 <= self.selected_index < len(self.image_files)):
                messagebox.showwarning("Uyarı", "Label klasörü belirlenmedi.", parent=self)
                return
            base = os.path.splitext(self.image_files[self.selected_index])[0]
            self.current_lbl_path = os.path.join(self.lbl_dir_var.get(), base + ".txt")
        parent = os.path.dirname(self.current_lbl_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.current_lbl_path, "w") as f:
            for entry in self.label_entries:
                cid, cx, cy, bw, bh = int(entry[0]), *[float(v) for v in entry[1:5]]
                f.write(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

    # ── Finder ────────────────────────────────────────────────────────────────

    def show_in_finder(self, target: str):
        if target == "image" and os.path.exists(self.current_img_path):
            subprocess.run(["open", "-R", self.current_img_path])
        elif target == "label":
            if self.current_lbl_path and os.path.exists(self.current_lbl_path):
                subprocess.run(["open", "-R", self.current_lbl_path])
            elif os.path.isdir(self.lbl_dir_var.get()):
                subprocess.run(["open", self.lbl_dir_var.get()])
            else:
                self.log.log("Label dosyası bulunamadı.", "error")

    # ── Fullscreen & Draw ─────────────────────────────────────────────────────

    def _open_fs(self, target: str):
        if not self._orig_pil:
            self.log.log("Önce bir görsel seçin.", "warning")
            return
        FullscreenWindow(self, "original" if target == "image" else "annotated")

    def open_draw_mode(self):
        if not self._orig_pil:
            self.log.log("Önce bir görsel seçin.", "warning")
            return
        if not self.class_names:
            self.class_names[0] = "Sınıf 0"
        DrawModeWindow(self)


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = LabelForgeApp()
    app.mainloop()
