"""Tùy chọn thí nghiệm của gate (mặc định tắt): swipe_conf, grace_ms, stability_reset."""
from tests.test_ambiguity_policies import run


def names(seg, policy="fixed", **kw):
    return [c for _, c in run(policy, seg, **kw)[0]]


def test_swipe_conf_replaces_conf_for_swipes_only_when_set():
    seg = [(600, 0.85, 0.02)]
    assert names(seg) == ["next"]
    assert names(seg, swipe_conf=0.9) == []
    assert names([(600, 0.75, 0.02)], conf=0.9, swipe_conf=0.7) == ["next"]


def test_grace_bridges_short_dropout_only():
    seg = [(200, 0.95, 0.01), (66, 0.02, 0.01), (170, 0.95, 0.01)]
    assert names(seg) == []
    assert names(seg, grace_ms=150) == ["next"]
    assert names(seg, grace_ms=50) == []


def test_keeping_history_makes_window_length_matter():
    seg = [(290, 0.02, 0.97), (1500, 0.02, 0.01), (500, 0.88, 0.02)]
    kw = dict(policy="adaptive", hold_ms=300, stability_weight=0.3, adapt_max_conf=0.99, stability_reset=False)
    short = names(seg, stability_window_ms=800, **kw)
    long = names(seg, stability_window_ms=5000, **kw)
    assert short == ["next"] and long == []
