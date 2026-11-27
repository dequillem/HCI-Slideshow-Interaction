"""Phần "Hướng dẫn" ở bên phải cửa sổ điều khiển. Ba tab:
  Cách dùng (mặc định) | Bộ cử chỉ (4 cử chỉ: Trước / Sau, chấm tròn hoặc phím ← →) | Bộ lọc lệnh (C1–C4).
Vuốt có 2 khung tự đổi mỗi 0,5 giây; like / dislike là ảnh tĩnh.
Tranh cử chỉ (src/ui/assets/<cỡ>/*.png) được co giãn mượt, bo góc, lấy hết chỗ trống của trang."""
from __future__ import annotations

from pathlib import Path

from . import render
from .status_model import CMD_VI
from .theme import BADGE, C, RADIUS, RADIUS_SM, SPACE, TYPE, px
from .widgets import Button, Card, Tabs, keycap, measure

ASSETS = Path(__file__).parent / "assets"
SIZES = (360, 480)             # các cỡ ảnh gốc có sẵn (px)
PIC_MIN, PIC_MAX, PIC_STEP = px(200), px(520), px(20)
FRAME_MS = 500                 # mỗi khung của cử chỉ động hiện 0,5 giây

# key (khớp nhãn model / external_labels), tiêu đề, cách làm, các khung ảnh
GESTURES = [
    {"key": "swipe_left", "title": "Vuốt trái",
     "how": "Mở bàn tay, đưa nhanh từ phải sang trái rồi dừng.", "frames": ["swipe_left_1.png", "swipe_left_2.png"]},
    {"key": "swipe_right", "title": "Vuốt phải",
     "how": "Mở bàn tay, đưa nhanh từ trái sang phải rồi dừng.", "frames": ["swipe_right_1.png", "swipe_right_2.png"]},
    {"key": "like", "title": "Like",
     "how": "Nắm tay, ngón cái chìa lên, giữ yên khoảng 0,6 giây.", "frames": ["like.png"], "command": "Vào trình chiếu"},
    {"key": "dislike", "title": "Dislike",
     "how": "Nắm tay, ngón cái chìa xuống, giữ yên khoảng 0,6 giây.", "frames": ["dislike.png"], "command": "Thoát trình chiếu"},
]
DEFAULT_CMD = {"swipe_left": "previous", "swipe_right": "next"}   # dùng khi config không có external_labels

# Bộ lọc lệnh (Intent Gate policy): tag, tên ngắn, mô tả.
CHOICES = ("fixed", "adaptive", "abstain", "combined")
MODE_INFO = {
    "fixed": ("C1", "Ngưỡng cố định",
              "Nhận lệnh khi độ tin cậy đạt ngưỡng và cử chỉ được giữ đủ lâu. Ngưỡng và thời gian giữ không đổi."),
    "adaptive": ("C2", "Ngưỡng thích ứng",
                 "Như C1, nhưng ngưỡng tự tăng khi cử chỉ mơ hồ (hai lựa chọn sát nhau, nhãn chưa ổn định)."),
    "abstain": ("C3", "Cố định + chưa chắc",
                "Như C1, nhưng khi còn nghi ngờ (chưa đủ chắc, vừa thấy chiều ngược) thì quan sát thêm; vẫn không rõ thì từ chối."),
    "combined": ("C4", "Thích ứng + chưa chắc",
                 "Kết hợp C2 và C3: chặt nhất, ít nhận nhầm nhất, đổi lại dễ bỏ sót hơn."),
    "swipe": ("Mặc định", "Vuốt trực tiếp",
              "Cấu hình demo: vuốt được nhận ngay (giữ rất ngắn), vẫn có ngưỡng tin cậy và thời gian nghỉ."),
    "naive": ("Không lọc", "Không có Intent Gate", "Mốc so sánh: nhận mọi lệnh ngay, không kiểm tra gì."),
}


def mode_list(current: str = None) -> list:
    """Các bộ lọc để chọn: C1–C4, cộng thêm bộ lọc đang đặt trong config nếu nó nằm ngoài C1–C4 (vd swipe mặc định)."""
    keys = list(CHOICES)
    if current and current not in CHOICES:
        keys.insert(0, current)
    out = []
    for k in keys:
        tag, title, desc = MODE_INFO.get(k, ("Khác", k, ""))
        out.append({"key": k, "tag": tag, "title": title, "desc": desc})
    return out


# Trang "Cách dùng": (tiêu đề mục, [dòng])
USAGE = [
    ("1. Bắt đầu", ["Bấm Bắt đầu nhận cử chỉ, đứng gần camera, giơ một tay vào khung hình.",
                    "Vuốt phải: slide tiếp. Vuốt trái: slide trước. Like / Dislike: vào / thoát trình chiếu."]),
    ("2. Tập trước khi trình chiếu", ["Chế độ Tập chỉ hiện lệnh nhận được, không bấm phím.",
                                       "Khi đã quen, chọn Gửi phím thật rồi bấm vào cửa sổ PowerPoint."]),
    ("3. Theo dõi khi đang chạy", ["Ô trạng thái nhỏ ở góc phải màn hình cho biết hệ thống đang chờ, đang giữ, hay đã nhận lệnh.",
                                    "Kéo để dời ô đó; chuột phải để dừng hoặc đổi chế độ."]),
]
SHORTCUTS = [("S", "Bắt đầu / dừng"), ("M", "Tập / gửi phím thật"), ("P", "Đổi bộ lọc lệnh"),
             ("I", "Hiện / ẩn hướng dẫn"), ("C", "Hiện camera"), ("← →", "Đổi cử chỉ")]

TABS = (("usage", "Cách dùng"), ("gestures", "Bộ cử chỉ"), ("modes", "Bộ lọc lệnh"))


def command_text(gesture: dict, labels: dict) -> str:
    """Lệnh của một cử chỉ: lấy từ external_labels trong config (vuốt) hoặc ghi chú cố định (like/dislike)."""
    if gesture.get("command"):
        return gesture["command"]
    cmd = (labels or {}).get(gesture["key"]) or DEFAULT_CMD.get(gesture["key"])
    return CMD_VI.get(cmd, cmd) if cmd else ""


def pick_size(avail: int) -> int:
    """Ảnh gốc nhỏ nhất đủ nét cho `avail` px (sau đó co giãn mượt)."""
    fit = [s for s in SIZES if s >= avail]
    return fit[0] if fit else SIZES[-1]


class GuidePanel:
    """Thẻ hướng dẫn, nhúng vào khung cha. show()/hide() bật tắt; mở ra ở tab "Cách dùng"; hide() dừng hoạt ảnh."""

    def __init__(self, tk, parent, labels: dict = None, font: str = None, policy: str = None):
        self.tk, self.labels, self.policy = tk, labels or {}, policy
        self.tab, self.idx, self.frame_i, self.visible, self._job = "usage", 0, 0, False, None
        self.pic_size = px(320)
        self.frame = Card(parent, fill_height=True)
        f = self.frame.inner
        self.tabs = Tabs(f, TABS, self.tab, self.select)
        self.tabs.pack(fill="x", padx=SPACE["xl"], pady=(SPACE["sm"], 0))
        self.body = tk.Frame(f, bg=C["surface"])
        self.body.pack(fill="both", expand=True, padx=SPACE["xl"], pady=(SPACE["lg"], SPACE["xl"]))
        self.pages = {"usage": self._build_usage(), "gestures": self._build_gestures(), "modes": tk.Frame(self.body, bg=C["surface"])}
        self.body.bind("<Configure>", lambda _e: self._resize())
        top = parent.winfo_toplevel()
        top.bind("<Left>", self._arrow, add="+")
        top.bind("<Right>", self._arrow, add="+")

    # ---------- dựng trang ----------
    def _label(self, parent, text="", style="body", fg=None, bg=None, wrap=False, **kw):
        lab = self.tk.Label(parent, text=text, bg=bg or parent["bg"], fg=fg or C["text"], font=TYPE[style], **kw)
        if wrap:   # ngắt dòng theo độ rộng thật của khung chứa
            parent.bind("<Configure>", lambda e, l=lab: l.config(wraplength=max(px(160), e.width - px(4))), add="+")
        return lab

    def _badge(self, parent, text, color):
        w, h = max(px(64), measure(TYPE["caps"], text) + px(16)), px(22)
        cv = self.tk.Canvas(parent, width=w, height=h, bg=parent["bg"], highlightthickness=0)
        cv.create_image(0, 0, anchor="nw", image=render.shape(cv, w, h, RADIUS_SM, fill=color))
        cv.create_text(w / 2, h / 2, text=text, font=TYPE["caps"], fill=C["on_color"])
        return cv

    def _build_usage(self):
        tk = self.tk
        p = tk.Frame(self.body, bg=C["surface"])
        self._label(p, "Cách dùng", "title").pack(anchor="w")
        for head, lines in USAGE:
            self._label(p, head, "heading").pack(anchor="w", pady=(SPACE["lg"], SPACE["xs"]))
            for line in lines:
                box = tk.Frame(p, bg=C["surface"])
                box.pack(fill="x")
                self._label(box, line, fg=C["text_2"], justify="left", anchor="w", wrap=True).pack(fill="x", pady=px(1))
        self._label(p, "Phím tắt", "heading").pack(anchor="w", pady=(SPACE["xl"], SPACE["sm"]))
        grid = tk.Frame(p, bg=C["surface"])
        grid.pack(anchor="w")
        for i, (key, what) in enumerate(SHORTCUTS):
            r, c = divmod(i, 2)
            keycap(grid, key).grid(row=r, column=2 * c, sticky="w", padx=(0, SPACE["sm"]), pady=SPACE["xs"])
            self._label(grid, what, fg=C["text_2"]).grid(row=r, column=2 * c + 1, sticky="w", padx=(0, SPACE["xl"]))
        return p

    def _build_gestures(self):
        tk = self.tk
        p = tk.Frame(self.body, bg=C["surface"])
        head = tk.Frame(p, bg=C["surface"])
        head.pack(fill="x")
        self.name = self._label(head, "", "title")
        self.name.pack(side="left")
        self.dots = tk.Frame(head, bg=C["surface"])
        self.dots.pack(side="right")
        self.dot_items = []
        for i in range(len(GESTURES)):
            d = tk.Canvas(self.dots, width=px(20), height=px(20), bg=C["surface"], highlightthickness=0, cursor="hand2")
            d.pack(side="left")
            d.bind("<Button-1>", lambda _e, k=i: self._goto(k))
            self.dot_items.append(d)
        self.cmd = self._label(p, "", "body_b", fg=C["accent_text"])
        self.cmd.pack(anchor="w", pady=(SPACE["xs"], 0))
        self.pic = tk.Label(p, bg=C["surface"], bd=0)
        self.pic.pack(pady=SPACE["md"], expand=True)
        box = tk.Frame(p, bg=C["surface"])
        box.pack(fill="x")
        self.how = self._label(box, "", fg=C["text_2"], justify="center", wrap=True)
        self.how.pack(fill="x")
        nav = tk.Frame(p, bg=C["surface"])
        nav.pack(pady=(SPACE["lg"], 0))
        Button(nav, "Trước", lambda: self.go(-1), variant="secondary", width=px(136), shortcut="←").pack(side="left", padx=SPACE["xs"])
        Button(nav, "Sau", lambda: self.go(1), variant="primary", width=px(136), shortcut="→").pack(side="left", padx=SPACE["xs"])
        return p

    def _fill_modes(self):
        """Trang Bộ lọc lệnh dựng lại mỗi lần mở (bộ lọc đang chọn có thể đã đổi)."""
        tk, p = self.tk, self.pages["modes"]
        for w in p.winfo_children():
            w.destroy()
        self._label(p, "Bộ lọc lệnh", "title").pack(anchor="w")
        self._label(p, "Quyết định khi nào một cử chỉ được coi là lệnh. Đổi ở thanh bên khi chưa chạy.",
                    fg=C["text_3"], style="small").pack(anchor="w", pady=(SPACE["xs"], SPACE["md"]))
        for m in mode_list(self.policy):
            on = m["key"] == self.policy
            bg = C["accent_soft"] if on else C["surface"]
            card = Card(p, fill=bg, shadow=None, outline=C["accent"] if on else C["border"], pad=SPACE["md"], radius=RADIUS)
            card.pack(fill="x", pady=SPACE["xs"])
            row = card.inner
            self._badge(row, m["tag"], BADGE.get(m["tag"], C["neutral"])).pack(side="left", anchor="n", padx=(0, SPACE["md"]))
            text = tk.Frame(row, bg=bg)
            text.pack(side="left", fill="x", expand=True)
            head = tk.Frame(text, bg=bg)
            head.pack(fill="x")
            self._label(head, m["title"], "body_b").pack(side="left")
            if on:
                self._label(head, "Đang chọn", "small_b", fg=C["accent_text"]).pack(side="right")
            self._label(text, m["desc"], "small", fg=C["text_2"], justify="left", anchor="w", wrap=True).pack(fill="x")

    # ---------- điều hướng ----------
    def _arrow(self, event) -> None:
        if self.visible and self.tab == "gestures":
            self.go(-1 if event.keysym == "Left" else 1)

    def set_policy(self, key: str) -> None:
        self.policy = key
        if self.visible and self.tab == "modes":
            self._refresh()

    def show(self, **pack) -> None:
        self.frame.pack(fill="both", expand=True, **pack)
        self.visible = True
        self.tab, self.idx = "usage", 0
        self._refresh()

    def hide(self) -> None:
        self._cancel()
        self.frame.pack_forget()
        self.visible = False

    def select(self, tab: str) -> None:
        self.tab = tab
        self._refresh()

    def go(self, step: int) -> None:
        if self.tab != "gestures":
            return
        self._goto((self.idx + step) % len(GESTURES))

    def _goto(self, i: int) -> None:
        self.idx = i
        self._refresh()

    def _refresh(self) -> None:
        self._cancel()
        self.tabs.set(self.tab)
        for key, page in self.pages.items():
            if key != self.tab:
                page.pack_forget()
        if self.tab == "modes":
            self._fill_modes()
        self.pages[self.tab].pack(fill="both", expand=True)
        self.frame_i = 0
        if self.tab == "gestures":
            g = GESTURES[self.idx]
            for i, d in enumerate(self.dot_items):
                d.delete("all")
                img = (render.circle(d, px(10), fill=C["accent"]) if i == self.idx
                       else render.circle(d, px(10), outline=C["border_ui"], width=px(1.5)))
                d.create_image(px(10), px(10), image=img)
            self.name.config(text=g["title"])
            self.cmd.config(text="Lệnh: " + command_text(g, self.labels))
            self.how.config(text=g["how"])
            self._draw()
            self.frame.after_idle(self._resize)     # cỡ ảnh chỉ tính được khi trang cử chỉ đang hiện

    def _draw(self) -> None:
        if self.tab != "gestures":
            return
        g = GESTURES[self.idx]
        src = ASSETS / str(pick_size(self.pic_size)) / g["frames"][self.frame_i]
        self.pic.config(image=render.picture(self.pic, src, self.pic_size, RADIUS + px(6)))
        if len(g["frames"]) > 1 and self.visible:
            self.frame_i = (self.frame_i + 1) % len(g["frames"])
            self._job = self.frame.after(FRAME_MS, self._draw)

    def _cancel(self) -> None:
        if self._job:
            self.frame.after_cancel(self._job)
            self._job = None

    def _resize(self) -> None:
        """Tranh cử chỉ lấy hết chỗ còn trống của trang (theo bước PIC_STEP để không vẽ lại liên tục)."""
        if self.tab != "gestures" or not self.visible:
            return
        page = self.pages["gestures"]
        page.update_idletasks()
        other = page.winfo_reqheight() - self.pic.winfo_reqheight() - 2 * SPACE["md"]
        avail = min(self.body.winfo_height() - other - 2 * SPACE["md"], self.body.winfo_width())
        new = max(PIC_MIN, min(PIC_MAX, avail // PIC_STEP * PIC_STEP))
        if new != self.pic_size:
            self.pic_size = new
            self._cancel()
            self._draw()
