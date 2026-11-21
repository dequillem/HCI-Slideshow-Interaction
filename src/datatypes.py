"""Hợp đồng dữ liệu giữa các khối: Observation -> FeatureWindow -> Hypothesis -> Decision."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

IDLE, ARMED, COMMAND, CONFIRM, EXECUTE, COOLDOWN = "IDLE", "ARMED", "COMMAND", "CONFIRM", "EXECUTE", "COOLDOWN"
ACCEPT, REJECT, UNCERTAIN = "ACCEPT", "REJECT", "UNCERTAIN"
ARM_LABEL, NONE_LABEL = "arm", "none"
COMMANDS = ("next", "previous", "play_pause", "start_show", "exit_show")
CONFIRM_YES, CONFIRM_NO = "like", "dislike"  # cử chỉ xác nhận / hủy trong trạng thái CONFIRM (nếu có lệnh cần xác nhận)
POSE_COMMANDS = {"like": "start_show", "dislike": "exit_show"}  # tư thế -> lệnh: thumb up = vào trình chiếu, thumb down = thoát


@dataclass(frozen=True)
class Observation:
    t_ms: int
    landmarks: Optional[list] = None        # 21 x [x, y, z] chuẩn hóa; None = không thấy tay
    handedness: Optional[str] = None
    score: float = 0.0
    world_landmarks: Optional[list] = None
    truth: Optional[str] = None             # nhãn thật ("cmd:next"...), chỉ có ở phiên gán nhãn

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Observation":
        return Observation(d["t_ms"], d.get("landmarks"), d.get("handedness"), d.get("score", 0.0),
                           d.get("world_landmarks"), d.get("truth"))


@dataclass(frozen=True)
class FeatureWindow:
    t_ms: int
    hand: bool
    vector: tuple = ()                      # 63 số đã chuẩn hóa, trung bình trong cửa sổ (đưa vào Random Forest)
    ext: tuple = (0.0, 0.0, 0.0, 0.0)       # mức duỗi trỏ/giữa/nhẫn/út (cho RuleRecognizer)
    speed: float = 0.0                      # tốc độ cổ tay / kích thước bàn tay (1/giây)
    n: int = 0
    thumb: tuple = (0.0, 0.0)               # (điểm like, điểm dislike) 0..1: đầu ngón cái cao hơn / thấp hơn mọi ngón còn lại
    landmarks: Optional[list] = None        # 21 x [x, y, z] thô của khung hiện tại (GRU cần tọa độ gốc, không làm mượt)


@dataclass(frozen=True)
class Hypothesis:
    t_ms: int
    has_hand: bool
    label: str
    probs: dict = field(default_factory=dict)
    margin: float = 0.0
    command: Optional[str] = None           # None = "không phải lệnh"
    swipe_probs: dict = field(default_factory=dict)  # xác suất GRU next/previous ở mọi khung (kể cả khi luật thắng) để gate dò mâu thuẫn hướng


@dataclass(frozen=True)
class Decision:
    t_ms: int
    verdict: str                            # ACCEPT | REJECT | UNCERTAIN
    command: Optional[str]
    reason: str
    state: str
    progress: float = 0.0
    label: str = ""
    conf: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Decision":
        return Decision(**d)
