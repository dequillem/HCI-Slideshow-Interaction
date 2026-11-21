from src.config import Config
from src.decision.policies import Context, get_policy


def test_fixed_uses_config_values():
    g = get_policy("fixed")(Config(conf=0.8, hold_ms=400), Context(0, 0.0))
    assert (g.min_conf, g.hold_ms, g.require_arm, g.abstain) == (0.8, 400, True, False)


def test_naive_has_no_gate():
    g = get_policy("naive")(Config(), Context(0, 0.0))
    assert not g.require_arm and g.hold_ms == 0


def test_adaptive_speed_stricter_when_hand_moves_fast():
    still = get_policy("adaptive_speed")(Config(), Context(0, 0.0))
    fast = get_policy("adaptive_speed")(Config(), Context(0, 3.0))
    assert fast.min_conf > still.min_conf and fast.hold_ms > still.hold_ms


def test_abstain_and_combined_can_abstain():
    assert get_policy("abstain")(Config(), Context(0, 0.0)).abstain
    assert get_policy("combined")(Config(), Context(0, 0.0)).abstain
