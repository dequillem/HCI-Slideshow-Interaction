from __future__ import annotations

from .theme import C

CMD_VI = {"next": "Slide tiếp", "previous": "Slide trước", "play_pause": "Phát / dừng", "start_show": "Vào trình chiếu", "exit_show": "Thoát trình chiếu"}
LAST_CMD_SHOW_S = 1.5
# trạng thái Intent Gate -> (nhãn, màu nền của nhãn, gợi ý). Màu đều đạt >= 4.5:1 với chữ trắng.
STATE_VIEW = {
    "IDLE": ("CHỜ", C["neutral"], "Giơ tay vào khung hình"),
    "ARMED": ("SẴN SÀNG", C["success"], "Làm cử chỉ lệnh"),
    "COMMAND": ("GIỮ YÊN", C["teal"], "Giữ cử chỉ thêm chút"),
    "UNCERTAIN": ("CHƯA CHẮC", C["warning"], "Làm cử chỉ rõ hơn"),
    "REJECT": ("KHÔNG RÕ", C["danger"], "Thử lại"),
    "CONFIRM": ("XÁC NHẬN", C["warning"], "Like = Có, Dislike = Không"),
    "EXECUTE": ("ĐÃ NHẬN", C["accent"], ""),
    "COOLDOWN": ("NGHỈ", C["violet"], "Chờ giây lát"),
}
OFF_COLOR = "#334155"
# chế độ -> (chữ, màu chấm trên nền tối của cửa sổ trạng thái)
MODE_VIEW = {True: ("TẬP", "#FBBF24"), False: ("GỬI THẬT", "#F87171")}


def view_model(snap: dict, now: float) -> dict:
    """snap: LiveSession.snapshot(). Trả về dict: title, color, command, hint, progress, mode_text, mode_color."""
    mode_text, mode_color = MODE_VIEW[bool(snap.get("dry_run", True))]
    base = {"command": "", "progress": 0.0, "mode_text": mode_text, "mode_color": mode_color}
    if not snap.get("running"):
        if snap.get("starting"):
            return {**base, "title": "KHỞI ĐỘNG", "color": OFF_COLOR, "hint": "Đang mở camera..."}
        return {**base, "title": "TẮT", "color": OFF_COLOR, "hint": "Bấm Bắt đầu để mở camera"}

    hud = snap.get("hud") or {}
    state = hud.get("state", "IDLE")
    title, color, hint = STATE_VIEW.get(state, STATE_VIEW["IDLE"])
    progress = float(hud.get("progress") or 0.0)
    if state == "IDLE" and hud.get("reason") == "arming":
        hint = "Giữ tay trong khung hình..."
    if state == "EXECUTE":
        hint = "Chưa gửi phím (đang tập)" if snap.get("dry_run", True) else "Đã gửi phím"
        if not snap.get("dry_run", True):
            title = "ĐÃ GỬI"

    command = ""
    if state in ("COMMAND", "CONFIRM", "EXECUTE") and hud.get("command"):
        command = CMD_VI.get(hud["command"], hud["command"])
    elif snap.get("last_command") and (snap.get("last_command_age") or 99) <= LAST_CMD_SHOW_S:
        command = CMD_VI.get(snap["last_command"], snap["last_command"])
    if state == "CONFIRM" and command:
        command += "?"
    return {**base, "title": title, "color": color, "command": command, "hint": hint, "progress": max(0.0, min(1.0, progress))}
