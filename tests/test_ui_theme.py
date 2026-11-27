"""Màu giao diện đạt WCAG 2.1 AA: chữ thường >= 4.5:1, thành phần giao diện >= 3:1."""
from src.ui.status_model import OFF_COLOR, STATE_VIEW
from src.ui.theme import BADGE, C, contrast


def test_text_on_surfaces():
    for bg in ("surface", "surface_alt", "bg", "accent_soft"):
        for fg in ("text", "text_2", "text_3", "accent_hover"):
            assert contrast(C[fg], C[bg]) >= 4.5, (fg, bg)


def test_white_text_on_colored_fills():
    fills = [C[k] for k in ("accent", "accent_hover", "danger", "success", "warning", "violet", "teal", "neutral")]
    fills += [v[1] for v in STATE_VIEW.values()] + list(BADGE.values()) + [OFF_COLOR]
    for f in fills:
        assert contrast(C["on_color"], f) >= 4.5, f


def test_ui_components_and_hud():
    assert contrast(C["border_ui"], C["surface"]) >= 3.0       # viền ô chọn, công tắc
    assert contrast(C["focus"], C["surface"]) >= 3.0
    assert contrast(C["disabled_fg"], C["disabled_bg"]) >= 3.0  # không bắt buộc với thành phần tắt, nhưng vẫn đọc được
    for fg in ("hud_text", "hud_muted"):
        assert contrast(C[fg], C["hud_bg"]) >= 4.5
