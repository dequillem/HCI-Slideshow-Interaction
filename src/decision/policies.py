"""Policy cắm rời: hàm thuần (cfg, ctx) -> Gating. Intent Gate gọi hàm này mỗi khung.

Bốn cấu hình của báo cáo (RQ1, RQ2) + hai mốc phụ:
  fixed     C1: ngưỡng cố định `conf`
  adaptive  C2: ngưỡng thích ứng theo ĐỘ MƠ HỒ (margin top-1/top-2 + độ ổn định nhãn) — cùng công thức với
                HCI-project/src/policies.py (DecisionPolicy._threshold) để kết quả offline và demo so được với nhau
  abstain   C3: ngưỡng cố định + abstention (chưa chắc thì chờ thêm, hết hạn vẫn không rõ thì từ chối; logic ở gate.py)
  combined  C4: adaptive + abstention
  naive:    không Intent Gate (mốc "không chống Midas touch")
  swipe:    cấu hình DEMO (không ARM, gate lỏng do người dùng chỉnh tay) — không dùng để so sánh
  adaptive_speed: bản adaptive cũ, khắt khe hơn khi tay chuyển động nhanh (giữ để tham khảo)
Bốn cấu hình C1–C4 dùng chung hold_ms, cooldown_ms, reverse_block_ms và `require_arm` để so sánh công bằng.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import Config


@dataclass(frozen=True)
class Context:
    t_ms: int
    speed: float
    margin: float = 1.0         # chênh lệch xác suất top-1 / top-2 của khung hiện tại
    stability: float = 1.0      # tỉ lệ khung trong chuỗi hợp lệ gần đây có cùng nhãn với khung hiện tại
    has_history: bool = False   # chuỗi hợp lệ gần đây có rỗng không (khung đầu tiên không bị phạt "không ổn định")


@dataclass(frozen=True)
class Gating:
    min_conf: float
    min_margin: float
    hold_ms: int
    require_arm: bool
    abstain: bool


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def ambiguity_conf(cfg: Config, ctx: Context) -> float:
    """Ngưỡng thích ứng theo độ mơ hồ. Bản sao của HCI-project DecisionPolicy._threshold:
    ngưỡng = conf + margin_weight * (1 - margin) + stability_weight * (1 - stability), kẹp trong [adapt_min_conf, adapt_max_conf]."""
    ambiguity = _clamp01(1.0 - ctx.margin)
    instability = _clamp01(1.0 - ctx.stability) if ctx.has_history else 0.0
    value = cfg.conf + cfg.margin_weight * ambiguity + cfg.stability_weight * instability
    return max(cfg.adapt_min_conf, min(cfg.adapt_max_conf, value))


def _speed_adapt(cfg: Config, ctx: Context):
    excess = max(0.0, ctx.speed - cfg.speed_floor)
    conf = min(0.97, cfg.conf + min(cfg.max_boost, cfg.speed_gain * excess))
    return conf, int(cfg.hold_ms * (1.0 + cfg.hold_gain * excess))


def naive(cfg, ctx):
    return Gating(0.5, 0.0, 0, False, False)


def fixed(cfg, ctx):  # C1. Từ teammate: GestureGate.threshold, hold_frames (đổi sang ms)
    return Gating(cfg.conf, 0.0, cfg.hold_ms, cfg.require_arm, False)


def adaptive(cfg, ctx):  # C2
    return Gating(ambiguity_conf(cfg, ctx), 0.0, cfg.hold_ms, cfg.require_arm, False)


def abstain(cfg, ctx):  # C3
    return Gating(cfg.conf, cfg.margin, cfg.hold_ms, cfg.require_arm, True)


def combined(cfg, ctx):  # C4
    return Gating(ambiguity_conf(cfg, ctx), cfg.margin, cfg.hold_ms, cfg.require_arm, True)


def adaptive_speed(cfg, ctx):
    conf, hold = _speed_adapt(cfg, ctx)
    return Gating(conf, 0.0, hold, cfg.require_arm, False)


def swipe(cfg, ctx):  # demo: không cần ARM; ngưỡng + thời gian giữ ngắn + cooldown
    return Gating(cfg.conf, 0.0, cfg.swipe_hold_ms, False, False)


REGISTRY = {"naive": naive, "fixed": fixed, "adaptive": adaptive, "abstain": abstain, "combined": combined,
            "swipe": swipe, "adaptive_speed": adaptive_speed}


def get_policy(name: str):
    return REGISTRY[name]
