"""Thành phần giao diện dùng chung. Vẽ hoàn toàn bằng Tk Canvas (không cần render.py/Pillow).
Mọi thành phần bấm được có đủ trạng thái: thường / rê chuột / đang bấm / tắt / có focus bàn phím.
Màu, cỡ, khoảng cách chỉ lấy từ theme.py."""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from .theme import BADGE, C, RADIUS, RADIUS_SM, SPACE, TARGET, TYPE, px

FOCUS_PAD = px(3)


def measure(style, text):
    return tkfont.Font(font=style).measure(text)


# ---------- Canvas primitives (thay render.py) ----------
def _round_rect(cv, x1, y1, x2, y2, r, fill=None, outline=None, width=1, tags=()):
    """Hình chữ nhật bo góc = polygon smooth. Không hỗ trợ gradient/bóng."""
    r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    kw = {}
    if fill is not None:
        kw["fill"] = fill
    else:
        kw["fill"] = ""
    if outline:
        kw["outline"] = outline
        kw["width"] = width
    else:
        kw["outline"] = fill or ""
        kw["width"] = 0
    return cv.create_polygon(pts, smooth=True, **kw, tags=tags)


def _circle(cv, cx, cy, d, fill=None, outline=None, width=1, tags=()):
    """Hình tròn tâm (cx,cy) đường kính d."""
    r = d / 2
    kw = {}
    kw["fill"] = fill or ""
    if outline:
        kw["outline"] = outline
        kw["width"] = width
    else:
        kw["outline"] = fill or ""
        kw["width"] = 0
    return cv.create_oval(cx - r, cy - r, cx + r, cy + r, **kw, tags=tags)


class _Interactive(tk.Canvas):
    """Nền chung: hover / bấm / focus / tắt, vẽ lại khi đổi cỡ."""

    def __init__(self, parent, height, width=None, command=None):
        super().__init__(parent, height=height, width=width or 1, bg=parent["bg"],
                         highlightthickness=0, bd=0, takefocus=1, cursor="hand2")
        self.command = command
        self.hover = self.down = self.focused = False
        self.enabled = True
        for seq, fn in (("<Configure>", lambda _e: self.draw()),
                        ("<Enter>", self._enter), ("<Leave>", self._leave),
                        ("<ButtonPress-1>", self._press),
                        ("<ButtonRelease-1>", self._release),
                        ("<FocusIn>", lambda _e: self._focus(True)),
                        ("<FocusOut>", lambda _e: self._focus(False)),
                        ("<space>", lambda _e: self.invoke()),
                        ("<Return>", lambda _e: self.invoke())):
            self.bind(seq, fn)

    def set_enabled(self, on: bool):
        self.enabled = bool(on)
        self.configure(cursor="hand2" if on else "arrow")
        self.draw()

    def invoke(self, *_):
        if self.enabled and self.command:
            self.command()
        return "break"

    def _enter(self, _e):
        self.hover = True
        self.draw()

    def _leave(self, _e):
        self.hover = self.down = False
        self.draw()

    def _press(self, _e):
        if self.enabled:
            self.down = True
            self.draw()

    def _release(self, e):
        fire = self.down and self.hover
        self.down = False
        self.draw()
        if fire:
            self.on_click(e)

    def on_click(self, _e):
        self.invoke()

    def _focus(self, on):
        self.focused = on
        self.draw()

    def size(self):
        return self.winfo_width(), self.winfo_height()

    def focus_ring(self, w, h, r=RADIUS):
        if self.focused:
            p = FOCUS_PAD
            _round_rect(self, p - 1, p - 1, w - p + 1, h - p + 1,
                        r + p, outline=C["focus"], width=px(2))

    def draw(self):
        raise NotImplementedError


class Button(_Interactive):
    """Nút. variant: primary | danger | secondary | ghost | soft."""

    VARIANTS = {
        "primary":   dict(fill=C["accent"],         hover=C["accent_hover"],   press=C["accent_press"],   fg=C["on_color"]),
        "danger":    dict(fill=C["danger"],         hover=C["danger_hover"],   press=C["danger_press"],   fg=C["on_color"]),
        "secondary": dict(fill=C["surface"],        hover=C["surface_alt"],    press=C["segment"],        fg=C["text"], border=C["border_ui"]),
        "ghost":     dict(fill=None,                hover=C["segment"],        press=C["border"],         fg=C["accent_text"]),
        "soft":      dict(fill=C["accent_soft"],    hover=C["segment"],        press=C["border"],         fg=C["accent_text"]),
    }

    def __init__(self, parent, text, command=None, variant="primary",
                 icon=None, shortcut=None, height=TARGET, width=None):
        self.text, self.variant, self.icon, self.shortcut = text, variant, icon, shortcut
        super().__init__(parent, height + 2 * FOCUS_PAD, width, command)

    def set(self, text=None, variant=None, icon=False, enabled=None):
        if text is not None:
            self.text = text
        if variant is not None:
            self.variant = variant
        if icon is not False:
            self.icon = icon
        if enabled is not None:
            self.enabled = bool(enabled)
            self.configure(cursor="hand2" if self.enabled else "arrow")
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.size()
        if w < 10:
            return
        v, p = self.VARIANTS[self.variant], FOCUS_PAD
        bw, bh = w - 2 * p, h - 2 * p
        solid = "grad" not in v and v["fill"] and self.variant in ("primary", "danger")
        if not self.enabled:
            _round_rect(self, p, p, w - p, h - p, RADIUS, fill=C["disabled_bg"])
            fg = C["disabled_fg"]
        else:
            fg = v["fg"]
            fill = v["press"] if self.down else v["hover"] if self.hover else v["fill"]
            if fill or v.get("border"):
                _round_rect(self, p, p, w - p, h - p, RADIUS,
                            fill=fill, outline=v.get("border"),
                            width=1 if v.get("border") else 0)
            else:
                # ghost: chỉ vẽ nền khi hover/press
                if self.hover or self.down:
                    _round_rect(self, p, p, w - p, h - p, RADIUS, fill=fill)
        self.focus_ring(w, h)
        font = TYPE["body_b"]
        tw = measure(font, self.text)
        right = 0
        if self.shortcut:
            sw = keycap_width(self.shortcut)
            x1 = w - p - px(10)
            on_dark = self.variant in ("primary", "danger") and self.enabled
            _round_rect(self, x1 - sw, h / 2 - px(12), x1, h / 2 + px(12),
                        RADIUS_SM,
                        fill=C["segment"] if not on_dark else C["accent_press"])
            self.create_text(x1 - sw / 2, h / 2, text=self.shortcut,
                             font=TYPE["small_b"],
                             fill=C["on_color"] if on_dark else C["text_2"])
            right = sw + px(14)
        x = (w - right - tw) / 2 + (p if right else 0)
        self.create_text(x, h / 2, text=self.text, fill=fg, font=font, anchor="w")


class Segmented(_Interactive):
    """Chọn một trong vài lựa chọn. options: [(key, chữ, màu chấm)]. command(key)."""

    def __init__(self, parent, options, value, command, height=px(42)):
        self.options, self.value, self.on_pick = options, value, command
        self.hot = None
        super().__init__(parent, height + 2 * FOCUS_PAD)
        self.bind("<Motion>", self._motion)
        self.bind("<Left>", lambda _e: self._step(-1))
        self.bind("<Right>", lambda _e: self._step(1))

    def set(self, value):
        self.value = value
        self.draw()

    def _index_at(self, x):
        w = self.winfo_width() - 2 * FOCUS_PAD
        return max(0, min(len(self.options) - 1,
                          int((x - FOCUS_PAD) / max(1, w) * len(self.options))))

    def _motion(self, e):
        i = self._index_at(e.x)
        if i != self.hot:
            self.hot = i
            self.draw()

    def _leave(self, e):
        self.hot = None
        super()._leave(e)

    def on_click(self, e):
        if self.enabled:
            self.on_pick(self.options[self._index_at(e.x)][0])

    def invoke(self, *_):
        return self._step(1)

    def _step(self, d):
        keys = [o[0] for o in self.options]
        if self.enabled:
            self.on_pick(keys[(keys.index(self.value) + d) % len(keys)])
        return "break"

    def draw(self):
        self.delete("all")
        w, h = self.size()
        if w < 10:
            return
        p, n, gap = FOCUS_PAD, len(self.options), px(4)
        _round_rect(self, p, p, w - p, h - p, RADIUS, fill=C["segment"])
        self.focus_ring(w, h)
        seg = (w - 2 * p - 2 * gap) / n
        for i, (key, text, dot) in enumerate(self.options):
            x0 = p + gap + i * seg
            sw, sh = int(seg), h - 2 * p - 2 * gap
            on = key == self.value
            if on:
                _round_rect(self, x0, p + gap, x0 + sw, p + gap + sh,
                            RADIUS - px(2), fill=C["surface"],
                            outline=C["border"], width=1)
            elif self.hot == i and self.enabled:
                _round_rect(self, x0, p + gap, x0 + sw, p + gap + sh,
                            RADIUS - px(2), fill=C["surface_alt"])
            font = TYPE["body_b"] if on else TYPE["body"]
            d = px(8)
            tw = measure(font, text) + (d + px(6) if on else 0)
            x = x0 + (seg - tw) / 2
            if on:
                _circle(self, x + d / 2, h / 2, d, fill=dot)
                x += d + px(6)
            self.create_text(x, h / 2, text=text, anchor="w", font=font,
                             fill=C["text"] if on else C["text_2"])


class RadioRow(_Interactive):
    """Một hàng chọn: vòng tròn + nhãn màu + tên."""

    def __init__(self, parent, key, tag, title, on_pick):
        self.key, self.tag, self.title, self.selected = key, tag, title, False
        super().__init__(parent, px(36), command=lambda: on_pick(key))

    def draw(self):
        self.delete("all")
        w, h = self.size()
        if w < 10:
            return
        if self.selected:
            _round_rect(self, 0, 0, w, h, RADIUS,
                        fill=C["accent_soft"], outline=C["accent"], width=1)
        elif self.hover and self.enabled:
            _round_rect(self, 0, 0, w, h, RADIUS, fill=C["surface_alt"])
        if self.focused:
            _round_rect(self, 0, 0, w, h, RADIUS,
                        outline=C["focus"], width=px(2))
        on_color = C["accent"] if self.enabled else C["disabled_fg"]
        d, cx, cy = px(18), px(12), h / 2
        if self.selected:
            _circle(self, cx + d / 2, cy, d, fill=on_color)
            _circle(self, cx + d / 2, cy, px(8), fill=C["surface"])
        else:
            _circle(self, cx + d / 2, cy, d, outline=C["border_ui"], width=px(1.5))
        bx = cx + d + px(10)
        bw = max(px(30), measure(TYPE["caps"], self.tag) + px(14))
        badge = BADGE.get(self.tag, C["neutral"]) if self.enabled else C["disabled_fg"]
        _round_rect(self, bx, cy - px(10), bx + bw, cy + px(10), RADIUS_SM, fill=badge)
        self.create_text(bx + bw / 2, cy, text=self.tag, fill=C["on_color"],
                         font=TYPE["caps"])
        self.create_text(bx + bw + px(10), cy, text=self.title, anchor="w",
                         font=TYPE["body_b"] if self.selected else TYPE["body"],
                         fill=C["text"] if self.enabled else C["text_3"])


class RadioList(tk.Frame):
    """Danh sách chọn một. items: [{"key","tag","title"}]. command(key). Phím ↑ ↓ đổi."""

    def __init__(self, parent, items, value, command):
        super().__init__(parent, bg=parent["bg"])
        self.value, self.command = value, command
        self.rows = []
        for it in items:
            r = RadioRow(self, it["key"], it["tag"], it["title"], command)
            r.pack(fill="x", pady=px(1))
            r.bind("<Up>", lambda _e: self._step(-1))
            r.bind("<Down>", lambda _e: self._step(1))
            self.rows.append(r)
        self.set(value)

    def _step(self, d):
        keys = [r.key for r in self.rows]
        if self.rows and self.rows[0].enabled:
            k = keys[(keys.index(self.value) + d) % len(keys)]
            self.command(k)
            self.rows[keys.index(k)].focus_set()
        return "break"

    def set(self, value):
        self.value = value
        for r in self.rows:
            r.selected = r.key == value
            r.draw()

    def set_enabled(self, on):
        for r in self.rows:
            r.set_enabled(on)


def keycap_width(text):
    return max(px(26), measure(TYPE["small_b"], text) + px(14))


def keycap(parent, text):
    """Ô phím (vd. S, ← →) cho bảng phím tắt."""
    w, h = keycap_width(text), px(24)
    cv = tk.Canvas(parent, width=w, height=h, bg=parent["bg"], highlightthickness=0)
    _round_rect(cv, 0, 0, w, h, RADIUS_SM, fill=C["segment"])
    cv.create_text(w / 2, h / 2, text=text, font=TYPE["small_b"], fill=C["text"])
    return cv


class Toggle(_Interactive):
    """Công tắc bật/tắt + nhãn. var: BooleanVar. command() gọi sau khi đổi."""

    def __init__(self, parent, var, text, command=None, shortcut=None):
        self.var, self.text, self.shortcut = var, text, shortcut
        super().__init__(parent, px(38), command=command)

    def invoke(self, *_):
        if self.enabled:
            self.var.set(not self.var.get())
            if self.command:
                self.command()
            self.draw()
        return "break"

    def draw(self):
        self.delete("all")
        w, h = self.size()
        if w < 10:
            return
        on, cy, x0 = self.var.get(), h / 2, px(4)
        tw, th = px(38), px(22)
        if on:
            _round_rect(self, x0, cy - th / 2, x0 + tw, cy + th / 2, th // 2,
                        fill=C["accent"])
        else:
            _round_rect(self, x0, cy - th / 2, x0 + tw, cy + th / 2, th // 2,
                        fill=C["segment"] if self.hover else C["surface"],
                        outline=C["border_ui"], width=px(1.5))
        k = px(16)
        kx = x0 + (tw - k - px(3) if on else px(3))
        _circle(self, kx + k / 2, cy, k,
                fill=C["surface"] if on else C["border_ui"])
        if self.focused:
            _round_rect(self, x0 - px(3), cy - th / 2 - px(3),
                        x0 + tw + px(3), cy + th / 2 + px(3),
                        th // 2 + px(3), outline=C["focus"], width=px(2))
        self.create_text(x0 + tw + px(12), cy, text=self.text, anchor="w",
                         font=TYPE["body"], fill=C["text"])
        if self.shortcut:
            kw = keycap_width(self.shortcut)
            kx = x0 + tw + px(12) + measure(TYPE["body"], self.text) + px(10)
            _round_rect(self, kx, cy - px(12), kx + kw, cy + px(12),
                        RADIUS_SM, fill=C["segment"])
            self.create_text(kx + kw / 2, cy, text=self.shortcut,
                             font=TYPE["small_b"], fill=C["text_2"])


class Tabs(tk.Frame):
    """Thanh tab chữ + gạch chân ở tab đang chọn. tabs: [(key, chữ)]. command(key)."""

    def __init__(self, parent, tabs, value, command):
        super().__init__(parent, bg=parent["bg"])
        self.items, self.value = {}, value
        for col, (key, text) in enumerate(tabs):
            self.columnconfigure(col, weight=1, uniform="tab")
            cell = tk.Frame(self, bg=self["bg"], cursor="hand2")
            cell.grid(row=0, column=col, sticky="ew")
            lab = tk.Label(cell, text=text, bg=self["bg"], font=TYPE["body_b"],
                           pady=SPACE["md"], cursor="hand2")
            lab.pack(fill="x")
            line = tk.Canvas(cell, height=px(3), width=1, bg=self["bg"],
                             highlightthickness=0)
            line.pack(fill="x")
            line.bind("<Configure>", lambda _e, k=key: self._paint(k))
            for wdg in (cell, lab):
                wdg.bind("<Button-1>", lambda _e, k=key: command(k))
                wdg.bind("<Enter>", lambda _e, k=key: self._hover(k, True))
                wdg.bind("<Leave>", lambda _e, k=key: self._hover(k, False))
            self.items[key] = (lab, line)
        tk.Frame(self, height=1, bg=C["border"]).grid(
            row=1, column=0, columnspan=len(tabs), sticky="ew")
        self.set(value)

    def _hover(self, key, on):
        if key != self.value:
            self.items[key][0].config(fg=C["text"] if on else C["text_2"])

    def _paint(self, key):
        _lab, line = self.items[key]
        line.delete("all")
        w = line.winfo_width()
        if key == self.value and w > 4:
            line.create_rectangle(0, 0, w, px(3), fill=C["accent"],
                                  outline=C["accent_2"])

    def set(self, value):
        self.value = value
        for key, (lab, _line) in self.items.items():
            lab.config(fg=C["accent_text"] if key == value else C["text_2"])
            self._paint(key)

    def set_labels(self, tabs):
        """Đổi chữ trên các tab (khi chuyển ngôn ngữ). tabs: [(key, chữ)]."""
        for key, text in tabs:
            if key in self.items:
                self.items[key][0].config(text=text)


class Card(tk.Frame):
    """Thẻ bo góc. Đặt nội dung vào `inner`."""

    def __init__(self, parent, fill=C["surface"], shadow=None, pad=0,
                 outline=None, radius=None, **_):
        super().__init__(parent, bg=parent["bg"])
        self.fill, self.outline = fill, outline
        self.radius = RADIUS + px(4) if radius is None else radius
        inset = max(pad, int(self.radius * 0.3) + 1)
        self.bgc = tk.Canvas(self, bg=parent["bg"], highlightthickness=0, bd=0)
        self.bgc.place(x=0, y=0, relwidth=1, relheight=1)
        self.inner = tk.Frame(self, bg=fill)
        self.inner.pack(fill="both", expand=True, padx=inset, pady=inset)
        self.bind("<Configure>", self._draw, add="+")

    def _draw(self, _e=None):
        w, h = self.winfo_width(), self.winfo_height()
        self.bgc.delete("all")
        if w < 10 or h < 10:
            return
        # Lùi vào 1px để nét vẽ (dày 1px) không bị cắt cụt ở mép
        inset = px(1) 
        _round_rect(self.bgc, inset, inset, w - inset, h - inset, self.radius,
                    fill=self.fill, outline=self.outline,
                    width=1 if self.outline else 0)


def section_label(parent, text, right=None):
    """Tiêu đề nhỏ viết hoa của một nhóm điều khiển; right = ghi chú bên phải."""
    row = tk.Frame(parent, bg=parent["bg"])
    tk.Label(row, text=text, bg=parent["bg"], fg=C["text_3"],
             font=TYPE["caps"]).pack(side="left")
    if right:
        tk.Label(row, text=right, bg=parent["bg"], fg=C["text_3"],
                 font=TYPE["small"]).pack(side="right")
    return row