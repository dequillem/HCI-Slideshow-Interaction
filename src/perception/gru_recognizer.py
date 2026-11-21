"""Khối: nhận diện cử chỉ ĐỘNG bằng GRU (train ở repo nghiên cứu HCI-project, dữ liệu Jester).

GRURecognizer: FeatureWindow -> Hypothesis cho next / previous (vuốt phải / trái).
HybridRecognizer: GRU cho cử chỉ động + RuleRecognizer cho tư thế tĩnh (arm, play_pause, exit_show, like, dislike).

Tiền xử lý PHẢI GIỐNG HỆT lúc train (HCI-project/src/sequence_utils.py):
  * mỗi bước = 63 tọa độ ảnh thô (x, y, z) của tay đầu tiên + 7 motion
    (dx/dy/dz cổ tay, dx/dy/dz đầu ngón trỏ, tốc độ xy cổ tay) so với bước trước;
  * không thấy tay -> 63 số 0; motion = 0 nếu bước này hoặc bước trước không có tay;
  * cửa sổ `sequence_length` bước, đệm 0 bên trái khi chưa đủ;
  * lấy mẫu theo THỜI GIAN mỗi `step_ms` (đọc từ meta.json), không theo số khung camera.
Có test đối chiếu với output của repo nghiên cứu: tests/test_gru_recognizer.py.
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import replace
from pathlib import Path

import numpy as np

from ..config import Config
from ..datatypes import ARM_LABEL, CONFIRM_NO, CONFIRM_YES, NONE_LABEL, FeatureWindow, Hypothesis

LANDMARK_FEATURES = 63
SEQUENCE_FEATURES = 70
GRU_COMMANDS = ("next", "previous")      # cử chỉ GRU được phép ra lệnh; zoom_in/zoom_out tạm bỏ -> gộp vào none
STATIC_KEEP = (ARM_LABEL, CONFIRM_YES, CONFIRM_NO)  # tư thế vẫn nhận khi tay đang chuyển động nhanh


def landmarks_to_frame(landmarks, flip_x: bool) -> np.ndarray:
    """21 x [x, y, z] (hoặc None) -> 63 số. flip_x: bỏ lật gương của CameraSource cho khớp ảnh Jester."""
    if landmarks is None:
        return np.zeros(LANDMARK_FEATURES, dtype=np.float32)
    frame = np.asarray(landmarks, dtype=np.float32).reshape(LANDMARK_FEATURES).copy()
    if flip_x:
        frame[0::3] = 1.0 - frame[0::3]
    return frame


def add_motion(frame: np.ndarray, previous: np.ndarray | None) -> np.ndarray:
    """Bản sao của sequence_utils.add_motion_features (HCI-project)."""
    out = np.zeros(SEQUENCE_FEATURES, dtype=np.float32)
    out[:LANDMARK_FEATURES] = frame
    if previous is None or not frame.any() or not previous.any():
        return out
    wrist = frame[0:3] - previous[0:3]
    index = frame[24:27] - previous[24:27]
    out[63:66] = wrist
    out[66:69] = index
    out[69] = float(np.linalg.norm(wrist[:2]))
    return out


class SequenceBuffer:
    """Gom khung camera thành chuỗi bước đều nhau theo thời gian."""

    def __init__(self, length: int, step_ms: float, flip_x: bool):
        self.length, self.step_ms, self.flip_x = length, step_ms, flip_x
        self.steps: deque = deque(maxlen=length)
        self.prev: np.ndarray | None = None
        self.next_t: float | None = None

    def push(self, t_ms: int, landmarks) -> bool:
        """True khi vừa thêm một bước mới (nên chạy model)."""
        if self.next_t is not None and t_ms < self.next_t - 1e-6:  # dung sai: 3 x 166.67 = 500.0000001
            return False
        if self.next_t is None or t_ms - self.next_t > self.step_ms:
            self.next_t = float(t_ms)  # khởi động hoặc bị trễ khung dài: bắt nhịp lại, không dồn bước
        self.next_t += self.step_ms
        frame = landmarks_to_frame(landmarks, self.flip_x)
        self.steps.append(add_motion(frame, self.prev))
        self.prev = frame
        return True

    def window(self) -> np.ndarray:
        steps = list(self.steps)
        pad = [np.zeros(SEQUENCE_FEATURES, dtype=np.float32)] * (self.length - len(steps))
        return np.stack(pad + steps)[None].astype(np.float32)


def _ranked(t_ms: int, has_hand: bool, probs: dict, command_set) -> Hypothesis:
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    label = ranked[0][0]
    margin = ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0)
    return Hypothesis(t_ms, has_hand, label, probs, margin, label if label in command_set else None)


class GRURecognizer:
    def __init__(self, model_dir: str, flip_x: bool = True, model=None, step_ms: float = 0):
        """model_dir chứa gru.keras, gru.labels.json, gru.meta.json (copy từ HCI-project/models/).
        model: truyền model giả khi kiểm thử (callable: mảng (1, T, 70) -> xác suất (1, C)).
        step_ms > 0: lấy mẫu nhanh hơn/chậm hơn lúc train (meta.json). Người dùng vuốt nhanh hơn diễn viên Jester
        nhiều lần, nên lấy mẫu dày hơn = "quay chậm" cú vuốt về đúng tốc độ model đã học."""
        d = Path(model_dir)
        self.classes = json.loads((d / "gru.labels.json").read_text(encoding="utf-8"))
        meta = json.loads((d / "gru.meta.json").read_text(encoding="utf-8"))
        self.length = int(meta["sequence_length"])
        self.step_ms = float(step_ms) if step_ms and step_ms > 0 else float(meta.get("step_ms", 125.0))
        if model is None:
            import tensorflow as tf  # nhập muộn: chỉ cần khi dùng recognizer gru/hybrid
            keras_model = tf.keras.models.load_model(d / "gru.keras")
            # Chạy dạng graph với shape cố định: gọi eager một GRU mất ~180 ms/lần trên CPU, graph chỉ vài ms.
            graph = tf.function(lambda x: keras_model(x, training=False), reduce_retracing=True,
                                input_signature=[tf.TensorSpec((1, self.length, SEQUENCE_FEATURES), tf.float32)])
            model = lambda x: graph(tf.constant(x, dtype=tf.float32)).numpy()
            model(np.zeros((1, self.length, SEQUENCE_FEATURES), dtype=np.float32))  # làm nóng: dựng graph lúc khởi động
        self.model = model
        self.buffer = SequenceBuffer(self.length, self.step_ms, flip_x)
        self.last = {NONE_LABEL: 1.0}

    def probabilities(self) -> dict:
        raw = np.asarray(self.model(self.buffer.window()))[0]
        probs = {c: 0.0 for c in (*GRU_COMMANDS, NONE_LABEL)}
        for name, p in zip(self.classes, raw):
            probs[name if name in GRU_COMMANDS else NONE_LABEL] += float(p)  # zoom tạm bỏ -> none
        return probs

    def __call__(self, fw: FeatureWindow) -> Hypothesis:
        if self.buffer.push(fw.t_ms, fw.landmarks if fw.hand else None):
            self.last = self.probabilities()
        return _ranked(fw.t_ms, fw.hand, dict(self.last), GRU_COMMANDS)

    def reset(self) -> None:
        """Quên chuỗi đã thấy (Pipeline gọi sau mỗi lệnh được thực hiện); giữ nhịp lấy mẫu."""
        self.buffer.steps.clear()
        self.buffer.prev = None
        self.last = {NONE_LABEL: 1.0}


class HybridRecognizer:
    """GRU thắng khi nó đủ chắc về một cú vuốt; còn lại dùng luật tư thế tĩnh.

    * next/previous dạng tư thế tĩnh bị bỏ khỏi luật (chỉ còn vuốt) để hai bộ không tranh nhau.
    * Tay đang di chuyển nhanh (speed > static_max_speed) thì không coi là tư thế lệnh tĩnh
      (vuốt bằng bàn tay mở dễ bị đọc nhầm thành play_pause); arm/like/dislike vẫn giữ.
    """

    def __init__(self, cfg: Config, rule=None, gru=None):
        from .recognizer import RuleRecognizer
        self.cfg = cfg
        self.rule = rule or RuleRecognizer(exclude=GRU_COMMANDS)
        self.gru = gru or GRURecognizer(cfg.gru_model_dir, flip_x=cfg.gru_flip_x, step_ms=cfg.gru_step_ms)

    def __call__(self, fw: FeatureWindow) -> Hypothesis:
        g = self.gru(fw)  # luôn gọi để GRU nhận đủ chuỗi, kể cả khung không có tay
        if not fw.hand:
            return Hypothesis(fw.t_ms, False, NONE_LABEL)
        swipe = {c: g.probs.get(c, 0.0) for c in GRU_COMMANDS}  # gate cần cả xác suất dưới ngưỡng để dò mâu thuẫn hướng
        if g.label in GRU_COMMANDS and g.probs[g.label] >= self.cfg.gru_override:
            return replace(g, swipe_probs=swipe)
        r = self.rule(fw)
        if fw.speed > self.cfg.static_max_speed and r.label not in STATIC_KEEP:
            return Hypothesis(fw.t_ms, True, NONE_LABEL, {NONE_LABEL: 1.0}, 1.0, None, swipe)
        return replace(r, swipe_probs=swipe)

    def reset(self) -> None:
        self.gru.reset()
