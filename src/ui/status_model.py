from __future__ import annotations

# Hai bộ chữ: "vi" (mặc định) và "en". Thêm ngôn ngữ mới = thêm một khóa vào 3 dict dưới và vào TEXT.
CMD = {
    "vi": {"next": "Slide tiếp", "previous": "Slide trước", "play_pause": "Phát / dừng", "start_show": "Vào trình chiếu", "exit_show": "Thoát"},
    "en": {"next": "Next slide", "previous": "Previous slide", "play_pause": "Play / pause", "start_show": "Start show", "exit_show": "Exit"},
}
LAST_CMD_SHOW_S = 1.5
OFF_COLOR = "#374151"

# state -> (tiêu đề, màu, gợi ý)
STATE_VIEWS = {
    "vi": {
        "IDLE": ("CHỜ", "#505050", "Mở bàn tay để bắt đầu"),
        "ARMED": ("SẴN SÀNG", "#14AA4B", "Làm cử chỉ lệnh"),
        "COMMAND": ("GIỮ YÊN", "#0F7F36", "Giữ cử chỉ thêm chút"),
        "UNCERTAIN": ("CHƯA CHẮC", "#FF6A00", "Giữ rõ hơn"),
        "REJECT": ("KHÔNG RÕ", "#DC2828", "Thử lại"),
        "CONFIRM": ("XÁC NHẬN", "#D2AA06", "Like = Có, Dislike = Không"),
        "EXECUTE": ("ĐÃ NHẬN", "#2864EB", ""),
        "COOLDOWN": ("NGHỈ", "#6D28D9", "Chờ giây lát"),
    },
    "en": {
        "IDLE": ("IDLE", "#505050", "Open your hand to begin"),
        "ARMED": ("READY", "#14AA4B", "Make a command gesture"),
        "COMMAND": ("HOLD", "#0F7F36", "Hold the gesture a bit longer"),
        "UNCERTAIN": ("UNSURE", "#FF6A00", "Hold it more clearly"),
        "REJECT": ("UNCLEAR", "#DC2828", "Try again"),
        "CONFIRM": ("CONFIRM", "#D2AA06", "Like = Yes, Dislike = No"),
        "EXECUTE": ("RECEIVED", "#2864EB", ""),
        "COOLDOWN": ("REST", "#6D28D9", "Wait a moment"),
    },
}
MODE_VIEWS = {
    "vi": {True: ("● TẬP", "#D2AA06"), False: ("● GỬI THẬT", "#3FA9F5")},
    "en": {True: ("● PRACTICE", "#D2AA06"), False: ("● LIVE", "#3FA9F5")},
}
TEXT = {
    "vi": {"starting": "KHỞI ĐỘNG", "opening": "Đang mở camera...", "off": "TẮT", "press_start": "Bấm Bắt đầu",
           "arming": "Giữ bàn tay mở...", "dry_sent": "Chưa gửi phím (đang tập)", "sent": "Đã gửi phím", "sent_title": "ĐÃ GỬI"},
    "en": {"starting": "STARTING", "opening": "Opening camera...", "off": "OFF", "press_start": "Press Start",
           "arming": "Keep your hand open...", "dry_sent": "Keys not sent (practice)", "sent": "Keys sent", "sent_title": "SENT"},
}

# tên cũ (bản tiếng Việt) vẫn giữ để chỗ khác import không vỡ
CMD_VI, STATE_VIEW, MODE_VIEW = CMD["vi"], STATE_VIEWS["vi"], MODE_VIEWS["vi"]


def view_model(snap: dict, now: float, lang: str = "vi") -> dict:
    """snap: LiveSession.snapshot(). Trả về dict: title, color, command, hint, progress, mode_text, mode_color.
    lang: "vi" | "en" (ngôn ngữ lạ thì dùng "vi")."""
    lang = lang if lang in TEXT else "vi"
    tx, cmds, states = TEXT[lang], CMD[lang], STATE_VIEWS[lang]
    mode_text, mode_color = MODE_VIEWS[lang][bool(snap.get("dry_run", True))]
    base = {"command": "", "progress": 0.0, "mode_text": mode_text, "mode_color": mode_color}
    if not snap.get("running"):
        if snap.get("starting"):
            return {**base, "title": tx["starting"], "color": OFF_COLOR, "hint": tx["opening"]}
        return {**base, "title": tx["off"], "color": OFF_COLOR, "hint": tx["press_start"]}

    hud = snap.get("hud") or {}
    state = hud.get("state", "IDLE")
    title, color, hint = states.get(state, states["IDLE"])
    progress = float(hud.get("progress") or 0.0)
    if state == "IDLE" and hud.get("reason") == "arming":
        hint = tx["arming"]
    if state == "EXECUTE":
        hint = tx["dry_sent"] if snap.get("dry_run", True) else tx["sent"]
        if not snap.get("dry_run", True):
            title = tx["sent_title"]

    command = ""
    if state in ("COMMAND", "CONFIRM", "EXECUTE") and hud.get("command"):
        command = cmds.get(hud["command"], hud["command"])
    elif snap.get("last_command") and (snap.get("last_command_age") or 99) <= LAST_CMD_SHOW_S:
        command = cmds.get(snap["last_command"], snap["last_command"])
    if state == "CONFIRM" and command:
        command += "?"
    return {**base, "title": title, "color": color, "command": command, "hint": hint, "progress": max(0.0, min(1.0, progress))}