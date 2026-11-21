"""C2 adaptive (ngưỡng theo độ mơ hồ) và C3 abstention (chưa chắc -> quan sát thêm -> chấp nhận / từ chối)."""
from src.config import Config
from src.datatypes import ACCEPT, UNCERTAIN, FeatureWindow, Hypothesis
from src.decision.gate import IntentGate
from src.decision.policies import Context, ambiguity_conf, get_policy

DT = 33
BASE = dict(require_arm=False, conf=0.8, hold_ms=300, cooldown_ms=800, reverse_block_ms=2500, margin=0.25,
            abstain_wait_ms=600, clear_conf=0.9, conflict_floor=0.5, conflict_window_ms=700)


def swipe(t, p_next, p_prev):
    probs = {"next": p_next, "previous": p_prev, "none": round(1 - p_next - p_prev, 6)}
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    label = ranked[0][0]
    return Hypothesis(t, True, label, probs, ranked[0][1] - ranked[1][1], label if label != "none" else None,
                      {"next": p_next, "previous": p_prev})


def run(policy, segments, **kw):
    """segments = [(thời lượng ms, p_next, p_prev)] -> (lệnh được thực thi [(t, lệnh)], mọi Decision)."""
    gate, acc, decs, t = IntentGate(Config(policy=policy, **{**BASE, **kw})), [], [], 0
    for dur, pn, pp in segments:
        for _ in range(dur // DT):
            d = gate(FeatureWindow(t, True), swipe(t, pn, pp))
            decs.append(d)
            if d.verdict == ACCEPT:
                acc.append((t, d.command))
            t += DT
    return acc, decs


# ---------- C2: ngưỡng thích ứng ----------

def test_adaptive_threshold_formula_matches_research_repo():
    cfg = Config(conf=0.8)  # mặc định giống HCI-project: min 0.70, max 0.95, margin_weight 0.20, stability_weight 0.15
    assert ambiguity_conf(cfg, Context(0, 0.0, margin=1.0)) == 0.8                     # rõ ràng: giữ ngưỡng gốc
    assert abs(ambiguity_conf(cfg, Context(0, 0.0, margin=0.5)) - 0.9) < 1e-9          # mơ hồ: +0.2 * 0.5
    assert abs(ambiguity_conf(cfg, Context(0, 0.0, 0.8, 0.6, True)) - 0.90) < 1e-9     # +0.04 margin +0.06 bất ổn
    assert ambiguity_conf(cfg, Context(0, 0.0, 0.2, 0.0, True)) == 0.95                # kẹp trần
    assert ambiguity_conf(cfg, Context(0, 0.0, 1.0, 0.0, False)) == 0.8                # khung đầu: không phạt bất ổn


def test_research_policies_honour_require_arm():
    for name in ("fixed", "adaptive", "abstain", "combined"):
        assert not get_policy(name)(Config(require_arm=False), Context(0, 0.0)).require_arm
        assert get_policy(name)(Config(require_arm=True), Context(0, 0.0)).require_arm


def test_adaptive_rejects_unstable_swipe_that_fixed_accepts():
    # previous ngắn rồi next 0.86: next bị chuỗi previous trước đó làm "bất ổn" -> ngưỡng adaptive > 0.86
    seg = [(200, 0.03, 0.86), (500, 0.86, 0.03)]
    fixed, _ = run("fixed", seg, hold_ms=100)
    adaptive, _ = run("adaptive", seg, hold_ms=100)
    assert [c for _, c in fixed] == ["previous"]
    assert all(c != "next" for _, c in adaptive) and len(adaptive) <= len(fixed)


# ---------- C3: abstention ----------

def test_clear_swipe_is_not_delayed_by_abstention():
    seg = [(1000, 0.97, 0.01)]
    fixed, _ = run("fixed", seg)
    abst, _ = run("abstain", seg)
    assert fixed == abst and [c for _, c in abst] == ["next"]


def test_lead_in_wrong_direction_is_suppressed():
    # đoạn lấy đà đọc thành previous 0.85 (400 ms), rồi cú vuốt thật next 0.99
    seg = [(400, 0.05, 0.85), (1500, 0.99, 0.005)]
    fixed, _ = run("fixed", seg)
    abst, decs = run("abstain", seg)
    assert [c for _, c in fixed] == ["previous"]          # fixed bắn nhầm chiều, rồi reverse_block chặn luôn lệnh đúng
    assert [c for _, c in abst] == ["next"]               # abstention chờ thêm -> chỉ thực thi chiều đúng
    assert any(d.verdict == UNCERTAIN and "conflict" in d.reason for d in decs)


def test_gray_zone_waits_then_rejects_once():
    seg = [(2000, 0.75, 0.02)]  # dưới ngưỡng 0.8 suốt
    fixed, fdecs = run("fixed", seg)
    abst, decs = run("abstain", seg)
    assert fixed == [] and abst == []
    assert any(d.verdict == UNCERTAIN for d in decs) and not any(d.verdict == UNCERTAIN for d in fdecs)
    assert sum(d.reason == "abstain_timeout" for d in decs) == 1  # từ chối một lần, giữ tay không bị đánh giá lại


def test_gray_zone_that_firms_up_is_accepted():
    abst, _ = run("abstain", [(300, 0.75, 0.02), (600, 0.97, 0.01)])
    assert [c for _, c in abst] == ["next"]


def test_medium_confidence_waits_longer_but_is_accepted():
    seg = [(1500, 0.85, 0.02)]  # qua ngưỡng nhưng dưới clear_conf
    fixed, _ = run("fixed", seg)
    abst, _ = run("abstain", seg)
    assert [c for _, c in abst] == ["next"]
    assert abst[0][0] - fixed[0][0] >= 600 - 300 - DT  # chờ abstain_wait_ms thay vì chỉ hold_ms


def test_combined_is_registered_and_abstains():
    _, decs = run("combined", [(2000, 0.75, 0.02)])
    assert any(d.verdict == UNCERTAIN for d in decs)
