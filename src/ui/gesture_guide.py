"""Phần "Hướng dẫn" ở bên phải cửa sổ điều khiển. Ba tab:
  Cách dùng (mặc định) | Bộ cử chỉ (4 cử chỉ: Trước / Sau, chấm tròn hoặc phím ← →) | Bộ lọc lệnh (C1–C4).
Vuốt có 2 khung tự đổi mỗi 0,5 giây; like / dislike là ảnh tĩnh.
Tranh cử chỉ (src/ui/assets/<cỡ>/*.png) được co giãn mượt, bo góc, lấy hết chỗ trống của trang.

Giao diện giữ nguyên bản paste (Card/Tabs/Button/keycap của widgets.py + render.picture).
Thêm bộ i18n VI/EN + set_lang() để control_panel.py (nút L) đổi ngôn ngữ được."""
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

# ================= Bộ cử chỉ =================
GESTURES = [
    {"key": "swipe_left", "title": "Vuốt trái",
     "how": "Mở bàn tay, đưa nhanh từ phải sang trái rồi dừng.",
     "frames": ["swipe_left_1.png", "swipe_left_2.png"]},
    {"key": "swipe_right", "title": "Vuốt phải",
     "how": "Mở bàn tay, đưa nhanh từ trái sang phải rồi dừng.",
     "frames": ["swipe_right_1.png", "swipe_right_2.png"]},
    {"key": "like", "title": "Like",
     "how": "Nắm tay, ngón cái chìa lên, giữ yên khoảng 0,6 giây.",
     "frames": ["like.png"], "command": "Vào trình chiếu"},
    {"key": "dislike", "title": "Dislike",
     "how": "Nắm tay, ngón cái chìa xuống, giữ yên khoảng 0,6 giây.",
     "frames": ["dislike.png"], "command": "Thoát trình chiếu"},
]
DEFAULT_CMD = {"swipe_left": "previous", "swipe_right": "next"}

GESTURES_EN = {
    "swipe_left": {"title": "Swipe left",
                   "how": "Open your hand and sweep it quickly from RIGHT to LEFT, then stop."},
    "swipe_right": {"title": "Swipe right",
                    "how": "Open your hand and sweep it quickly from LEFT to RIGHT, then stop."},
    "like": {"title": "Like (start slideshow)",
             "how": "Make a fist with the thumb pointing UP and hold still for about 0.6 s.",
             "command": "Start slideshow"},
    "dislike": {"title": "Dislike (exit slideshow)",
                "how": "Make a fist with the thumb pointing DOWN and hold still for about 0.6 s.",
                "command": "Exit slideshow"},
}
CMD_EN = {"next": "Next slide", "previous": "Previous slide", "play_pause": "Play / pause",
          "start_show": "Start slideshow", "exit_show": "Exit slideshow"}

# ================= Bộ lọc lệnh (C1–C4) =================
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
    "naive": ("Không lọc", "Không có Intent Gate",
              "Mốc so sánh: nhận mọi lệnh ngay, không kiểm tra gì."),
}
MODE_INFO_EN = {
    "fixed": ("C1", "Fixed threshold",
              "Accepts a command when confidence reaches the threshold and the gesture is held long enough. Threshold and hold time never change."),
    "adaptive": ("C2", "Adaptive threshold",
                 "Like C1, but the threshold rises automatically when the gesture is ambiguous (two close options, unstable label)."),
    "abstain": ("C3", "Fixed + abstention",
                "Like C1, but when still in doubt it keeps observing; if still unclear, it rejects."),
    "combined": ("C4", "Adaptive + abstention",
                 "Combines C2 and C3: the strictest, fewest false detections, but it misses more."),
    "swipe": ("Default", "Direct swipe",
              "Demo config: a swipe is accepted right away (very short hold), still with a confidence threshold and a cooldown."),
    "naive": ("No filter", "No Intent Gate",
              "Baseline: accepts every command immediately, no checks."),
}


def mode_list(current: str = None, lang: str = "vi") -> list:
    """Các bộ lọc để chọn: C1–C4, cộng thêm bộ lọc đang đặt trong config nếu nó nằm ngoài C1–C4."""
    keys = list(CHOICES)
    if current and current not in CHOICES:
        keys.insert(0, current)
    out = []
    for k in keys:
        info = MODE_INFO_EN if lang == "en" else MODE_INFO
        tag, title, desc = info.get(k) or MODE_INFO.get(k, ("Other" if lang == "en" else "Khác", k, ""))
        out.append({"key": k, "tag": tag, "title": title, "desc": desc})
    return out


# ================= Trang "Cách dùng" =================
USAGE = [
    ("1. Bắt đầu",
     ["Bấm Bắt đầu nhận cử chỉ, đứng gần camera, giơ một tay vào khung hình.",
      "Vuốt phải: slide tiếp. Vuốt trái: slide trước. Like / Dislike: vào / thoát trình chiếu."]),
    ("2. Tập trước khi trình chiếu",
     ["Chế độ Tập chỉ hiện lệnh nhận được, không bấm phím.",
      "Khi đã quen, chọn Gửi phím thật rồi bấm vào cửa sổ PowerPoint."]),
    ("3. Theo dõi khi đang chạy",
     ["Ô trạng thái nhỏ ở góc phải màn hình cho biết hệ thống đang chờ, đang giữ, hay đã nhận lệnh.",
      "Kéo để dời ô đó; chuột phải để dừng hoặc đổi chế độ."]),
]
USAGE_EN = [
    ("1. Getting started",
     ["Press Start listening, stand near the camera, raise one hand inside the frame.",
      "Swipe right: next slide. Swipe left: previous slide. Like / Dislike: start / exit slideshow."]),
    ("2. Practise before presenting",
     ["Practice mode only shows recognised commands, it sends no keys.",
      "Once comfortable, switch to Live keys and click into the PowerPoint window."]),
    ("3. Monitor while running",
     ["The small status box in the screen corner shows whether it is waiting, holding or accepting a command.",
      "Drag to move it; right-click to stop or change mode."]),
]
SHORTCUTS = [("S", "Bắt đầu / dừng"), ("M", "Tập / gửi phím thật"), ("P", "Đổi bộ lọc lệnh"),
             ("I", "Hiện / ẩn hướng dẫn"), ("C", "Hiện camera"), ("← →", "Đổi cử chỉ")]
SHORTCUTS_EN = [("S", "Start / stop"), ("M", "Practice / live keys"), ("P", "Change command filter"),
                ("I", "Show / hide guide"), ("C", "Show camera"), ("← →", "Change gesture")]

TABS = (("usage", "Cách dùng"), ("gestures", "Bộ cử chỉ"), ("modes", "Bộ lọc lệnh"))
TABS_EN = (("usage", "How to use"), ("gestures", "Gestures"), ("modes", "Modes"))

# Nhãn dùng chung
UI = {
    "vi": {"step": "Cử chỉ {i} / {n}", "usage_name": "Cách dùng",
           "modes_name": "Chế độ lọc lệnh (C1–C4)",
           "shortcuts_name": "Phím tắt", "selected": "Đang chọn",
           "prev": "Trước", "next": "Sau", "cmd": "Lệnh: ",
           "modes_intro": "Quyết định khi nào một cử chỉ được coi là lệnh."},
    "en": {"step": "Gesture {i} / {n}", "usage_name": "How to use",
           "modes_name": "Command filter modes (C1–C4)",
           "shortcuts_name": "Shortcuts", "selected": "Selected",
           "prev": "Prev", "next": "Next", "cmd": "Command: ",
           "modes_intro": "Decides when a gesture counts as a command."},
}


def gesture_text(gesture: dict, lang: str = "vi") -> dict:
    """Tiêu đề / cách làm / lệnh cố định của cử chỉ theo ngôn ngữ."""
    if lang == "en":
        return {**gesture, **GESTURES_EN.get(gesture["key"], {})}
    return gesture


def command_text(gesture: dict, labels: dict, lang: str = "vi") -> str:
    """Dòng "Lệnh: ..." của một cử chỉ."""
    prefix, names = UI[lang]["cmd"], (CMD_EN if lang == "en" else CMD_VI)
    g = gesture_text(gesture, lang)
    if g.get("command"):
        return prefix + g["command"]
    cmd = (labels or {}).get(gesture["key"]) or DEFAULT_CMD.get(gesture["key"])
    return prefix + names.get(cmd, cmd) if cmd else ""


def pick_size(avail: int) -> int:
    """Ảnh gốc nhỏ nhất đủ nét cho `avail` px (sau đó co giãn mượt)."""
    fit = [s for s in SIZES if s >= avail]
    return fit[0] if fit else SIZES[-1]


class GuidePanel:
    """Thẻ hướng dẫn, nhúng vào khung cha. show()/hide() bật tắt; mở ra ở tab "Cách dùng"; hide() dừng hoạt ảnh.
    set_lang("vi"|"en") đổi toàn bộ chữ trên panel — giao diện giữ nguyên."""

    def __init__(self, tk, parent, labels: dict = None, font: str = "TkDefaultFont",
                 policy: str = None, lang: str = "vi"):
        self.tk, self.labels, self.policy, self.lang = tk, labels or {}, policy, lang
        self.tab, self.idx, self.frame_i, self.visible, self._job = "usage", 0, 0, False, None
        self.pic_size = px(320)
        self.images = {}                          # giữ tham chiếu PhotoImage

        self.frame = Card(parent, fill_height=True)
        f = self.frame.inner

        # Ba tab: dùng Tabs của widgets
        self.tabs = Tabs(f, TABS_EN if lang == "en" else TABS, self.tab, self.select)
        self.tabs.pack(fill="x", padx=SPACE["xl"], pady=(SPACE["sm"], 0))

        self.body = tk.Frame(f, bg=C["surface"])
        # Đã giảm padding dọc (pady) từ "lg" -> "sm", "xl" -> "md" để tránh mất đáy ở tab Cách dùng
        self.body.pack(fill="both", expand=True, padx=SPACE["xl"], pady=(SPACE["sm"], SPACE["md"]))

        self.pages = {
            "usage": self._build_usage(),
            "gestures": self._build_gestures(),
            "modes": tk.Frame(self.body, bg=C["surface"]),
        }
        self.body.bind("<Configure>", lambda _e: self._resize())
        top = parent.winfo_toplevel()
        top.bind("<Left>", self._arrow, add="+")
        top.bind("<Right>", self._arrow, add="+")

    # ---------- helper ----------
    def _label(self, parent, text="", style="body", fg=None, bg=None, wrap=False, **kw):
        lab = self.tk.Label(parent, text=text, bg=bg or parent["bg"],
                            fg=fg or C["text"], font=TYPE[style], **kw)
        if wrap:
            parent.bind("<Configure>",
                        lambda e, l=lab: l.config(wraplength=max(px(160), e.width - px(4))),
                        add="+")
        return lab

    def _badge(self, parent, text, color):
        w, h = max(px(64), measure(TYPE["caps"], text) + px(16)), px(22)
        cv = self.tk.Canvas(parent, width=w, height=h, bg=parent["bg"], highlightthickness=0)
        cv.create_image(0, 0, anchor="nw", image=render.shape(cv, w, h, RADIUS_SM, fill=color))
        cv.create_text(w / 2, h / 2, text=text, font=TYPE["caps"], fill=C["on_color"])
        return cv

    # ---------- dựng trang ----------
    def _build_usage(self):
        tk = self.tk
        p = tk.Frame(self.body, bg=C["surface"])
        self.usage_title = self._label(p, UI[self.lang]["usage_name"], "title")
        self.usage_title.pack(anchor="w")
        self.usage_rows, self.usage_lines = [], []
        data = USAGE_EN if self.lang == "en" else USAGE
        for head, lines in data:
            h = self._label(p, head, "heading")
            # Giảm khoảng cách trên của mỗi mục (từ "lg" -> "md")
            h.pack(anchor="w", pady=(SPACE["md"], SPACE["xs"]))
            self.usage_rows.append(h)
            for line in lines:
                box = tk.Frame(p, bg=C["surface"])
                box.pack(fill="x")
                lab = self._label(box, line, fg=C["text_2"], justify="left",
                                  anchor="w", wrap=True)
                lab.pack(fill="x", pady=px(1))
                self.usage_lines.append(lab)
        self.shortcuts_head = self._label(p, UI[self.lang]["shortcuts_name"], "heading")
        # Giảm khoảng cách trên của "Phím tắt"
        self.shortcuts_head.pack(anchor="w", pady=(SPACE["md"], SPACE["xs"]))
        self.shortcuts_grid = tk.Frame(p, bg=C["surface"])
        self.shortcuts_grid.pack(anchor="w")
        self._draw_shortcuts()
        return p

    def _draw_shortcuts(self):
        grid = self.shortcuts_grid
        for w in grid.winfo_children():
            w.destroy()
        self.shortcut_labels = []
        sc = SHORTCUTS_EN if self.lang == "en" else SHORTCUTS
        for i, (key, what) in enumerate(sc):
            r, c = divmod(i, 2)
            keycap(grid, key).grid(row=r, column=2 * c, sticky="w",
                                   padx=(0, SPACE["sm"]), pady=px(2)) # Giảm nhẹ pady
            lab = self._label(grid, what, fg=C["text_2"])
            lab.grid(row=r, column=2 * c + 1, sticky="w", padx=(0, SPACE["md"])) # Giảm nhẹ padx
            self.shortcut_labels.append(lab)

    def _build_gestures(self):
        tk = self.tk
        p = tk.Frame(self.body, bg=C["surface"])
        
        # --- HEADER: Tên cử chỉ & Chấm tròn (Đã bỏ dòng step "Cử chỉ i/n") ---
        head = tk.Frame(p, bg=C["surface"])
        head.pack(fill="x", pady=(0, SPACE["xs"]))
        
        self.name = self._label(head, "", "title")
        self.name.pack(side="left")
        
        self.dots = tk.Frame(head, bg=C["surface"])
        self.dots.pack(side="right")
        self.dot_items = []
        for i in range(len(GESTURES)):
            d = tk.Canvas(self.dots, width=px(20), height=px(20),
                          bg=C["surface"], highlightthickness=0, cursor="hand2")
            d.pack(side="left")
            d.bind("<Button-1>", lambda _e, k=i: self._goto(k))
            self.dot_items.append(d)
            
        # --- CMD: Lệnh ---
        self.cmd = self._label(p, "", "body_b", fg=C["accent_text"])
        self.cmd.pack(anchor="w", pady=(0, SPACE["md"])) # Căn trái (anchor="w")
        
        # --- PIC: Ảnh minh họa ---
        self.pic = tk.Label(p, bg=C["surface"], bd=0)
        self.pic.pack(pady=SPACE["sm"], expand=True)
        
        # --- BOX: Hướng dẫn làm ---
        box = tk.Frame(p, bg=C["surface"])
        box.pack(fill="x")
        # how.canvas = ... (căn trái, bỏ justify="center")
        self.how = self._label(box, "", fg=C["text_2"], justify="center", anchor="w", wrap=True)
        self.how.pack(fill="x", anchor="w")
        
        # --- NAV: Nút Trước / Sau ---
        self.nav = tk.Frame(p, bg=C["surface"])
        self.nav.pack(pady=(SPACE["md"], 0))
        self.prev_btn = Button(self.nav, UI[self.lang]["prev"], lambda: self.go(-1),
                               variant="secondary", width=px(136), shortcut="←")
        self.prev_btn.pack(side="left", padx=SPACE["xs"])
        self.next_btn = Button(self.nav, UI[self.lang]["next"], lambda: self.go(1),
                               variant="primary", width=px(136), shortcut="→")
        self.next_btn.pack(side="left", padx=SPACE["xs"])
        return p

    def _fill_modes(self):
        tk, p = self.tk, self.pages["modes"]
        for w in p.winfo_children():
            w.destroy()
            
        self._label(p, UI[self.lang]["modes_name"], "title").pack(anchor="w")
        # Giảm pady dưới của dòng giới thiệu
        self._label(p, UI[self.lang]["modes_intro"], fg=C["text_3"],
                    style="small").pack(anchor="w", pady=(SPACE["xs"], SPACE["sm"]))
        
        for m in mode_list(self.policy, self.lang):
            on = m["key"] == self.policy
            bg = C["accent_soft"] if on else C["surface"]
            
            wrapper = tk.Frame(p, bg=C["surface"])
            # Giảm khoảng cách giữa các thẻ từ SPACE["sm"] (8px) xuống px(4)
            wrapper.pack(fill="x", pady=(0, px(4)))
            
            # Giảm pad bên trong thẻ từ SPACE["md"] (12px) xuống SPACE["sm"] (8px)
            # Giảm radius cho bớt bo tròn to
            card = Card(wrapper, fill=bg, shadow=None,
                        outline=C["accent"] if on else C["border"],
                        pad=SPACE["sm"], radius=px(8))
            card.pack(fill="x", padx=px(1)) 
            
            row = card.inner
            # Thu gọn khoảng cách từ Badge sang phần chữ
            self._badge(row, m["tag"], BADGE.get(m["tag"], C["neutral"])).pack(
                side="left", anchor="n", padx=(0, SPACE["sm"]))
                
            text = tk.Frame(row, bg=bg)
            text.pack(side="left", fill="x", expand=True)
            
            head = tk.Frame(text, bg=bg)
            head.pack(fill="x")
            self._label(head, m["title"], "body_b").pack(side="left")
            if on:
                self._label(head, UI[self.lang]["selected"], "small_b",
                            fg=C["accent_text"]).pack(side="right")
            
            # Thêm chút khoảng cách nhỏ (px(2)) giữa title và desc để không bị dính chữ
            self._label(text, m["desc"], "small", fg=C["text_2"],
                        justify="left", anchor="w", wrap=True).pack(fill="x", pady=(px(2), 0))

    # ---------- điều hướng ----------
    def _arrow(self, event) -> None:
        if self.visible and self.tab == "gestures":
            self.go(-1 if event.keysym == "Left" else 1)

    def set_lang(self, lang: str) -> None:
        if lang == self.lang:
            return
        self.lang = lang
        # 1) tab
        if hasattr(self.tabs, "set_labels"):
            self.tabs.set_labels(TABS_EN if lang == "en" else TABS)
        else:
            for key, text in (TABS_EN if lang == "en" else TABS):
                lab, _line = self.tabs.items[key]
                lab.config(text=text)
        # 2) nút Trước / Sau
        try:
            self.prev_btn.set(text=UI[lang]["prev"])
            self.next_btn.set(text=UI[lang]["next"])
        except Exception:
            pass
        # 3) trang Cách dùng
        self.usage_title.config(text=UI[lang]["usage_name"])
        data = USAGE_EN if lang == "en" else USAGE
        for h, (head, _lines) in zip(self.usage_rows, data):
            h.config(text=head)
        flat = [line for _h, lines in data for line in lines]
        for lab, txt in zip(self.usage_lines, flat):
            lab.config(text=txt)
        self.shortcuts_head.config(text=UI[lang]["shortcuts_name"])
        self._draw_shortcuts()
        # 4) vẽ lại trang đang mở
        if self.visible:
            self._refresh()

    def set_policy(self, key: str) -> None:
        self.policy = key
        if self.visible and self.tab == "modes":
            self._refresh()

    # ---------- bật / tắt ----------
    def show(self, grid: dict = None, **pack) -> None:
        if grid is not None:
            self.frame.grid(**grid)
        else:
            self.frame.pack(fill="both", expand=True, **pack)
        self.visible = True
        self.tab, self.idx = "usage", 0
        self._refresh()

    def hide(self) -> None:
        self._cancel()
        self.frame.grid_forget()
        self.frame.pack_forget()
        self.visible = False

    # ---------- chọn trang ----------
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
            g = gesture_text(GESTURES[self.idx], self.lang)
            # Đã bỏ self.step.config(...)
            for i, d in enumerate(self.dot_items):
                d.delete("all")
                img = (render.circle(d, px(10), fill=C["accent"]) if i == self.idx
                       else render.circle(d, px(10), outline=C["border_ui"],
                                          width=px(1.5)))
                d.create_image(px(10), px(10), image=img)
            self.name.config(text=g["title"])
            self.cmd.config(text=command_text(GESTURES[self.idx],
                                             self.labels, self.lang))
            self.how.config(text=g["how"])
            self._draw()
            self.frame.after_idle(self._resize)

    def _draw(self) -> None:
        if self.tab != "gestures":
            return
        g = GESTURES[self.idx]
        src = ASSETS / str(pick_size(self.pic_size)) / g["frames"][self.frame_i]
        try:
            self.pic.config(image=render.picture(self.pic, src, self.pic_size,
                                                 RADIUS + px(6)))
        except Exception:
            self.pic.config(image="", text=g["title"],
                            font=TYPE["body_b"], fg=C["text_3"])
        if len(g["frames"]) > 1 and self.visible:
            self.frame_i = (self.frame_i + 1) % len(g["frames"])
            self._job = self.frame.after(FRAME_MS, self._draw)

    def _cancel(self) -> None:
        if self._job:
            self.frame.after_cancel(self._job)
            self._job = None

    def _resize(self) -> None:
        if self.tab != "gestures" or not self.visible:
            return
        page = self.pages["gestures"]
        page.update_idletasks()
        other = (page.winfo_reqheight()
                 - self.pic.winfo_reqheight() - 2 * SPACE["md"])
        avail = min(self.body.winfo_height() - other - 2 * SPACE["md"],
                    self.body.winfo_width())
        new = max(PIC_MIN, min(PIC_MAX, avail // PIC_STEP * PIC_STEP))
        if new != self.pic_size:
            self.pic_size = new
            self._cancel()
            self._draw()