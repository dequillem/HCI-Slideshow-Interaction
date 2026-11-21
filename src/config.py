"""Config: dataclass + nạp từ config.yaml."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace, fields

POLICIES = ("naive", "fixed", "adaptive", "abstain", "combined", "swipe", "adaptive_speed")


@dataclass(frozen=True)
class Config:
    policy: str = "fixed"
    recognizer: str = "hybrid"      # hybrid (GRU vuốt + luật tư thế) | gru | rule (chỉ tư thế tĩnh)
    gru_model_dir: str = "models/gru"   # gru.keras + gru.labels.json + gru.meta.json (từ HCI-project)
    gru_flip_x: bool = True         # CameraSource lật gương, ảnh Jester thì không -> lật lại x cho GRU
    gru_step_ms: float = 0          # > 0: nhịp lấy mẫu GRU (ms), ghi đè step_ms của meta.json; 0 = dùng meta (tốc độ lúc train)
    gru_override: float = 0.5       # hybrid: GRU chắc >= mức này về next/previous thì dùng GRU thay luật
    static_max_speed: float = 1.5   # hybrid: tay nhanh hơn mức này (kích thước tay/giây) thì không nhận tư thế lệnh tĩnh
    camera_index: int = 0
    preview_width: int = 480        # độ rộng cửa sổ camera (px)
    preview_topmost: bool = True    # cửa sổ camera luôn nổi trên cùng (để thấy HUD khi PowerPoint toàn màn hình)
    status_every_s: float = 5.0   
    dry_run: bool = True
    log_dir: str = "sessions"
    window_ms: int = 150
    require_arm: bool = True        # fixed/adaptive/abstain/combined có cần nắm tay ARM trước không (naive, swipe: không bao giờ)
    arm_hold_ms: int = 300
    armed_timeout_ms: int = 4000
    conf: float = 0.80
    play_pause: int = 700  
    hold_ms: int = 400
    swipe_hold_ms: int = 200        # policy swipe: thời gian giữ (ngắn hơn vì cú vuốt chỉ kéo dài ít khung)
    disabled_commands: list = field(default_factory=list)  # lệnh bị tắt hẳn (gate coi như không phải lệnh)
    reverse_block_ms: int = 0       # sau một cú vuốt, bỏ qua vuốt chiều ngược trong ngần này ms (nhịp đưa tay về)
    command_hold_ms: dict = field(default_factory=dict)
    cooldown_ms: int = 1200
    confirm_commands: list = field(default_factory=list)  # lệnh cần bước xác nhận (like) trước khi thực hiện; hiện không dùng
    confirm_hold_ms: int = 400
    confirm_timeout_ms: int = 4000
    margin: float = 0.25
    uncertain_floor: float = 0.40
    # adaptive / combined: ngưỡng theo độ mơ hồ (cùng tham số mặc định với HCI-project/src/policies.py)
    adapt_min_conf: float = 0.70
    adapt_max_conf: float = 0.95
    margin_weight: float = 0.20
    stability_weight: float = 0.15
    stability_window_ms: int = 800  # độ ổn định tính trên chuỗi khung hợp lệ trong ngần này ms (~5 bước GRU, khớp hold_frames=5)
    # abstain / combined: chưa chắc -> quan sát thêm tối đa abstain_wait_ms, vẫn không rõ -> từ chối
    abstain_wait_ms: int = 600
    clear_conf: float = 0.90        # dưới mức này (dù đã qua ngưỡng) coi là "chưa rõ", phải quan sát thêm
    conflict_floor: float = 0.50    # vuốt chiều ngược có xác suất >= mức này trong cửa sổ gần đây = mâu thuẫn hướng
    conflict_window_ms: int = 700
    speed_floor: float = 0.6
    speed_gain: float = 0.08
    max_boost: float = 0.15
    hold_gain: float = 0.25
    keymap: dict = field(default_factory=lambda: {"next": "right", "previous": "left", "play_pause": "alt+p"})

    def __post_init__(self):
        if self.policy not in POLICIES:
            raise ValueError(f"policy phải thuộc {POLICIES}")

    def to_dict(self) -> dict:
        return asdict(self)

    def with_policy(self, name: str) -> "Config":
        return replace(self, policy=name)

    @staticmethod
    def from_dict(d: dict) -> "Config":
        known = {f.name for f in fields(Config)}
        return Config(**{k: v for k, v in d.items() if k in known})


def load_config(path: str = "config.yaml") -> Config:
    import yaml  # nhập muộn để test không cần pyyaml
    with open(path, encoding="utf-8") as f:
        return Config.from_dict(yaml.safe_load(f) or {})

