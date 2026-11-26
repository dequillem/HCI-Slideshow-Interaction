"""Phần "Hướng dẫn" nằm TRONG cửa sổ điều khiển (không mở cửa sổ mới). Ba nút ở đỉnh chọn trang:
  Cách dùng (mặc định khi mở) | Bộ cử chỉ (4 cử chỉ, đổi bằng Trước / Sau hoặc phím ← →) | Chế độ (bộ lọc C1–C4).
Vuốt có 2 khung tự đổi mỗi 0,5 giây; like / dislike là ảnh tĩnh; Cách dùng và Chế độ là chữ.

Ảnh vẽ sẵn 4 cỡ (src/ui/assets/<cỡ>/*.png). Cửa sổ càng lớn (phóng to kín màn hình) thì chọn ảnh càng to, vẫn nét,
không cần thư viện ảnh (Tk đọc thẳng PNG)."""
from __future__ import annotations

from pathlib import Path

from .status_model import CMD_VI
COLOR = {"card": "#ffffff", "border": "#d1d5db", "text": "#111827", "muted": "#4b5563"}

ASSETS = Path(__file__).parent / "assets"
SIZES = (360, 480)   # các cỡ ảnh có sẵn (px)
FRAME_MS = 500                 # mỗi khung của cử chỉ động hiện 0,5 giây

# key (khớp nhãn model / external_labels), tiêu đề, cách làm, các khung ảnh
GESTURES = [
    {"key": "swipe_left", "title": "Vuốt trái",
     "how": "Mở bàn tay, đưa nhanh từ PHẢI sang TRÁI rồi dừng.", "frames": ["swipe_left_1.png", "swipe_left_2.png"]},
    {"key": "swipe_right", "title": "Vuốt phải",
     "how": "Mở bàn tay, đưa nhanh từ TRÁI sang PHẢI rồi dừng.", "frames": ["swipe_right_1.png", "swipe_right_2.png"]},
    {"key": "like", "title": "Like (vào trình chiếu)",
     "how": "Nắm tay, ngón cái chìa LÊN, giữ yên khoảng 0,6 giây.", "frames": ["like.png"],
     "command": "Vào chế độ trình chiếu"},
    {"key": "dislike", "title": "Dislike (thoát trình chiếu)",
     "how": "Nắm tay, ngón cái chìa XUỐNG, giữ yên khoảng 0,6 giây.", "frames": ["dislike.png"],
     "command": "Thoát chế độ trình chiếu"},
]
DEFAULT_CMD = {"swipe_left": "previous", "swipe_right": "next"}   # dùng khi config không có external_labels

# ===== Bản tiếng Anh (bản tiếng Việt ở trên giữ nguyên; thêm ngôn ngữ nào thì thêm một bộ bảng như dưới đây) =====
CMD_EN = {"next": "Next slide", "previous": "Previous slide", "play_pause": "Play / pause",
          "start_show": "Start slideshow", "exit_show": "Exit slideshow"}
GESTURES_EN = {
    "swipe_left": {"title": "Swipe left", "how": "Open your hand and sweep it quickly from RIGHT to LEFT, then stop."},
    "swipe_right": {"title": "Swipe right", "how": "Open your hand and sweep it quickly from LEFT to RIGHT, then stop."},
    "like": {"title": "Like (start slideshow)", "how": "Make a fist with the thumb pointing UP and hold still for about 0.6 s.",
             "command": "Start slideshow"},
    "dislike": {"title": "Dislike (exit slideshow)", "how": "Make a fist with the thumb pointing DOWN and hold still for about 0.6 s.",
                "command": "Exit slideshow"},
}
UI = {
    "vi": {"step": "Cử chỉ {i} / {n}", "usage_name": "Cách dùng", "modes_name": "Chế độ lọc lệnh (C1–C4)",
           "prev": "‹ Trước", "next": "Sau ›", "cmd": "Lệnh: "},
    "en": {"step": "Gesture {i} / {n}", "usage_name": "How to use", "modes_name": "Command filter modes (C1–C4)",
           "prev": "‹ Prev", "next": "Next ›", "cmd": "Command: "},
}

# Bộ lọc lệnh (Intent Gate policy): tag, tên ngắn, mô tả. C1–C4 chọn được bằng nút "Bộ lọc" trong giao diện.
CHOICES = ("fixed", "adaptive", "abstain", "combined")
MODE_INFO = {
    "fixed": ("C1", "Ngưỡng cố định",
              "Nhận lệnh khi độ tin cậy đạt ngưỡng và cử chỉ được giữ đủ lâu. Ngưỡng và thời gian giữ không đổi."),
    "adaptive": ("C2", "Ngưỡng thích ứng",
                 "Như C1, nhưng khi tay di chuyển nhanh thì ngưỡng và thời gian giữ tự tăng lên, nên khó nhận nhầm hơn."),
    "abstain": ("C3", "Cố định + từ chối",
                "Như C1, nhưng khi hai cử chỉ có xác suất sát nhau thì hệ thống coi là chưa chắc và bỏ qua."),
    "combined": ("C4", "Thích ứng + từ chối",
                 "Kết hợp C2 và C3: chặt nhất, ít nhận nhầm nhất, đổi lại dễ bỏ sót hơn."),
    "swipe": ("Mặc định", "Vuốt trực tiếp",
              "Không cần cử chỉ kích hoạt: vuốt được nhận ngay (giữ rất ngắn), vẫn có ngưỡng tin cậy và thời gian nghỉ."),
    "naive": ("Không lọc", "Không có Intent Gate", "Mốc so sánh: nhận mọi lệnh ngay, không kiểm tra gì."),
}


MODE_INFO_EN = {
    "fixed": ("C1", "Fixed threshold",
              "Accepts a command when confidence reaches the threshold and the gesture is held long enough. Threshold and hold time never change."),
    "adaptive": ("C2", "Adaptive threshold",
                 "Like C1, but when the hand moves fast the threshold and hold time increase automatically, so false detections are rarer."),
    "abstain": ("C3", "Fixed + abstention",
                "Like C1, but when two gestures have close probabilities the system treats it as uncertain and ignores it."),
    "combined": ("C4", "Adaptive + abstention",
                 "Combines C2 and C3: the strictest, fewest false detections, but it misses more."),
    "swipe": ("Default", "Direct swipe",
              "No activation gesture needed: a swipe is accepted right away (very short hold), still with a confidence threshold and a cooldown."),
    "naive": ("No filter", "No Intent Gate", "Baseline: accepts every command immediately, no checks."),
}


def mode_list(current: str = None, lang: str = "vi") -> list:
    """Các bộ lọc để chọn: C1–C4, cộng thêm bộ lọc đang đặt trong config nếu nó nằm ngoài C1–C4 (vd swipe mặc định)."""
    keys = list(CHOICES)
    if current and current not in CHOICES:
        keys.insert(0, current)
    out = []
    for k in keys:
        info = MODE_INFO_EN if lang == "en" else MODE_INFO
        tag, title, desc = info.get(k) or MODE_INFO.get(k, ("Khác" if lang != "en" else "Other", k, ""))
        out.append({"key": k, "tag": tag, "title": title, "desc": desc})
    return out


USAGE_TEXT = (
    "Chế độ TẬP / GỬI THẬT (phím M)\n"
    "• TẬP: nhận cử chỉ nhưng không gửi phím, dùng để làm quen.\n"
    "• GỬI THẬT: phím gửi vào cửa sổ đang được chọn, hãy bấm vào PowerPoint đang trình chiếu.\n\n"
    "Cửa sổ trạng thái nhỏ (hiện khi đang chạy)\n"
    "• Kéo để dời, chuột phải để dừng hoặc đổi chế độ.\n\n"
    "Phím tắt\n"
    "S bắt đầu / dừng · M tập / gửi thật · P bộ lọc lệnh · G hướng dẫn · C camera · ← → chuyển cử chỉ (tab Bộ cử chỉ)"
)

USAGE_TEXT_EN = (
    "PRACTICE / LIVE mode (key M)\n"
    "• PRACTICE: gestures are recognised but no keys are sent, use it to get familiar.\n"
    "• LIVE: keys go to the currently selected window, so click the PowerPoint that is presenting.\n\n"
    "Small status window (shown while running)\n"
    "• Drag to move it, right-click to stop or change mode.\n\n"
    "Shortcuts\n"
    "S start / stop · M practice / live · P command filter · G guide · C camera · L language · ← → switch gesture (Gestures tab)"
)

TABS = (("usage", "Cách dùng"), ("gestures", "Bộ cử chỉ"), ("modes", "Chế độ"))   # ba nút ở đỉnh phần hướng dẫn
TABS_EN = (("usage", "How to use"), ("gestures", "Gestures"), ("modes", "Modes"))
TAB_ACCENT = "#5b3df5"  # màu gạch nhấn dưới tab đang chọn
TAB_TEXT = "#111827"


def gesture_text(gesture: dict, lang: str = "vi") -> dict:
    """Tiêu đề / cách làm / lệnh cố định của cử chỉ theo ngôn ngữ (thiếu bản dịch thì dùng tiếng Việt)."""
    if lang == "en":
        return {**gesture, **GESTURES_EN.get(gesture["key"], {})}
    return gesture


def command_text(gesture: dict, labels: dict, lang: str = "vi") -> str:
    """Dòng "Lệnh: ..." của một cử chỉ: lấy từ external_labels trong config (vuốt) hoặc ghi chú cố định (like/dislike)."""
    prefix, names = UI[lang]["cmd"], (CMD_EN if lang == "en" else CMD_VI)
    g = gesture_text(gesture, lang)
    if g.get("command"):
        return prefix + g["command"]
    cmd = (labels or {}).get(gesture["key"]) or DEFAULT_CMD.get(gesture["key"])
    return prefix + names.get(cmd, cmd) if cmd else ""


def pick_size(avail: int) -> int:
    """Cỡ ảnh lớn nhất không vượt `avail` px (tối thiểu cỡ nhỏ nhất)."""
    fit = [s for s in SIZES if s <= avail]
    return fit[-1] if fit else SIZES[0]


class GuidePanel:
    """Khung hướng dẫn, nhúng vào cửa sổ cha. show()/hide() bật tắt; mở ra luôn ở tab "Cách dùng"; hide() dừng hoạt ảnh."""

    def __init__(self, tk, parent, labels: dict = None, font: str = "TkDefaultFont", policy: str = None, lang: str = "vi"):
        self.tk, self.labels, self.policy, self.lang = tk, labels or {}, policy, lang
        self.tab, self.idx, self.frame_i, self.size, self.visible, self._job = "usage", 0, 0, SIZES[0], False, None
        self.images = {}                          # giữ tham chiếu PhotoImage, nếu không Tk sẽ xóa ảnh
        card = COLOR["card"]
        f = self.frame = tk.Frame(parent, bg=card, highlightthickness=1, highlightbackground=COLOR["border"])
        bar = tk.Frame(f, bg=card)                # ba nút chọn trang
        bar.pack(fill="x", padx=10, pady=(10, 0))
        self.tab_btns = {}
        self.tab_indicators = {}
        for col, (key, text) in enumerate(TABS_EN if lang == "en" else TABS):
            bar.columnconfigure(col, weight=1, uniform="tab")
            cell = tk.Frame(bar, bg=card)
            cell.grid(row=0, column=col, sticky="ew", padx=2)
            cell.columnconfigure(0, weight=1)
            b = tk.Button(cell, text=text, font=(font, 10, "bold"), bd=0, relief="flat",
                          cursor="hand2", pady=8, bg=card, fg=TAB_TEXT,
                          activebackground=card, activeforeground=TAB_ACCENT,
                          command=lambda k=key: self.select(k))
            b.grid(row=0, column=0, sticky="ew")
            indicator = tk.Frame(cell, bg=card, height=3)
            indicator.grid(row=1, column=0, sticky="ew")
            self.tab_btns[key] = b
            self.tab_indicators[key] = indicator
        self.step = tk.Label(f, bg=card, fg=COLOR["muted"], font=(font, 9))
        self.step.pack(pady=(8, 0))
        self.name = tk.Label(f, bg=card, fg=COLOR["text"], font=(font, 14, "bold"))
        self.name.pack()
        self.pic = tk.Label(f, bg=card)
        self.pic.pack(padx=12, pady=6, expand=True)
        self.how = tk.Label(f, bg=card, fg=COLOR["text"], font=(font, 10), wraplength=280, justify="center")
        self.how.pack(padx=10)
        self.cmd = tk.Label(f, bg=card, fg="#2563eb", font=(font, 10, "bold"), wraplength=280, justify="center")
        self.cmd.pack(pady=(2, 0))
        self.nav = tk.Frame(f, bg=card)           # Trước / Sau: chỉ hiện ở tab Bộ cử chỉ
        self.prev_btn = tk.Button(self.nav, text=UI[lang]["prev"], width=9, font=(font, 10), command=lambda: self.go(-1))
        self.prev_btn.pack(side="left", padx=6)
        self.next_btn = tk.Button(self.nav, text=UI[lang]["next"], width=9, font=(font, 10), command=lambda: self.go(1))
        self.next_btn.pack(side="left", padx=6)
        f.bind("<Configure>", self._resize)
        top = parent.winfo_toplevel()
        top.bind("<Left>", self._arrow, add="+")      # phím ← → chuyển cử chỉ khi hướng dẫn đang hiện ở tab Bộ cử chỉ
        top.bind("<Right>", self._arrow, add="+")

    def _arrow(self, event) -> None:
        if self.visible and self.tab == "gestures":
            self.go(-1 if event.keysym == "Left" else 1)

    def set_lang(self, lang: str) -> None:
        """Đổi ngôn ngữ ("vi" | "en"): cập nhật chữ trên 3 tab và nút Trước / Sau, rồi vẽ lại trang đang mở."""
        if lang == self.lang:
            return
        self.lang = lang
        for key, text in (TABS_EN if lang == "en" else TABS):
            self.tab_btns[key].config(text=text)
        self.prev_btn.config(text=UI[lang]["prev"])
        self.next_btn.config(text=UI[lang]["next"])
        if self.visible:
            self._refresh()

    def set_policy(self, key: str) -> None:
        """Báo bộ lọc đang chọn để tab "Chế độ" đánh dấu."""
        self.policy = key
        if self.visible and self.tab == "modes":
            self._refresh()

    # --- bật / tắt ---
    def show(self, grid: dict = None) -> None:
        if grid:
            self.frame.grid(**grid)
        else:
            self.frame.pack(fill="both", expand=True, padx=14, pady=4)
        self.visible = True
        self.tab, self.idx = "usage", 0           # mặc định mở ở "Cách dùng"
        self._refresh()

    def hide(self) -> None:
        self._cancel()
        self.frame.grid_forget()
        self.frame.pack_forget()
        self.visible = False

    # --- chọn trang ---
    def select(self, tab: str) -> None:
        self.tab = tab
        self._refresh()

    def go(self, step: int) -> None:
        """Cử chỉ trước / sau (vòng tròn); chỉ có nghĩa ở tab Bộ cử chỉ."""
        if self.tab != "gestures":
            return
        self.idx = (self.idx + step) % len(GESTURES)
        self._refresh()

    def _modes_text(self) -> str:
        lines = []
        for m in mode_list(self.policy, self.lang):
            mark = "▶ " if m["key"] == self.policy else "    "
            lines.append(f"{mark}{m['tag']} · {m['title']}\n      {m['desc']}")
        head = ("C1–C4 need an activation gesture (ARM) before a command. Pick one with the Filter button (key P); it can only be changed before pressing Start.\n\n"
                if self.lang == "en" else
                "C1–C4 cần làm cử chỉ kích hoạt (ARM) trước khi ra lệnh. Chọn bằng nút Bộ lọc (phím P), đổi được khi chưa bấm Bắt đầu.\n\n")
        return head + "\n\n".join(lines)

    def _refresh(self) -> None:
        self._cancel()
        for key, b in self.tab_btns.items():
            active = key == self.tab
            b.config(bg=COLOR["card"], fg=TAB_ACCENT if active else TAB_TEXT,
                     activebackground=COLOR["card"], activeforeground=TAB_ACCENT)
            self.tab_indicators[key].config(bg=TAB_ACCENT if active else COLOR["card"])
        self.frame_i = 0
        if self.tab == "gestures":
            g = gesture_text(GESTURES[self.idx], self.lang)
            self.step.config(text=UI[self.lang]["step"].format(i=self.idx + 1, n=len(GESTURES)))
            self.name.config(text=g["title"])
            self.pic.pack(padx=12, pady=6, expand=True, before=self.how)
            self.how.config(text=g["how"], justify="center")
            self.how.pack_configure(anchor="center", fill="none")
            self.cmd.config(text=command_text(GESTURES[self.idx], self.labels, self.lang))
            self.nav.pack(pady=8)
            self._draw()
            return
        self.step.config(text="")                 # tab chữ: ẩn ảnh và Trước / Sau, chữ canh trái
        self.name.config(text=UI[self.lang]["usage_name" if self.tab == "usage" else "modes_name"])
        self.pic.pack_forget()
        self.nav.pack_forget()
        self.how.config(text=(USAGE_TEXT_EN if self.lang == "en" else USAGE_TEXT) if self.tab == "usage" else self._modes_text(), justify="left")
        self.how.pack_configure(anchor="w", fill="x")
        self.cmd.config(text="")

    def _image(self, filename: str):
        key = (self.size, filename)
        if key not in self.images:
            self.images[key] = self.tk.PhotoImage(file=str(ASSETS / str(self.size) / filename))
        return self.images[key]

    def _draw(self) -> None:
        if self.tab != "gestures":
            return
        g = GESTURES[self.idx]
        self.pic.config(image=self._image(g["frames"][self.frame_i]))
        if len(g["frames"]) > 1 and self.visible:   # cử chỉ động: đổi khung mỗi 0,5 giây
            self.frame_i = (self.frame_i + 1) % len(g["frames"])
            self._job = self.frame.after(FRAME_MS, self._draw)

    def _cancel(self) -> None:
        if self._job:
            self.frame.after_cancel(self._job)
            self._job = None

    def _resize(self, _event=None) -> None:
        """Cửa sổ rộng/cao hơn mức nội dung cần ("slack") thì dùng ảnh to hơn; hẹp lại thì dùng ảnh nhỏ hơn.
        Tính theo (cỡ ảnh hiện tại + phần dư) nên không dao động qua lại."""
        slack = self.frame.winfo_height() - self.frame.winfo_reqheight()
        avail = min(self.size + slack, self.frame.winfo_width() - 30)
        new = pick_size(avail)
        wrap = max(220, self.frame.winfo_width() - 30)
        self.how.config(wraplength=wrap)
        self.cmd.config(wraplength=wrap)
        if new != self.size:
            self.size = new
            self._draw()