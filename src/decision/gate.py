"""Khối: Intent Gate (xử lý Midas Touch).

IDLE --(cử chỉ ARM đủ lâu)--> ARMED --(cử chỉ lệnh rõ, giữ đủ lâu)--> COMMAND --> EXECUTE --> COOLDOWN --> IDLE
(require_arm = false hoặc policy naive/swipe: IDLE tự chuyển sang ARMED.)
Mỗi khung trả về một Decision: ACCEPT (chỉ khi EXECUTE) | REJECT | UNCERTAIN (chỉ policy có abstain).

Bằng chứng gate tự giữ:
  * run: chuỗi khung hợp lệ liên tiếp gần đây (nhãn lệnh, đủ ngưỡng) -> độ ổn định cho ngưỡng thích ứng (adaptive/combined).
    Giống `history` của HCI-project DecisionPolicy: khung không hợp lệ thì xóa, khung đầu tiên không bị phạt.
  * evidence: xác suất GRU next/previous trong `conflict_window_ms` gần đây -> dò mâu thuẫn hướng (abstain/combined).

Abstention (abstain/combined): khi cử chỉ đã giữ đủ lâu mà còn "nghi ngờ" thì KHÔNG thực thi ngay:
  nghi ngờ = low_conf (dưới ngưỡng nhưng trên uncertain_floor) | low_margin | unclear (dưới clear_conf)
             | conflict (vuốt chiều ngược >= conflict_floor trong cửa sổ gần đây, vd. đoạn lấy đà trước cú vuốt).
  -> trả UNCERTAIN và quan sát thêm tối đa abstain_wait_ms (tính từ lúc bắt đầu nghi ngờ của ứng viên này):
     hết nghi ngờ -> chấp nhận; hết hạn mà đủ ngưỡng và chiều ngược không còn -> chấp nhận;
     hết hạn mà vẫn dưới ngưỡng / chiều ngược vẫn còn -> từ chối, và bỏ qua cử chỉ đó tới khi người dùng đổi tay.
  Ứng viên đổi (vd. next <-> previous xen kẽ) thì đồng hồ chờ bắt đầu lại, nên chuỗi mâu thuẫn liên tục không bao giờ được thực thi.
"""
from __future__ import annotations

from collections import deque
from dataclasses import replace

from ..config import Config
from ..datatypes import (ACCEPT, ARM_LABEL, ARMED, COMMAND, CONFIRM, CONFIRM_NO, CONFIRM_YES, COOLDOWN, EXECUTE, IDLE, REJECT, UNCERTAIN,
                     Decision, FeatureWindow, Hypothesis)
from .policies import Context, get_policy

OPPOSITE = {"next": "previous", "previous": "next"}


class IntentGate:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.policy = get_policy(cfg.policy)
        self.swipe_cfg = replace(cfg, conf=cfg.swipe_conf) if cfg.swipe_conf > 0 else cfg  # ngưỡng riêng cho vuốt
        self.state = IDLE
        self.arm_start = None
        self.armed_refresh = 0
        self.pending = None
        self.need_release = False
        self.cand = None            # từ teammate: GestureGate.history (nhưng theo thời gian, không đếm khung)
        self.cand_start = 0
        self.cand_last = 0          # khung hợp lệ gần nhất của ứng viên (grace_ms)
        self.confirm_start = 0
        self.cooldown_until = 0     # từ teammate: GestureGate.cooldown (nhưng theo ms)
        self.last_swipe = (None, -10**9)  # (lệnh vuốt gần nhất, thời điểm) để chặn nhịp đưa tay về
        self.released = None        # lệnh vừa thực hiện / vừa bị abstention từ chối: phải đổi cử chỉ rồi mới nhận lại
        self.doubt_start = None     # abstention: lúc ứng viên hiện tại bắt đầu bị nghi ngờ
        self.run = deque()          # (t, nhãn) các khung hợp lệ liên tiếp -> độ ổn định
        self.evidence = deque()     # (t, p_next, p_previous) -> mâu thuẫn hướng

    # ---------- bằng chứng ----------
    def _stability(self, t, label):
        while self.run and t - self.run[0][0] > self.cfg.stability_window_ms:
            self.run.popleft()
        if not self.run:
            return 1.0, False
        return sum(1 for _, lab in self.run if lab == label) / len(self.run), True

    def _push_evidence(self, t, hyp):
        sp = hyp.swipe_probs or hyp.probs
        self.evidence.append((t, sp.get("next", 0.0), sp.get("previous", 0.0)))
        while self.evidence and t - self.evidence[0][0] > self.cfg.conflict_window_ms:
            self.evidence.popleft()

    def _opposite_max(self, cmd):
        idx = 1 if OPPOSITE[cmd] == "next" else 2
        return max((e[idx] for e in self.evidence), default=0.0)

    def _doubts(self, cmd, conf, hyp, g):
        d = []
        if conf < g.min_conf:
            d.append("low_conf")
        elif conf < self.cfg.clear_conf:
            d.append("unclear")
        if hyp.margin < g.min_margin:
            d.append("low_margin")
        if cmd in OPPOSITE and self._opposite_max(cmd) >= self.cfg.conflict_floor:
            d.append("conflict")
        return d

    def _resolved(self, cmd, conf, hyp, g):
        """Hết thời gian quan sát: đủ ngưỡng, đủ margin và chiều ngược không còn ở khung hiện tại thì chấp nhận."""
        if conf < g.min_conf or hyp.margin < g.min_margin:
            return False
        if cmd in OPPOSITE:
            sp = hyp.swipe_probs or hyp.probs
            return sp.get(OPPOSITE[cmd], 0.0) < self.cfg.conflict_floor
        return True

    def _reset_candidate(self):
        self.cand, self.doubt_start = None, None
        self._clear_run()

    def _clear_run(self):
        if self.cfg.stability_reset:
            self.run.clear()

    def _in_grace(self, t):
        return self.cand is not None and self.state == COMMAND and t - self.cand_last <= self.cfg.grace_ms

    # ---------- xác nhận (giữ lại cho confirm_commands) ----------
    def _confirm(self, t, hyp, g, out):
        """Trạng thái CONFIRM: like (giữ confirm_hold_ms) = thực hiện lệnh đang chờ; dislike = hủy về IDLE; quá hạn = về IDLE."""
        if t - self.confirm_start > self.cfg.confirm_timeout_ms:
            self.state, self.pending, self.cand = IDLE, None, None
            return None                                   # rơi xuống xử lý như IDLE
        if not hyp.has_hand:
            self.cand = None
            return out(REJECT, "no_hand", self.pending)
        sure = hyp.probs.get(hyp.label, 0.0) >= g.min_conf
        if hyp.label == CONFIRM_NO and sure:
            cmd = self.pending
            self.state, self.pending, self.cand = IDLE, None, None
            return out(REJECT, "cancelled", cmd)
        if hyp.label == CONFIRM_YES and sure:
            if self.cand != CONFIRM_YES:
                self.cand, self.cand_start = CONFIRM_YES, t
            prog = min(1.0, (t - self.cand_start) / max(1, self.cfg.confirm_hold_ms))
            if prog >= 1.0:
                cmd, self.state = self.pending, EXECUTE
                decision = out(ACCEPT, "accepted", cmd, 1.0)
                self.state, self.pending, self.cand = COOLDOWN, None, None
                self.cooldown_until = t + self.cfg.cooldown_ms
                return decision
            return out(REJECT, "confirming", self.pending, prog)
        self.cand = None
        return out(REJECT, "confirm", self.pending)

    def _execute(self, t, cmd, out):
        self.state = EXECUTE
        decision = out(ACCEPT, "accepted", cmd, 1.0)
        if cmd in OPPOSITE:
            self.last_swipe = (cmd, t)
        else:
            self.released = cmd
        self.state, self.cooldown_until = COOLDOWN, t + self.cfg.cooldown_ms
        self._reset_candidate()
        self.evidence.clear()
        return decision

    def __call__(self, fw: FeatureWindow, hyp: Hypothesis) -> Decision:
        t = fw.t_ms
        conf = hyp.probs.get(hyp.label, 0.0)
        stability, has_history = self._stability(t, hyp.label)
        g = self.policy(self.swipe_cfg if hyp.command in OPPOSITE else self.cfg, Context(t, fw.speed, hyp.margin, stability, has_history))

        def out(verdict, reason, cmd=None, progress=0.0):
            return Decision(t, verdict, cmd, reason, self.state, progress, hyp.label, round(conf, 4))

        if self.state == COOLDOWN:
            if t < self.cooldown_until:
                return out(REJECT, "cooldown")
            self.state, self.arm_start = IDLE, None
            self._reset_candidate()
        if hyp.has_hand:
            self._push_evidence(t, hyp)
        if self.state == CONFIRM:
            early = self._confirm(t, hyp, g, out)
            if early is not None:
                return early
        # if not g.require_arm and self.state == IDLE:
        #     self.state, self.armed_refresh = ARMED, t
        if not g.require_arm:
            if self.cfg.presence_arm_ms < 0:                       # hành vi cũ
                if self.state == IDLE:
                    self.state, self.armed_refresh = ARMED, t
            elif not hyp.has_hand:                                 # mất tay: về IDLE
                if self.state in (ARMED, COMMAND):
                    self.state = IDLE
                self.arm_start = None
            elif self.state == IDLE:                               # tay hiện đủ lâu: lên ARMED
                if self.arm_start is None:
                    self.arm_start = t
                if t - self.arm_start >= self.cfg.presence_arm_ms:
                    self.state, self.armed_refresh, self.arm_start = ARMED, t, None
        if self.state in (ARMED, COMMAND) and g.require_arm and t - self.armed_refresh > self.cfg.armed_timeout_ms:
            self.state, self.need_release = IDLE, True
            self._reset_candidate()

        if not hyp.has_hand:
            self.arm_start, self.need_release = None, False
            self._reset_candidate()
            if self.state == COMMAND:
                self.state = ARMED
            return out(REJECT, "no_hand")

        if self.state == IDLE:
            if not g.require_arm:
                prog = 0.0 if self.arm_start is None else min(1.0, (t - self.arm_start) / max(1, self.cfg.presence_arm_ms))
                return out(REJECT, "arming" if prog > 0 else "idle", progress=prog)
            if self.need_release:
                if hyp.label != ARM_LABEL:
                    self.need_release = False
                return out(REJECT, "idle")
            if hyp.label == ARM_LABEL and conf >= g.min_conf:
                if self.arm_start is None:
                    self.arm_start = t
                prog = min(1.0, (t - self.arm_start) / max(1, self.cfg.arm_hold_ms))
                if prog >= 1.0:
                    self.state, self.armed_refresh, self.arm_start = ARMED, t, None
                    return out(REJECT, "armed")
                return out(REJECT, "arming", progress=prog)
            self.arm_start = None
            return out(REJECT, "idle")

        if hyp.label == ARM_LABEL:
            self._reset_candidate()
            self.state = ARMED
            return out(REJECT, "armed")
        cmd = hyp.command
        raw_cmd = cmd
        if cmd in self.cfg.disabled_commands:
            cmd = None
        if cmd != self.released:
            self.released = None
        elif cmd is not None:
            cmd = None  # vẫn đang giữ nguyên cử chỉ của lệnh vừa thực hiện / vừa bị từ chối
        if cmd in OPPOSITE and self.last_swipe[0] == OPPOSITE[cmd] and t - self.last_swipe[1] < self.cfg.reverse_block_ms:
            cmd = None  # vuốt phải xong tay đưa về bên trái -> GRU đọc thành previous; bỏ qua chiều ngược trong một lúc
        if cmd is None or conf < self.cfg.uncertain_floor:
            if (raw_cmd is None or cmd is not None) and self._in_grace(t):
                return out(REJECT, "grace", self.cand)
            self._reset_candidate()
            self.state = ARMED
            return out(REJECT, "no_command")
        weak = conf < g.min_conf or hyp.margin < g.min_margin
        if weak and not g.abstain:
            if self._in_grace(t):
                return out(REJECT, "grace", self.cand)
            self._reset_candidate()
            self.state = ARMED
            return out(REJECT, "low_conf" if conf < g.min_conf else "low_margin", cmd)
        if weak:
            self._clear_run()            # khung dưới ngưỡng không hợp lệ (giống HCI-project: xóa history)
        else:
            self.run.append((t, hyp.label))
        if self.cand != cmd:
            self.cand, self.cand_start, self.doubt_start = cmd, t, None
        self.state, self.cand_last = COMMAND, t
        hold = g.hold_ms
        if self.cfg.policy != "naive":   # naive giữ nguyên là mốc "không gate"
            hold = max(hold, self.cfg.command_hold_ms.get(cmd, 0))
        prog = 1.0 if hold <= 0 else min(1.0, (t - self.cand_start) / hold)

        if g.abstain:
            doubts = self._doubts(cmd, conf, hyp, g)
            if doubts:
                if self.doubt_start is None:
                    self.doubt_start = t
                if prog < 1.0 or t - self.doubt_start < self.cfg.abstain_wait_ms:
                    return out(UNCERTAIN, "uncertain:" + "+".join(doubts), cmd, prog)
                if not self._resolved(cmd, conf, hyp, g):
                    self._reset_candidate()
                    self.state, self.released = ARMED, cmd
                    return out(REJECT, "abstain_timeout", cmd)
                # quan sát đủ lâu, bằng chứng đã đủ -> rơi xuống thực thi

        if prog < 1.0:
            return out(REJECT, "holding", cmd, prog)
        if cmd in self.cfg.confirm_commands:
            self.state, self.pending, self.confirm_start = CONFIRM, cmd, t
            self._reset_candidate()
            return out(REJECT, "confirm", cmd)
        return self._execute(t, cmd, out)
