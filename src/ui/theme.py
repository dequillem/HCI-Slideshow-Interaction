"""Design tokens của giao diện: tên, màu, chữ, khoảng cách, bo góc, bóng. Mọi màn hình chỉ lấy giá trị từ đây.

Độ nét: import module này sẽ bật chế độ "DPI aware" trên Windows (phải trước khi tạo cửa sổ Tk). Không bật thì Windows
kéo giãn cả cửa sổ lên 125–150% -> mờ, răng cưa. Mọi kích thước pixel đi qua px() để nhân theo tỉ lệ màn hình.

Tương phản theo WCAG 2.1 AA (kiểm tra ở tests/test_ui_theme.py):
  chữ thường >= 4.5:1 trên nền của nó; thành phần giao diện (viền ô chọn, công tắc) >= 3:1.
"""
from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "Glide"                                   # tên hiển thị; đổi ở đây là đổi mọi nơi
APP_TAGLINE = "Điều khiển slide bằng cử chỉ tay"


def _init_dpi() -> float:
    if sys.platform != "win32":
        return 1.0
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)      # system DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            return 1.0
    try:
        return max(1.0, ctypes.windll.user32.GetDpiForSystem() / 96)
    except Exception:
        return 1.0


SCALE = _init_dpi()


def px(v: float) -> int:
    """Pixel thiết kế (ở 96 dpi) -> pixel màn hình."""
    return int(round(v * SCALE))


FONT = "Lato"            # đóng gói trong assets/fonts (Windows); hệ khác Tk tự thay bằng font mặc định

C = {
    # nền và bề mặt
    "bg": "#F3F4F9",             # nền cửa sổ
    "surface": "#FFFFFF",        # thẻ, thanh bên
    "surface_alt": "#F7F8FC",    # hàng đang rê chuột
    "segment": "#ECEEF6",        # rãnh của nút chọn hai phía, ô phím
    "border": "#E3E6F0",         # viền trang trí
    "border_ui": "#7A8099",      # viền thành phần tương tác (>= 3:1 trên trắng)
    # chữ
    "text": "#15172E",
    "text_2": "#4A4F6B",
    "text_3": "#5C627E",
    "on_color": "#FFFFFF",
    # màu nhấn: chàm -> tím (chuyển sắc trên nút chính và logo)
    "accent": "#4F46E5", "accent_2": "#7C3AED",
    "accent_hover": "#4338CA", "accent_2_hover": "#6D28D9",
    "accent_press": "#3730A3", "accent_2_press": "#5B21B6",
    "accent_soft": "#EEF0FF", "accent_text": "#4338CA",
    # ngữ nghĩa (đều >= 4.5:1 với chữ trắng)
    "danger": "#DC2626", "danger_hover": "#B91C1C", "danger_press": "#991B1B",
    "success": "#047857", "warning": "#C2410C", "violet": "#7C3AED", "teal": "#0F766E", "neutral": "#52577A",
    "disabled_bg": "#E6E8F0", "disabled_fg": "#5C627E",
    "focus": "#4F46E5",
    "shadow": "#1B1F4B",         # màu bóng (độ đậm đặt bằng alpha trong SHADOW)
    # ô trạng thái nổi (nền tối)
    "hud_bg": "#14162B", "hud_track": "#2E3252", "hud_text": "#F8FAFC", "hud_muted": "#C3C7DB",
}

# Cỡ chữ (pt, Tk tự nhân theo DPI) và độ đậm: một thang duy nhất
TYPE = {
    "display": (FONT, 18, "bold"),
    "title": (FONT, 14, "bold"),
    "heading": (FONT, 11, "bold"),
    "body": (FONT, 10),
    "body_b": (FONT, 10, "bold"),
    "small": (FONT, 9),
    "small_b": (FONT, 9, "bold"),
    "caps": (FONT, 8, "bold"),
}

SPACE = {k: px(v) for k, v in {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}.items()}
RADIUS = px(10)          # nút, thẻ, ô chọn
RADIUS_SM = px(6)        # nhãn, ô phím
TARGET = px(44)          # chiều cao tối thiểu của vùng bấm
# bóng: (độ mờ px, lệch xuống px, độ đậm 0-1)
SHADOW = {"card": (px(14), px(4), 0.10), "raised": (px(4), px(1), 0.16), "float": (px(18), px(6), 0.28)}

# Bộ lọc lệnh: màu nhãn (chữ trắng)
BADGE = {"C1": C["accent"], "C2": C["teal"], "C3": C["warning"], "C4": C["violet"],
         "Mặc định": C["success"], "Không lọc": C["neutral"], "Khác": C["neutral"]}


def load_bundled_fonts() -> None:
    """Windows: đăng ký các .ttf/.otf trong assets/fonts cho riêng tiến trình này (không cài vào máy)."""
    font_dir = Path(__file__).parent / "assets" / "fonts"
    if sys.platform != "win32" or not font_dir.exists():
        return
    import ctypes
    for f in list(font_dir.glob("*.ttf")) + list(font_dir.glob("*.otf")):
        try:
            ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)      # 0x10 = FR_PRIVATE
        except Exception:
            pass


def mix(c1: str, c2: str, t: float) -> str:
    """Trộn màu: t = 0 -> c1, t = 1 -> c2."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def tint(color: str, t: float = 0.88) -> str:
    """Nền nhạt cùng tông với `color` (vd. nền nhãn trạng thái)."""
    return mix(color, "#FFFFFF", t)


def _lum(color: str) -> float:
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(fg: str, bg: str) -> float:
    """Tỉ lệ tương phản WCAG giữa hai màu #rrggbb."""
    a, b = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)
