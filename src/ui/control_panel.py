from __future__ import annotations

import base64
import sys
import threading
import time
from pathlib import Path

from ..config import Config
from .gesture_guide import mode_list
from .status_model import view_model

W, H = 100, 150          # kích thước cửa sổ trạng thái
BG, FG, MUTED = "#111827", "#f9fafb", "#cbd5e1"

# ===== Cửa sổ điều khiển: hai trạng thái (thường / phóng to), nền vẽ trên một Canvas =====
FONT = "El Messiri Regular"                
FONT_BOLD = "El Messiri Bold"      
FONT_ITALIC = "El Messiri Italic"
WIN_BG = "#eef2f7"                        # màu nền khi KHÔNG có ảnh nền
TXT, TXT_MUTED, TXT_LINK = "#111827", "#4b5563", "#2563eb"    # màu chữ vẽ thẳng lên nền: đổi nếu ảnh nền tối
NORMAL_SIZE = (440, 540)                  # cửa sổ thường, chưa bật hướng dẫn  -> ảnh nền bg_normal.png
GUIDE_SIZE = (880, 640)                   # cửa sổ thường, đang bật hướng dẫn  -> ảnh nền bg_guide.png
BTN_W, BTN_H = 340, 54                    # cỡ nút ở trạng thái thường; phóng to nhân với MAX_SCALE (476 x 76)
MARGIN = 50                                # cách viền trên/trái của tiêu đề + nút ở cỡ thường và khi bật hướng dẫn
HOVER_SHIFT = 5                           # nút nhích lên trái bấy nhiêu px khi hover (nhân theo tỉ lệ phóng to)
BTN_PAD = 20                              # chữ trên nút cách mép trái bấy nhiêu px (nhân theo tỉ lệ phóng to)
SMALL_H = 36 
MAX_SCALE = 1.4
ASSETS = Path(__file__).parent / "assets"
BG_DIR = ASSETS / "backgrounds"            # bg_normal.png | bg_guide.png | bg_max.png | background.png (dùng chung)
BTN_DIR = ASSETS / "buttons"              # <tên>.png, <tên>_hover.png, <tên>_down.png, <tên>_off.png
TITLE_IMG = ASSETS / "label.png"          # ảnh tiêu đề (không có thì dùng chữ)
FONT_DIR = ASSETS / "fonts"

STR = {
    "vi": {"start": "Bắt đầu  (S)", "stop": "Dừng  (S)", "stopping": "Đang dừng...",
           "tap": "Chế độ: TẬP (không gửi phím) (M)",
           "real": "Chế độ: GỬI PHÍM THẬT (M)",
           "policy": "Bộ lọc lệnh: {tag}  (P)\n{second}", "policy_locked": "Dừng để đổi bộ lọc",
           "guide_off": "Hướng dẫn (G) ▶", "guide_on": "Hướng dẫn (G) ◀",
           "cam_on": "Camera: BẬT  (C)", "cam_off": "Camera: TẮT  (C)", "lang": "Tiếng Việt",
           "idle": "Chưa chạy", "starting": "Đang khởi động camera...", "stopped": "Đã dừng", "error": "Lỗi: {err}",
           "running": "Đang chạy · {fps:.0f} khung/s · {seen}", "hand": "thấy tay", "nohand": "chưa thấy tay",
           "title": "Hệ thống điều khiển slide bằng cử chỉ tay",
           "err_keys_t": "Không gửi được phím", "err_keys": "Thiếu thư viện pynput ({e}).\nCài bằng: pip install pynput",
           "ask_real_t": "Chuyển sang GỬI PHÍM THẬT", "ask_real": "Từ giờ cử chỉ sẽ gửi phím thật vào cửa sổ đang được chọn. Tiếp tục?",
           "err_mode_t": "Không đổi được chế độ"}, "title": "Hệ thống điều khiển slide bằng cử chỉ tay",
    "en": {"start": "Start  (S)", "stop": "Stop  (S)", "stopping": "Stopping...",
           "tap": "Mode: PRACTICE (no keys) (M)", "real": "Mode: LIVE (sends keys) (M)",
           "policy": "Command filter: {tag}  (P)\n{second}", "policy_locked": "Stop to change filter",
           "guide_off": "Guide (G) ▶", "guide_on": "Guide (G) ◀",
           "cam_on": "Camera: ON  (C)", "cam_off": "Camera: OFF  (C)", "lang": "English",
           "idle": "Not running", "starting": "Starting camera...", "stopped": "Stopped", "error": "Error: {err}",
           "running": "Running · {fps:.0f} fps · {seen}", "hand": "hand detected", "nohand": "no hand",
           "title": "Hand-Gesture Interaction Slideshow System",
           "err_keys_t": "Cannot send keys", "err_keys": "Missing library pynput ({e}).\nInstall with: pip install pynput",
           "ask_real_t": "Switch to LIVE mode", "ask_real": "Gestures will now send real keys to the selected window. Continue?",
           "err_mode_t": "Cannot change mode"}, "title": "Hand-Gesture Interaction Slideshow System",
}

def load_bundled_fonts():
    """Windows: đăng ký các .ttf/.otf trong assets/fonts cho riêng tiến trình này (không cài vào máy). Hệ khác: bỏ qua, Tk dùng font hệ thống."""
    if sys.platform != "win32" or not FONT_DIR.exists():
        return
    import ctypes
    for f in list(FONT_DIR.glob("*.ttf")) + list(FONT_DIR.glob("*.otf")):
        try:
            ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)      # 0x10 = FR_PRIVATE
        except Exception:
            pass

def make_photo(tk, path, size, mode="stretch"):
    """Đọc PNG/JPG thành PhotoImage đúng `size` (rộng, cao). mode "cover": phủ kín rồi cắt giữa (nền); "stretch": kéo cho vừa (nút).
    Dùng OpenCV (đã có trong requirements) để đổi cỡ; không có thì dùng ảnh nguyên bản. Lỗi đọc ảnh -> None (giao diện quay về màu đặc)."""
    try:
        import numpy as np
        try:
            import cv2
        except ImportError:
            return tk.PhotoImage(file=str(path))
        img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)   # đọc được cả đường dẫn có dấu
        if img is None:
            return None
        h, w = img.shape[:2]
        tw, th = size
        if mode == "cover":
            k = max(tw / w, th / h)
            nw, nh = max(tw, round(w * k)), max(th, round(h * k))
            if (nw, nh) != (w, h):
                img = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
            x, y = (nw - tw) // 2, (nh - th) // 2
            img = img[y:y + th, x:x + tw]
        elif (w, h) != (tw, th):
            img = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA if tw * th < w * h else cv2.INTER_CUBIC)
        ok, buf = cv2.imencode(".png", img)
        return tk.PhotoImage(data=base64.b64encode(buf.tobytes())) if ok else None
    except Exception:
        return None

def _shade(color, k=0.82):
    """Làm tối màu #rrggbb (dùng cho nút khi bấm)."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * k), int(g * k), int(b * k))

class CanvasButton:
    """Nút vẽ trên Canvas: không có ô nền riêng nên ảnh nền nhìn xuyên qua được. Có ảnh trong assets/buttons/ thì dùng ảnh,
    không thì vẽ hình chữ nhật màu. API giống tk.Button ở những chỗ ControlApp dùng: config(text, bg, fg, state, skin), ["state"].
    Các phần tử (khung, ảnh, chữ) tạo một lần rồi chỉ cập nhật: xóa/tạo lại dưới con trỏ sẽ làm Tk bắn Enter/Leave liên tục."""


    def __init__(self, app, command=None, **opts):
        self.app, self.command = app, command
        self.opts = {"text": "", "bg": "#e5e7eb", "activebackground": "#d1d5db", "fg": TXT, "state": "normal", "skin": None, "align": "left"}
        self.opts.update(opts)
        self.x = self.y = 0
        self.w, self.h = BTN_W, BTN_H
        self.hover = self.down = False
        self.tag = f"cbtn{id(self)}"
        cv = app.cv
        self.s_item = cv.create_rectangle(0, 0, 1, 1, fill="black", width=0, state="hidden", tags=self.tag)   # bóng đen (tạo trước để nằm dưới nút)
        self.r_item = cv.create_rectangle(0, 0, 1, 1, width=0, tags=self.tag)
        self.i_item = cv.create_image(0, 0, anchor="nw", state="hidden", tags=self.tag)
        self.t_item = cv.create_text(0, 0, justify="center", tags=self.tag)
        app.btns.append(self)                  # hover/bấm do ControlApp xử lý theo tọa độ chuột (không gắn sự kiện lên từng phần tử)
        self.draw()

    # --- giống tk.Button ---
    def config(self, **kw):
        self.opts.update({k: v for k, v in kw.items() if k in self.opts})
        self.draw()

    configure = config

    def cget(self, key):
        return self.opts[key]

    __getitem__ = cget

    def invoke(self):
        if self.opts["state"] != "disabled" and self.command:
            self.command()

    # --- vị trí và vẽ ---
    def place(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.draw()

    def contains(self, px, py):
        """Con trỏ có đang ở trên nút không: gồm cả vị trí gốc (bóng đen) và vị trí nhích lên khi hover (để con trỏ ở mép không làm nút nhảy qua lại)."""
        off = round(HOVER_SHIFT * self.app.scale) if self.hover else 0
        return self.x - off <= px <= self.x + self.w and self.y - off <= py <= self.y + self.h

    def _state(self):
        if self.opts["state"] == "disabled":
            return "off"
        return "down" if self.down and self.hover else "hover" if self.hover else ""

    def draw(self):
        cv, o, st = self.app.cv, self.opts, self._state()
        off = round(HOVER_SHIFT * self.app.scale) if st in ("hover", "down") else 0
        bx, by = self.x - off, self.y - off                      # vị trí vẽ của nút (nhích lên trái khi hover)
        cv.coords(self.s_item, self.x, self.y, self.x + self.w, self.y + self.h)
        cv.itemconfig(self.s_item, state="normal" if off else "hidden")   # bóng đen đứng yên ở vị trí gốc, lộ ra khi nút nhích lên
        if o["align"] == "center":
            cv.coords(self.t_item, bx + self.w // 2, by + self.h // 2)
            anchor, just = "center", "center"
        else:
            cv.coords(self.t_item, bx + round(BTN_PAD * self.app.scale), by + self.h // 2)
            anchor, just = "w", "left"
        cv.itemconfig(self.t_item, text=o["text"], anchor=anchor, justify=just,
                      fill="#6b7280" if st == "off" else o["fg"],
                      font=self.app.fonts["btn_s" if o["align"] == "center" else "btn"])
        img = self.app.skin_image(o["skin"], st, (self.w, self.h))
        if img is not None:
            cv.coords(self.i_item, bx, by)
            cv.itemconfig(self.i_item, image=img, state="normal")
            cv.itemconfig(self.r_item, state="hidden")
        else:
            if st == "off":
                fill = "#d1d5db"
            elif st == "down":
                fill = _shade(o["activebackground"])
            elif st == "hover":
                fill = o["activebackground"]
            else:
                fill = o["bg"]
            cv.coords(self.r_item, bx, by, bx + self.w, by + self.h)
            cv.itemconfig(self.r_item, fill=fill, state="normal")
            cv.itemconfig(self.i_item, state="hidden")

    def _enter(self, _e):
        self.hover = True
        self.app.cv.config(cursor="hand2" if self.opts["state"] != "disabled" else "")
        self.draw()

    def _leave(self, _e):
        self.hover = self.down = False
        self.app.cv.config(cursor="")
        self.draw()

    def _press(self, _e):
        if self.opts["state"] != "disabled":
            self.down = True
            self.draw()

    def _release(self, _e):
        fire = self.down and self.hover
        self.down = False
        self.draw()
        if fire:
            self.invoke()


class CanvasLink(CanvasButton):
    """Dòng chữ bấm được (không khung): vẽ thẳng lên nền."""

    def __init__(self, app, command=None, **opts):
        super().__init__(app, command, **opts)
        app.cv.itemconfig(self.r_item, state="hidden")
        app.cv.itemconfig(self.i_item, state="hidden")

    def draw(self):
        cv, o = self.app.cv, self.opts
        cv.itemconfig(self.r_item, state="hidden")
        cv.itemconfig(self.i_item, state="hidden")
        cv.coords(self.t_item, self.x, self.y + self.h // 2)
        cv.itemconfig(self.t_item, text=o["text"], anchor="w", fill=o["fg"],
                      font=FONT if self.hover else self.app.fonts["small"])


class CanvasText:
    """Dòng chữ không khung, vẽ thẳng lên nền."""

    def __init__(self, app, text="", fg=TXT, font=FONT, anchor="nw"):
        self.app, self.fontkey = app, font
        self.id = app.cv.create_text(0, 0, text=text, fill=fg, anchor=anchor, font=app.fonts[font], justify="left")

    def config(self, **kw):
        if "text" in kw:
            self.app.cv.itemconfig(self.id, text=kw["text"])
        if "fg" in kw:
            self.app.cv.itemconfig(self.id, fill=kw["fg"])

    def place(self, x, y, width=0):
        self.app.cv.coords(self.id, x, y)
        self.app.cv.itemconfig(self.id, width=width, font=self.app.fonts[self.fontkey])


class CanvasCheck:
    """Ô tích + chữ, vẽ trên Canvas."""

    def __init__(self, app, var, text, command):
        self.app, self.var, self.text, self.command = app, var, text, command
        self.x = self.y = 0
        self.tag = f"ccheck{id(self)}"
        app.cv.tag_bind(self.tag, "<ButtonRelease-1>", lambda _e: self.toggle())
        app.cv.tag_bind(self.tag, "<Enter>", lambda _e: app.cv.config(cursor="hand2"))
        app.cv.tag_bind(self.tag, "<Leave>", lambda _e: app.cv.config(cursor=""))

    def toggle(self):
        self.var.set(not self.var.get())
        self.command()
        self.draw()

    def place(self, x, y):
        self.x, self.y = x, y
        self.draw()

    def draw(self):
        cv, s = self.app.cv, self.app.scale
        cv.delete(self.tag)
        b = round(16 * s)
        cv.create_rectangle(self.x, self.y, self.x + b, self.y + b, fill="white", outline="#6b7280", tags=self.tag)
        if self.var.get():
            cv.create_line(self.x + b * .2, self.y + b * .55, self.x + b * .42, self.y + b * .78, self.x + b * .82, self.y + b * .22,
                           fill=TXT_LINK, width=max(2, round(2 * s)), tags=self.tag)
        cv.create_text(self.x + b + round(8 * s), self.y + b // 2, text=self.text, anchor="w", fill=TXT,
                       font=self.app.fonts["small"], tags=self.tag)


def _no_activate(win) -> None:
    """Windows: cửa sổ không giành focus khi bấm vào, để phím vẫn gửi tới PowerPoint."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = -20, 0x08000000, 0x00000080
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
    except Exception:
        pass  # không có thì cửa sổ vẫn dùng được, chỉ là bấm vào sẽ lấy focus


class StatusWindow:
    """Cửa sổ nhỏ 100x150: dải chế độ (TẬP/THẬT) | ô trạng thái Intent Gate | lệnh | gợi ý | thanh tiến độ."""

    def __init__(self, tk, master, on_stop, on_toggle_mode):
        self.tk = tk
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)            # không viền, không thanh tiêu đề
        self.win.attributes("-topmost", True)
        x = self.win.winfo_screenwidth() - W - 12
        self.win.geometry(f"{W}x{H}+{x}+12")      # góc trên phải; kéo chuột để dời
        self.canvas = tk.Canvas(self.win, width=W, height=H, bg=BG, highlightthickness=1, highlightbackground="#6b7280")
        self.canvas.pack()
        self.menu = tk.Menu(self.win, tearoff=0)
        self.menu.add_command(label="Đổi chế độ TẬP / THẬT", command=on_toggle_mode)
        self.menu.add_command(label="Dừng", command=on_stop)
        self.canvas.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self._last = None
        _no_activate(self.win)
        self.win.after(1000, self._keep_on_top)

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag(self, e):
        self.win.geometry(f"+{self.win.winfo_x() + e.x - self._dx}+{self.win.winfo_y() + e.y - self._dy}")

    def _keep_on_top(self):
        try:
            self.win.attributes("-topmost", True)
            self.win.lift()
            self.win.after(1000, self._keep_on_top)
        except Exception:
            pass  # cửa sổ đã đóng

    def draw(self, vm: dict) -> None:
        key = tuple(vm.values())
        if key == self._last:
            return
        self._last = key
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, W, 18, fill=vm["mode_color"], width=0)                       # dải chế độ
        c.create_text(W // 2, 9, text=vm["mode_text"], fill="white", font=(FONT_BOLD, 10))
        c.create_rectangle(0, 18, W, 74, fill=vm["color"], width=0)                           # ô trạng thái
        c.create_text(W // 2, 46, text=vm["title"], fill="white", font=(FONT_BOLD, 12), width=W - 6, justify="center")
        c.create_text(W // 2, 88, text=vm["command"], fill=FG, font=(FONT_BOLD, 10), width=W - 8, justify="center")
        c.create_text(W // 2, 116, text=vm["hint"], fill=MUTED, font=(FONT, 10), width=W - 10, justify="center")
        c.create_rectangle(8, 141, W - 8, 146, fill="#374151", width=0)                       # thanh tiến độ
        if vm["progress"] > 0:
            c.create_rectangle(8, 141, 8 + (W - 16) * vm["progress"], 146, fill=vm["color"], width=0)

    def destroy(self):
        self.win.destroy()


class ControlApp:
    def __init__(self, cfg: Config, log: bool = True, session_factory=None, maximized: bool = False):
        import tkinter as tk
        from tkinter import messagebox
        self.tk, self.messagebox = tk, messagebox
        self.cfg, self.log = cfg, log
        self.session_factory = session_factory      # để kiểm thử thay LiveSession bằng bản giả
        self.dry_run = cfg.dry_run                  # mặc định bắt đầu ở chế độ TẬP
        self.session = self.thread = self.status = self.guide = None
        self.policy = cfg.policy                    # bộ lọc lệnh (Intent Gate policy) đang chọn; đổi được khi chưa chạy
        self.maximized = False
        self.lang = "vi"                            # "vi" | "en"
        self.info_state = ("idle", "#4b5563", {})
        self.scale = 1.0
        self._images, self._layout_key, self._cfg_job, self._sync_job = {}, None, None, None
        self.bg_image = self.title_image = None
        load_bundled_fonts()
        r = self.root = tk.Tk()
        r.title("HGISS")
        r.configure(bg=WIN_BG)
        r.resizable(True, True)           # giữ nút phóng to trên thanh tiêu đề; kéo giãn tay bị đưa về cỡ cố định (_sync_zoom)
        r.rowconfigure(0, weight=1)
        r.protocol("WM_DELETE_WINDOW", self.close)
        self._make_fonts()
        self.cv = tk.Canvas(r, highlightthickness=0, bd=0, bg=WIN_BG)    # nền + mọi thứ ở cột điều khiển vẽ trên Canvas này
        self.cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.title_items = []
        self.btns, self.hover_btn = [], None       # mọi nút trên Canvas; nút đang được rê chuột
        self.start_btn = CanvasButton(self, command=self.toggle_run, bg="#16a34a",
                                      activebackground="#15803d", fg="white", skin="start")
        self.mode_btn = CanvasButton(self, command=self.toggle_mode)
        self.policy_btn = CanvasButton(self, command=self.open_policy_menu, bg="#dbeafe", activebackground="#bfdbfe", skin="policy")
        self.guide_btn = CanvasButton(self, command=self.toggle_guide, skin="guide")
        self.buttons = [self.start_btn, self.mode_btn, self.policy_btn, self.guide_btn]
        self.preview_var = tk.BooleanVar(value=False)
        self.cam_btn = CanvasButton(self, command=self.toggle_camera, skin="camera", align="center")
        self.lang_btn = CanvasButton(self, command=self.toggle_lang, skin="lang", align="center")
        self.small_buttons = [self.cam_btn, self.lang_btn]
        self.info = CanvasText(self, "", fg=TXT_MUTED, font="small")
        self._repaint()
        r.bind("<Key>", self._on_key)                 # phím tắt
        r.bind("<Configure>", self._schedule_sync, add="+")   # phóng to/thu nhỏ bằng thanh tiêu đề
        self.cv.bind("<Configure>", self._schedule_layout)
        self.cv.bind("<Motion>", self._on_motion)
        self.cv.bind("<Leave>", lambda _e: self._set_hover(None))
        self.cv.bind("<ButtonPress-1>", lambda e: self.hover_btn and self.hover_btn._press(e))
        self.cv.bind("<ButtonRelease-1>", self._on_release)
        self._layout()
        self._center()
        if maximized:
            self.set_maximized(True)
        r.after(60, self._tick)

    # --- ảnh: nền và nút ---
    def _make_fonts(self):
        s = self.scale
        self.fonts = {"btn": (FONT_BOLD, round(14 * s)), "btn_s": (FONT_BOLD, round(11 * s)), "title": (FONT_BOLD, round(14 * s)),
                      "sub": (FONT_ITALIC, round(12 * s)), "small": (FONT, round(10 * s)),
                      "small_u": (FONT, round(10 * s), "underline")}

    def _photo(self, path, size, mode):
        key = (str(path), size, mode)
        if key not in self._images:
            self._images[key] = make_photo(self.tk, path, size, mode)      # None nếu lỗi: nhớ luôn để khỏi đọc lại mỗi lần vẽ
        return self._images[key]

    def skin_image(self, skin, state, size):
        """Ảnh của nút: assets/buttons/<skin>[_hover|_down|_off].png; thiếu ảnh trạng thái thì dùng <skin>.png; không có thì None."""
        if not skin:
            return None
        for name in ((f"{skin}_{state}" if state else None), skin):
            if name and (BTN_DIR / f"{name}.png").exists():
                return self._photo(BTN_DIR / f"{name}.png", size, "stretch")
        return None

    def _draw_background(self, size):
        guide_on = bool(self.guide and self.guide.visible)
        key = "max" if self.maximized else "guide" if guide_on else "normal"
        self.cv.delete("bg")
        for f in (BG_DIR / f"bg_{key}.png", BG_DIR / "background.png"):
            if f.exists():
                img = self._photo(f, size, "cover")
                if img is not None:
                    self.bg_image = img
                    self.cv.create_image(0, 0, image=img, anchor="nw", tags="bg")
                    self.cv.tag_lower("bg")
                return

    # --- bố cục theo trạng thái cửa sổ ---
    def _canvas_size(self):
        if self.maximized:
            return max(1, self.cv.winfo_width()), max(1, self.cv.winfo_height())
        return GUIDE_SIZE if (self.guide and self.guide.visible) else NORMAL_SIZE

    def _layout(self):
        """Thường: cột điều khiển ở giữa. Phóng to (chưa bật hướng dẫn): ở giữa và to hơn.
        Bật hướng dẫn: cột điều khiển dồn sang trái cỡ thường, hướng dẫn chiếm phần còn lại."""
        r, tk = self.root, self.tk
        guide_on = bool(self.guide and self.guide.visible)
        self.scale = MAX_SCALE if (self.maximized and not guide_on) else 1.0
        self._make_fonts()
        s = self.scale
        cw, ch = self._canvas_size()
        bw, bh, gap = round(BTN_W * s), round(BTN_H * s), round(10 * s)
        title_h, row_h = round(70 * s), round(30 * s)
        sh = round(SMALL_H * s)
        total = title_h + 4 * (bh + gap) + row_h + round(46 * s)
        if guide_on:
            x0, y0 = MARGIN, MARGIN - 20
            r.columnconfigure(0, weight=0, minsize=MARGIN + bw + MARGIN) 
            r.columnconfigure(1, weight=1)
        else:
            if self.maximized:
                x0, y0 = (cw - bw) // 2, max(MARGIN, (ch - total) // 2 - 20)
            else:
                x0, y0 = MARGIN, MARGIN - 20         # cỡ thường: cách viền trái và trên 50 px, giống lúc bật hướng dẫn
            r.columnconfigure(0, weight=1, minsize=0)
            r.columnconfigure(1, weight=0)
        self._draw_background((cw, ch))
        y = y0 + self._draw_title(x0 + bw // 2, y0, bw)
        for b in self.buttons:
            b.place(x0, y, bw, bh)
            y += bh + gap
        sw = (bw - gap) // 2                                        # 2 nút nhỏ chung một hàng, khít 2 mép của các nút trên
        self.cam_btn.place(x0, y, sw, sh)
        self.lang_btn.place(x0 + bw - sw, y, sw, sh)
        y += sh + gap
        # y += row_h + round(6 * s)
        self.info.place(x0, y, bw)
        self._layout_key = (cw, ch, self.maximized, guide_on)
        self._fit_window()

    def _draw_title(self, cx, y, width):
        for it in self.title_items:
            self.cv.delete(it)
        self.title_items = []
        s, y_start = self.scale, y
        if self.title_image is None and TITLE_IMG.exists():
            try:
                self.title_image = self.tk.PhotoImage(file=str(TITLE_IMG))
            except self.tk.TclError:
                self.title_image = False
        if self.title_image:
            self.title_items.append(self.cv.create_image(cx, y, image=self.title_image, anchor="n"))
            y += self.title_image.height() + round(6 * s)          # chữ nằm ngay dưới ảnh
        self.title_items.append(self.cv.create_text(cx, y + round(4 * s), text=self.tr("title"),
                                                    anchor="n", fill=TXT, font=self.fonts["title"], width=width + 40, justify="center"))
        # self.title_items.append(self.cv.create_text(cx, y + round(34 * s), text="Hand-Gesture Interaction Slideshow System",
        #                                             anchor="n", fill=TXT, font=self.fonts["sub"], width=width + 40, justify="center"))
        return (y - y_start) + round(70 * s)                                            

    def _schedule_layout(self, _e):
        if self._cfg_job:
            self.root.after_cancel(self._cfg_job)
        self._cfg_job = self.root.after(60, self._relayout)

    def _relayout(self):
        """Kích thước Canvas đổi (vd vừa phóng to xong): vẽ lại nền và xếp lại cột điều khiển."""
        self._cfg_job = None
        guide_on = bool(self.guide and self.guide.visible)
        if self._layout_key != (self.cv.winfo_width(), self.cv.winfo_height(), self.maximized, guide_on):
            self._layout()

    def _fit_window(self):
        if self.maximized:
            return
        w, h = self._canvas_size()
        self.root.geometry(f"{w}x{h}")

    def _center(self):
        r = self.root
        w, h = NORMAL_SIZE
        r.geometry(f"{w}x{h}+{max(0, (r.winfo_screenwidth() - w) // 2)}+{max(0, (r.winfo_screenheight() - h) // 3)}")

    # --- hai trạng thái cửa sổ ---
    def _zoom(self, on: bool):
        """Gọi hệ điều hành phóng to / khôi phục (vẫn thấy thanh tiêu đề và thanh tác vụ, khác với toàn màn hình F11)."""
        try:
            self.root.state("zoomed" if on else "normal")                  # Windows, macOS
        except self.tk.TclError:
            self.root.attributes("-zoomed", on)                            # Linux

    def _is_zoomed(self) -> bool:
        try:
            if sys.platform in ("win32", "darwin"):
                return self.root.state() == "zoomed"
            return bool(self.root.attributes("-zoomed"))
        except self.tk.TclError:
            return False

    def set_maximized(self, on: bool):
        on = bool(on)
        if on == self.maximized:
            return
        self.maximized = on
        self._zoom(on)
        self._layout()

    maximize = set_maximized                    # tên cũ, run_ui(maximized=True) vẫn dùng

    def is_maximized(self) -> bool:
        return self.maximized

    def toggle_maximized(self):
        self.set_maximized(not self.maximized)

    def _schedule_sync(self, event):
        if event.widget is not self.root:
            return
        if self._sync_job:
            self.root.after_cancel(self._sync_job)
        self._sync_job = self.root.after(80, self._sync_zoom)

    def _sync_zoom(self):
        """Người dùng khôi phục bằng nút trên thanh tiêu đề: đưa cờ và bố cục về khớp."""
        self._sync_job = None
        z = self._is_zoomed()
        if z != self.maximized:
            self.set_maximized(z)
        elif not z:
            w, h = self._canvas_size()                  # người dùng kéo cạnh cửa sổ: trả về cỡ cố định
            if (self.root.winfo_width(), self.root.winfo_height()) != (w, h):
                self.root.geometry(f"{w}x{h}")

    def _on_key(self, e):
        """S = Bắt đầu/Dừng · M = TẬP/GỬI THẬT · P = bộ lọc lệnh · G = hướng dẫn · C = bật/tắt camera · L = đổi ngôn ngữ."""
        k = (e.keysym or "").lower()
        if k == "s" and self.start_btn["state"] != "disabled":
            self.toggle_run()
        elif k == "m":
            self.toggle_mode()
        elif k == "p":
            self.cycle_policy()
        elif k == "g":
            self.toggle_guide()
        elif k == "c":
            self.toggle_camera()
        elif k == "l":
            self.toggle_lang()

    # --- chuột trên các nút (một chỗ duy nhất, chỉ vẽ lại khi nút đang rê thay đổi) ---
    def _on_motion(self, e):
        hit = next((b for b in reversed(self.btns) if b.contains(e.x, e.y)), None)
        self._set_hover(hit)

    def _set_hover(self, btn):
        if btn is self.hover_btn:
            return
        old, self.hover_btn = self.hover_btn, btn
        if old:
            old._leave(None)
        if btn:
            btn._enter(None)

    def _on_release(self, e):
        if self.hover_btn:
            self.hover_btn._release(e)

    # --- ngôn ngữ ---
    def tr(self, key, **kw):
        text = STR[self.lang][key]
        return text.format(**kw) if kw else text

    def _set_info(self, key, fg, **kw):
        self.info_state = (key, fg, kw)
        self.info.config(text=self.tr(key, **kw), fg=fg)

    def toggle_lang(self):
        self.lang = "en" if self.lang == "vi" else "vi"
        self._repaint()
        self._layout()                                          # tiêu đề vẽ lại bằng ngôn ngữ mới

    def _repaint(self):
        """Gán lại toàn bộ chữ trên giao diện theo ngôn ngữ và trạng thái hiện tại."""
        running = self.session is not None
        if self.start_btn["state"] != "disabled":            # đang "Đang dừng..." thì giữ nguyên
            self.start_btn.config(text=self.tr("stop" if running else "start"))
        else:
            self.start_btn.config(text=self.tr("stopping"))
        self._paint_mode()
        self._paint_policy()
        self.guide_btn.config(text=self.tr("guide_on" if self.guide and self.guide.visible else "guide_off"))
        self.cam_btn.config(text=self.tr("cam_on" if self.preview_var.get() else "cam_off"))
        self.lang_btn.config(text=self.tr("lang"))
        key, fg, kw = self.info_state
        self.info.config(text=self.tr(key, **kw), fg=fg)
        if self.guide:
            self.guide.set_lang(self.lang)                     

    def toggle_camera(self):
        self.preview_var.set(not self.preview_var.get())
        self._apply_preview()
        self.cam_btn.config(text=self.tr("cam_on" if self.preview_var.get() else "cam_off"))

    # --- nút bấm ---
    def toggle_run(self):
        if self.session is None:
            self.start()
        else:
            self.stop()

    def start(self):
        cfg = self.cfg if self.policy == self.cfg.policy else self.cfg.with_policy(self.policy)
        if self.session_factory:
            self.session = self.session_factory(cfg, self.log, self.preview_var.get())
        else:
            from ..live import LiveSession  # nhập muộn: cv2/mediapipe chỉ nạp khi bấm Bắt đầu
            self.session = LiveSession(cfg, log=self.log, preview=self.preview_var.get())
        self.session.dry_run = self.dry_run
        self.thread = threading.Thread(target=self.session.run, daemon=True)
        self.thread.start()
        self.status = StatusWindow(self.tk, self.root, self.stop, self.toggle_mode)
        self.start_btn.config(text=self.tr("stop"), bg="#dc2626", activebackground="#b91c1c", skin="stop")
        self._paint_policy()
        self._set_info("starting", "#4b5563")

    def stop(self):
        if self.session:
            self.session.request_stop()
            self.start_btn.config(text=self.tr("stopping"), state="disabled")

    def toggle_mode(self):
        new = not self.dry_run
        if not new:  # sang GỬI THẬT: kiểm tra trước và hỏi lại
            try:
                import pynput.keyboard  # noqa: F401
            except Exception as e:
                self.messagebox.showerror(self.tr("err_keys_t"), self.tr("err_keys", e=e))
                return
            if not self.messagebox.askokcancel(self.tr("ask_real_t"), self.tr("ask_real")):
                return
        if self.session:
            try:
                self.session.set_dry_run(new)
            except Exception as e:
                self.messagebox.showerror(self.tr("err_mode_t"), str(e))
                return
        self.dry_run = new
        self._paint_mode()

    def toggle_guide(self):
        """Bật / tắt phần hướng dẫn cử chỉ ngay trong cửa sổ này (không mở cửa sổ mới)."""
        if self.guide is None:
            from .gesture_guide import GuidePanel  # nhập muộn
            self.guide = GuidePanel(self.tk, self.root, labels=getattr(self.cfg, "external_labels", {}), font=FONT, policy=self.policy, lang=self.lang)
        if self.guide.visible:
            self.guide.hide()
            self.guide_btn.config(text=self.tr("guide_off"))
        else:
            self.guide.show(grid=dict(row=0, column=1, sticky="nsew", padx=(0, MARGIN), pady=14))  # cột phải của cùng cửa sổ
            self.guide_btn.config(text=self.tr("guide_on"))
        self._layout()

    # --- bộ lọc lệnh (C1–C4) ---
    def _policy_info(self):
        return next(m for m in mode_list(self.cfg.policy, self.lang) if m["key"] == self.policy)

    def open_policy_menu(self):
        """Bấm nút Bộ lọc: hiện danh sách chọn ngay dưới nút. Đang chạy thì không đổi (phải Dừng trước)."""
        if self.session:
            return
        menu = self.tk.Menu(self.root, tearoff=0)
        var = self.tk.StringVar(value=self.policy)
        for m in mode_list(self.cfg.policy, self.lang):
            menu.add_radiobutton(label=f"{m['tag']} · {m['title']}", variable=var, value=m["key"],
                                 command=lambda k=m["key"]: self.set_policy(k))
        b = self.policy_btn
        menu.tk_popup(self.cv.winfo_rootx() + b.x, self.cv.winfo_rooty() + b.y + b.h)

    def cycle_policy(self):
        keys = [m["key"] for m in mode_list(self.cfg.policy, self.lang)]
        self.set_policy(keys[(keys.index(self.policy) + 1) % len(keys)])

    def set_policy(self, key: str):
        if self.session or key == self.policy:
            return
        self.policy = key
        self._paint_policy()
        if self.guide:
            self.guide.set_policy(key)

    def _paint_policy(self):
        m = self._policy_info()
        second = self.tr("policy_locked") if self.session else m["title"]
        self.policy_btn.config(text=self.tr("policy", tag=m["tag"], second=second), state="disabled" if self.session else "normal", fg=TXT)

    def _paint_mode(self):
        if self.dry_run:
            self.mode_btn.config(text=self.tr("tap"), bg="#f59e0b", activebackground="#d97706", fg="black", skin="tap")
        else:
            self.mode_btn.config(text=self.tr("real"), bg="#001AAF", activebackground="#00137F", fg="white", skin="real")

    def _apply_preview(self):
        if self.session:
            self.session.preview = self.preview_var.get()

    # --- vòng cập nhật ---
    def _tick(self):
        if self.session is not None:
            if self.thread is not None and not self.thread.is_alive():
                self._finished()
            else:
                snap = self.session.snapshot()
                if self.status:
                    self.status.draw(view_model(snap, time.monotonic()))
                if snap["running"]:
                    self._set_info("running", "#15803d", fps=snap["fps"], seen=self.tr("hand" if snap["hand"] > 0.3 else "nohand"))
        self.root.after(60, self._tick)

    def _finished(self):
        err = self.session.error
        self.session = self.thread = None
        if self.status:
            self.status.destroy()
            self.status = None
        self.start_btn.config(text=self.tr("start"), bg="#16a34a", activebackground="#15803d", state="normal", skin="start")
        self._paint_policy()
        if err:
            self._set_info("error", "#dc2626", err=err)
        else:
            self._set_info("stopped", "#4b5563")

    def close(self):
        if self.session:
            self.session.request_stop()
            if self.thread:
                self.thread.join(timeout=2)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_ui(cfg: Config, log: bool = True, maximized: bool = False):
    ControlApp(cfg, log=log, maximized=maximized).run()