"""Cửa sổ điều khiển: thẻ bên trái (trạng thái, Bắt đầu/Dừng, Tập/Gửi phím thật, bộ lọc lệnh, camera, hướng dẫn)
+ thẻ hướng dẫn bên phải (ẩn/hiện bằng phím I) + ô trạng thái nhỏ nổi ở góc phải màn hình khi đang chạy.
Màu, chữ, khoảng cách lấy từ theme.py; hình vẽ mượt từ render.py; nút và ô chọn từ widgets.py."""
from __future__ import annotations

import sys
import threading
import time

from ..config import Config
from . import render
from .gesture_guide import mode_list
from .status_model import view_model
from .theme import APP_NAME, APP_TAGLINE, C, FONT, RADIUS, SHADOW, SPACE, TYPE, load_bundled_fonts, px, tint
from .widgets import Button, Card, RadioList, Segmented, Toggle, keycap_width, measure, section_label

SIDEBAR_W = px(400)      # thẻ bên trái (gồm lề và bóng)
GUIDE_W = px(640)        # thẻ hướng dẫn khi mở
MIN_H = px(660)
MODE_DOT = {True: C["warning"], False: C["danger"]}          # chấm màu của chế độ trên nền sáng


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


def _work_area(root):
    """(trên, dưới) của vùng làm việc màn hình chính (trừ thanh tác vụ), theo pixel màn hình."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            rect = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rect), 0):    # SPI_GETWORKAREA
                return rect.top, rect.bottom
        except Exception:
            pass
    return 0, root.winfo_screenheight() - px(48)


def _fit_font(text, style, width, min_size=8):
    """Font cỡ lớn nhất (<= cỡ của style) để `text` nằm gọn một dòng trong `width` px."""
    family, size, *rest = style
    while size > min_size and measure((family, size, *rest), text) > width:
        size -= 1
    return (family, size, *rest)


def _progress(cv, x0, y, x1, value, color, track):
    """Thanh tiến độ bo tròn hai đầu."""
    h = px(6)
    cv.create_image(x0, y, anchor="nw", image=render.shape(cv, x1 - x0, h, h // 2, fill=track))
    if value > 0:
        w = max(h, int((x1 - x0) * value))
        cv.create_image(x0, y, anchor="nw", image=render.shape(cv, w, h, h // 2, grad=(color, tint(color, 0.25))))


class StatusCard:
    """Ô trạng thái trong thẻ bên: chế độ, nhãn trạng thái Intent Gate, lệnh, gợi ý, tiến độ giữ, dòng phụ (fps / lỗi)."""

    H = px(104)

    def __init__(self, tk, parent):
        self.cv = tk.Canvas(parent, height=self.H, width=1, bg=parent["bg"], highlightthickness=0)
        self.cv.bind("<Configure>", lambda _e: self._draw())
        self.state = None

    def show(self, vm, dry_run, meta="", error=False):
        state = (tuple(vm.values()), dry_run, meta, error)
        if state != self.state:
            self.state = state
            self.vm, self.dry_run, self.meta, self.error = vm, dry_run, meta, error
            self._draw()

    def _draw(self):
        cv = self.cv
        cv.delete("all")
        w, h = cv.winfo_width(), self.H
        if w < 40 or self.state is None:
            return
        vm, pad = self.vm, SPACE["lg"]
        cv.create_image(0, 0, anchor="nw", image=render.shape(cv, w, h, RADIUS + px(2), fill=C["surface_alt"], outline=C["border"], width=1))
        color = C["danger"] if self.error else vm["color"]
        title = "LỖI" if self.error else vm["title"]
        # hàng 1: nhãn trạng thái (nền nhạt cùng tông + chấm màu + chữ đậm) + lệnh | chế độ bên phải
        ph, dot, y0 = px(30), px(9), px(14)
        pw = measure(TYPE["heading"], title) + dot + px(32)
        cv.create_image(pad, y0, anchor="nw", image=render.shape(cv, pw, ph, ph // 2, fill=tint(color, 0.86)))
        cv.create_image(pad + px(13), y0 + ph / 2, anchor="w", image=render.circle(cv, dot, fill=color))
        cv.create_text(pad + px(13) + dot + px(8), y0 + ph / 2, text=title, anchor="w", font=TYPE["heading"], fill=C["text"])
        if vm["command"] and not self.error:
            cv.create_text(pad + pw + SPACE["sm"], y0 + ph / 2, text=vm["command"], anchor="w", font=TYPE["body_b"], fill=C["text"])
        mode = "Tập" if self.dry_run else "Gửi phím thật"
        mx = w - pad - measure(TYPE["small_b"], mode) - px(13)
        cv.create_image(mx, y0 + ph / 2, anchor="w", image=render.circle(cv, px(8), fill=MODE_DOT[self.dry_run]))
        cv.create_text(w - pad, y0 + ph / 2, text=mode, anchor="e", font=TYPE["small_b"], fill=C["text"])
        # hàng 2: gợi ý | dòng phụ (fps) bên phải; lỗi: chiếm cả hàng 2 và 3
        if self.error:
            cv.create_text(pad, px(54), text=vm["hint"] + "\n" + self.meta, anchor="nw", font=TYPE["small"],
                           fill=C["danger_hover"], width=w - 2 * pad)
            return
        cv.create_text(pad, px(66), text=vm["hint"], anchor="w", font=TYPE["body"], fill=C["text_2"])
        if self.meta:
            cv.create_text(w - pad, px(66), text=self.meta, anchor="e", font=TYPE["small"], fill=C["text_3"])
        _progress(cv, pad, px(84), w - pad, vm["progress"], color, C["border"])


class StatusWindow:
    """Ô trạng thái nổi ở góc phải màn hình khi đang chạy: chế độ | nhãn trạng thái | lệnh | gợi ý | thanh tiến độ.
    Kéo để dời, chuột phải: đổi chế độ / dừng. Không giành focus của PowerPoint."""

    W, H = px(176), px(146)
    KEY = "#010203"      # màu trong suốt (Windows) để bo góc cửa sổ

    def __init__(self, tk, master, on_stop, on_toggle_mode):
        self.tk = tk
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)            # không viền, không thanh tiêu đề
        self.win.attributes("-topmost", True)
        self.rounded = True
        try:
            self.win.attributes("-transparentcolor", self.KEY)
        except tk.TclError:
            self.rounded = False
        x = self.win.winfo_screenwidth() - self.W - px(16)
        self.win.geometry(f"{self.W}x{self.H}+{x}+{px(16)}")
        self.canvas = tk.Canvas(self.win, width=self.W, height=self.H, bg=self.KEY if self.rounded else C["hud_bg"],
                                highlightthickness=0, cursor="fleur")
        self.canvas.pack()
        self.menu = tk.Menu(self.win, tearoff=0, font=TYPE["body"])
        self.menu.add_command(label="Đổi chế độ Tập / Gửi phím thật", command=on_toggle_mode)
        self.menu.add_command(label="Dừng nhận cử chỉ", command=on_stop)
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
        c, W, H = self.canvas, self.W, self.H
        c.delete("all")
        if self.rounded:
            c.create_image(0, 0, anchor="nw", image=render.window_bg(c, W, H, px(16), C["hud_bg"], self.KEY))
        pad = px(12)
        c.create_image(pad + px(2), px(18), anchor="w", image=render.circle(c, px(8), fill=vm["mode_color"]))
        c.create_text(pad + px(16), px(18), text=vm["mode_text"], anchor="w", fill=vm["mode_color"], font=TYPE["caps"])
        y0, ph = px(32), px(44)
        c.create_image(pad, y0, anchor="nw", image=render.shape(c, W - 2 * pad, ph, px(10), grad=(vm["color"], vm["color"])))
        c.create_text(W / 2, y0 + ph / 2, text=vm["title"], fill=C["on_color"], font=_fit_font(vm["title"], TYPE["title"], W - 2 * pad - px(16)))
        y = px(94)
        if vm["command"]:
            c.create_text(W / 2, y, text=vm["command"], fill=C["hud_text"], font=_fit_font(vm["command"], TYPE["body_b"], W - 2 * pad))
            y += px(20)
        c.create_text(W / 2, y, text=vm["hint"], fill=C["hud_muted"], font=TYPE["small"], width=W - 2 * pad, justify="center")
        _progress(c, px(16), H - px(18), W - px(16), vm["progress"], vm["color"], C["hud_track"])

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
        self.error = None
        load_bundled_fonts()
        r = self.root = tk.Tk()
        r.title(f"{APP_NAME} · {APP_TAGLINE}")
        r.configure(bg=C["bg"])
        r.option_add("*Font", TYPE["body"])
        r.protocol("WM_DELETE_WINDOW", self.close)
        try:
            r.iconphoto(True, render.logo(r, px(64)))
        except Exception:
            pass
        r.rowconfigure(0, weight=1)
        r.columnconfigure(0, minsize=SIDEBAR_W)
        r.columnconfigure(1, weight=1)
        self._build_sidebar()
        self.content = tk.Frame(r, bg=C["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        r.bind("<Key>", self._on_key)
        r.bind("<Configure>", self._on_configure, add="+")
        self._refresh_sidebar()
        self._fit(center=True)
        if maximized:
            self.set_maximized(True)
        r.after(60, self._tick)

    # ---------- thẻ bên ----------
    def _build_sidebar(self):
        tk = self.tk
        gap = SPACE["lg"]
        self.side_card = Card(self.root, pad=SPACE["xl"], fill_height=True)
        self.side_card.grid(row=0, column=0, sticky="nsew", padx=(gap, 0), pady=gap)
        inner = self.inner = self.side_card.inner

        head = tk.Frame(inner, bg=C["surface"])
        head.pack(fill="x")
        self.logo = render.logo(head, px(44))
        tk.Label(head, image=self.logo, bg=C["surface"]).pack(side="left")
        names = tk.Frame(head, bg=C["surface"])
        names.pack(side="left", padx=(SPACE["md"], 0))
        tk.Label(names, text=APP_NAME, font=TYPE["display"], fg=C["text"], bg=C["surface"]).pack(anchor="w")
        tk.Label(names, text=APP_TAGLINE, font=TYPE["small"], fg=C["text_2"], bg=C["surface"]).pack(anchor="w")

        self.card = StatusCard(tk, inner)
        self.card.cv.pack(fill="x", pady=(SPACE["xl"], SPACE["md"]))
        self.start_btn = Button(inner, "Bắt đầu nhận cử chỉ", self.toggle_run, variant="primary", icon="play", shortcut="S", height=px(48))
        self.start_btn.pack(fill="x")

        section_label(inner, "CHẾ ĐỘ", "phím M").pack(fill="x", pady=(SPACE["xl"], SPACE["xs"]))
        self.mode_seg = Segmented(inner, [("dry", "Tập", C["warning"]), ("real", "Gửi phím thật", C["danger"])],
                                  "dry", self._pick_mode)
        self.mode_seg.pack(fill="x")
        self.mode_help = tk.Label(inner, font=TYPE["small"], fg=C["text_3"], bg=C["surface"], anchor="w", justify="left")
        self.mode_help.pack(fill="x", pady=(SPACE["xs"], 0))

        self.policy_head = section_label(inner, "BỘ LỌC LỆNH", "phím P")
        self.policy_head.pack(fill="x", pady=(SPACE["lg"], SPACE["xs"]))
        self.policy_list = RadioList(inner, mode_list(self.cfg.policy), self.policy, self.set_policy)
        self.policy_list.pack(fill="x")

        tk.Frame(inner, height=1, bg=C["border"]).pack(fill="x", pady=(SPACE["md"], SPACE["sm"]))
        row = tk.Frame(inner, bg=C["surface"])
        row.pack(fill="x")
        self.preview_var = tk.BooleanVar(value=False)
        self.cam = Toggle(row, self.preview_var, "Camera", self._apply_preview, shortcut="C")
        self.cam.pack(side="left", fill="x", expand=True, padx=(0, SPACE["lg"]))
        self.guide_btn = Button(row, "Hướng dẫn", self.toggle_guide, variant="ghost", shortcut="I", height=px(38),
                                width=measure(TYPE["body_b"], "Hướng dẫn") + keycap_width("I") + px(40))
        self.guide_btn.pack(side="right")

    def _refresh_sidebar(self):
        running = self.session is not None
        self.mode_seg.set("dry" if self.dry_run else "real")
        self.mode_help.config(text="Chỉ hiện lệnh nhận được, không bấm phím." if self.dry_run
                              else "Cử chỉ bấm phím thật vào cửa sổ đang được chọn.")
        self.policy_list.set(self.policy)
        self.policy_list.set_enabled(not running)
        self.policy_head.winfo_children()[1].config(text="khóa khi đang chạy" if running else "phím P")
        if not running:
            vm = view_model({"running": False, "dry_run": self.dry_run}, time.monotonic())
            meta = "Kiểm tra camera rồi bấm Bắt đầu lại." if self.error else ""
            if self.error:
                vm = {**vm, "hint": self.error}
            self.card.show(vm, self.dry_run, meta, error=bool(self.error))

    # ---------- kích thước cửa sổ ----------
    def _guide_on(self):
        return bool(self.guide and self.guide.visible)

    def _fit(self, center=False):
        """Đặt cỡ cửa sổ theo việc hướng dẫn đang mở hay không (khi không phóng to)."""
        r = self.root
        if self.is_maximized():
            return
        r.update_idletasks()
        w = SIDEBAR_W + SPACE["lg"] + (GUIDE_W if self._guide_on() else 0)
        need = self.inner.winfo_reqheight() + 2 * (SPACE["xl"] + SPACE["lg"] + self.side_card.m)
        top, bottom = _work_area(r)
        h = min(max(MIN_H, need), bottom - top - px(48))     # chừa thanh tiêu đề cửa sổ
        if center:
            r.geometry(f"{w}x{h}+{max(0, (r.winfo_screenwidth() - w) // 2)}+{top + max(0, (bottom - top - h - px(40)) // 2)}")
        else:
            r.geometry(f"{w}x{h}")
        r.minsize(SIDEBAR_W + SPACE["lg"], h)

    def _on_configure(self, e):
        """Người dùng kéo rộng / phóng to cửa sổ khi hướng dẫn đang ẩn: hiện hướng dẫn cho khỏi trống."""
        if e.widget is self.root and e.width > SIDEBAR_W + px(320) and not self._guide_on():
            self.root.after_idle(lambda: None if self._guide_on() else self.toggle_guide())

    def is_maximized(self) -> bool:
        try:
            if sys.platform in ("win32", "darwin"):
                return self.root.state() == "zoomed"
            return bool(self.root.attributes("-zoomed"))
        except self.tk.TclError:
            return False

    def set_maximized(self, on: bool):
        try:
            self.root.state("zoomed" if on else "normal")
        except self.tk.TclError:
            self.root.attributes("-zoomed", bool(on))
        if on and not self._guide_on():
            self.toggle_guide()
        if not on:
            self._fit()

    maximize = set_maximized

    def toggle_maximized(self):
        self.set_maximized(not self.is_maximized())

    # ---------- phím tắt ----------
    def _on_key(self, e):
        """S = Bắt đầu/Dừng · M = Tập/Gửi phím thật · P = bộ lọc lệnh · I = hướng dẫn · C = camera."""
        k = (e.keysym or "").lower()
        if k == "s" and self.start_btn.enabled:
            self.toggle_run()
        elif k == "m":
            self.toggle_mode()
        elif k == "p":
            self.cycle_policy()
        elif k == "i":
            self.toggle_guide()
        elif k == "c":
            self.cam.invoke()

    # ---------- chạy / dừng ----------
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
        self.error = None
        self.thread = threading.Thread(target=self.session.run, daemon=True)
        self.thread.start()
        self.status = StatusWindow(self.tk, self.root, self.stop, self.toggle_mode)
        self.start_btn.set(text="Dừng nhận cử chỉ", variant="danger", icon="stop")
        self._refresh_sidebar()

    def stop(self):
        if self.session:
            self.session.request_stop()
            self.start_btn.set(text="Đang dừng...", enabled=False)

    # ---------- chế độ ----------
    def _pick_mode(self, key):
        if (key == "dry") != self.dry_run:
            self.toggle_mode()

    def toggle_mode(self):
        new = not self.dry_run
        if not new:  # sang GỬI THẬT: kiểm tra trước và hỏi lại
            try:
                import pynput.keyboard  # noqa: F401
            except Exception as e:
                self.messagebox.showerror("Không gửi được phím",
                                          f"Máy chưa có thư viện pynput ({e}).\n\nCài bằng lệnh: pip install pynput, rồi mở lại ứng dụng.")
                return
            if not self.messagebox.askokcancel("Gửi phím thật?",
                                               "Từ giờ cử chỉ sẽ bấm phím thật vào cửa sổ đang được chọn.\n\n"
                                               "Hãy bấm vào cửa sổ PowerPoint trước khi trình chiếu."):
                return
        if self.session:
            try:
                self.session.set_dry_run(new)
            except Exception as e:
                self.messagebox.showerror("Không đổi được chế độ", f"{e}\n\nChế độ vẫn giữ như cũ.")
                return
        self.dry_run = new
        self._refresh_sidebar()

    # ---------- hướng dẫn ----------
    def toggle_guide(self):
        if self.guide is None:
            from .gesture_guide import GuidePanel  # nhập muộn
            self.guide = GuidePanel(self.tk, self.content, labels=getattr(self.cfg, "external_labels", {}), font=FONT, policy=self.policy)
        if self.guide.visible:
            if self.is_maximized():
                self.set_maximized(False)
            self.guide.hide()
            self.guide_btn.set(variant="ghost")
        else:
            self.guide.show(padx=SPACE["lg"], pady=SPACE["lg"])
            self.guide_btn.set(variant="soft")
        self._fit()

    # ---------- bộ lọc lệnh (C1–C4) ----------
    def cycle_policy(self):
        keys = [m["key"] for m in mode_list(self.cfg.policy)]
        self.set_policy(keys[(keys.index(self.policy) + 1) % len(keys)])

    def set_policy(self, key: str):
        if self.session or key == self.policy:
            return
        self.policy = key
        self._refresh_sidebar()
        if self.guide:
            self.guide.set_policy(key)

    def _apply_preview(self):
        if self.session:
            self.session.preview = self.preview_var.get()

    # ---------- vòng cập nhật ----------
    def _tick(self):
        if self.session is not None:
            if self.thread is not None and not self.thread.is_alive():
                self._finished()
            else:
                snap = self.session.snapshot()
                vm = view_model(snap, time.monotonic())
                if self.status:
                    self.status.draw(vm)
                meta = ""
                if snap["running"]:
                    seen = "thấy tay" if snap["hand"] > 0.3 else "chưa thấy tay"
                    meta = f"{snap['fps']:.0f} khung/s · {seen}"
                self.card.show(vm, self.dry_run, meta)
        self.root.after(60, self._tick)

    def _finished(self):
        self.error = self.session.error
        self.session = self.thread = None
        if self.status:
            self.status.destroy()
            self.status = None
        self.start_btn.set(text="Bắt đầu nhận cử chỉ", variant="primary", icon="play", enabled=True)
        self._refresh_sidebar()

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
