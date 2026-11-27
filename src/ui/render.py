"""Vẽ hình mượt cho Canvas Tk: Tk không khử răng cưa, nên mọi hình (bo góc, tròn, chuyển sắc, bóng, logo, tranh cử chỉ)
được vẽ bằng Pillow ở kích thước gấp SS lần rồi thu nhỏ, trả về PhotoImage (có kênh alpha). Ảnh được nhớ đệm theo tham số."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk

from .theme import C

SS = 4                   # hệ số vẽ phóng to (siêu lấy mẫu)
_cache: dict = {}


def rgba(c, alpha=None):
    if c is None:
        return (0, 0, 0, 0)
    c = c.lstrip("#")
    v = [int(c[i:i + 2], 16) for i in (0, 2, 4)] + [int(c[6:8], 16) if len(c) == 8 else 255]
    if alpha is not None:
        v[3] = int(255 * alpha)
    return tuple(v)


def _photo(widget, key, build):
    k = (str(widget.winfo_toplevel()), key)
    if k not in _cache:
        _cache[k] = ImageTk.PhotoImage(build(), master=widget)
    return _cache[k]


def _gradient(w, h, c1, c2, diagonal=False):
    a, b = np.array(rgba(c1), float), np.array(rgba(c2), float)
    x = np.linspace(0, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]
    t = (x + y) / 2 if diagonal else np.repeat(x, h, axis=0)
    arr = a + (b - a) * t[..., None]
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def _mask(W, H, r, inset=0):
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([inset, inset, W - 1 - inset, H - 1 - inset], max(0, r - inset), fill=255)
    return m


def shape_image(w, h, r, fill=None, outline=None, width=0, grad=None, shadow=None):
    """Hình chữ nhật bo góc w x h. grad=(màu1, màu2) chuyển sắc ngang; shadow=(độ mờ, lệch xuống, độ đậm)
    -> ảnh to hơn mỗi phía `margin(shadow)` px để chứa bóng."""
    W, H, R = w * SS, h * SS, r * SS
    base_rgb = rgba(fill or (grad[0] if grad else outline) or "#000000")[:3]
    img = Image.new("RGBA", (W, H), base_rgb + (0,))          # nền trong suốt cùng màu -> không viền đen khi thu nhỏ
    if grad or fill:
        src = _gradient(W, H, *grad) if grad else Image.new("RGBA", (W, H), rgba(fill))
        img.paste(src, (0, 0), _mask(W, H, R))
    if outline and width:
        ImageDraw.Draw(img).rounded_rectangle([0, 0, W - 1, H - 1], R, outline=rgba(outline), width=max(1, round(width * SS)))
    img = img.resize((w, h), Image.LANCZOS)
    if not shadow:
        return img
    blur, dy, alpha = shadow
    m = margin(shadow)
    sm = Image.new("L", (w + 2 * m, h + 2 * m), 0)
    ImageDraw.Draw(sm).rounded_rectangle([m, m + dy, m + w - 1, m + dy + h - 1], r, fill=int(255 * alpha))
    sm = sm.filter(ImageFilter.GaussianBlur(blur / 2))
    out = Image.new("RGBA", sm.size, rgba(C["shadow"])[:3] + (0,))
    out.putalpha(sm)
    out.alpha_composite(img, (m, m))
    return out


def margin(shadow) -> int:
    return 0 if not shadow else shadow[0] + abs(shadow[1])


def shape(widget, w, h, r, **kw):
    w, h = max(2, int(w)), max(2, int(h))
    key = ("shape", w, h, int(r), tuple(sorted((k, v) for k, v in kw.items())))
    return _photo(widget, key, lambda: shape_image(w, h, int(r), **kw))


def circle(widget, d, **kw):
    return shape(widget, d, d, d // 2, **kw)


def icon(widget, kind, size, color):
    """Biểu tượng nhỏ: play | stop | book | camera."""
    def build():
        S = size * SS
        im = Image.new("RGBA", (S, S), rgba(color)[:3] + (0,))
        d, col = ImageDraw.Draw(im), rgba(color)
        if kind == "play":
            d.polygon([(S * .24, S * .14), (S * .24, S * .86), (S * .88, S * .5)], fill=col)
        elif kind == "stop":
            d.rounded_rectangle([S * .18, S * .18, S * .82, S * .82], S * .12, fill=col)
        elif kind == "book":
            lw = max(1, round(S * .09))
            d.rounded_rectangle([S * .08, S * .16, S * .5, S * .84], S * .08, outline=col, width=lw)
            d.rounded_rectangle([S * .5, S * .16, S * .92, S * .84], S * .08, outline=col, width=lw)
        return im.resize((size, size), Image.LANCZOS)
    return _photo(widget, ("icon", kind, size, color), build)


def logo_image(size):
    """Logo: ô vuông bo góc chuyển sắc chàm -> tím, bên trong là màn chiếu với mũi tên "tiếp" và vệt vuốt."""
    S = size * SS
    im = _gradient(S, S, C["accent"], C["accent_2"], diagonal=True)
    im.putalpha(_mask(S, S, int(S * .28)))
    d = ImageDraw.Draw(im)
    white, lw = (255, 255, 255, 255), max(2, round(S * .065))
    d.rounded_rectangle([S * .2, S * .24, S * .8, S * .66], S * .07, outline=white, width=lw)      # màn chiếu
    d.line([(S * .5, S * .66), (S * .5, S * .78)], fill=white, width=lw)                          # chân
    d.line([(S * .38, S * .79), (S * .62, S * .79)], fill=white, width=lw)
    d.line([(S * .45, S * .35), (S * .56, S * .45), (S * .45, S * .55)], fill=white, width=lw, joint="curve")   # mũi tên
    for i, y in enumerate((.38, .45, .52)):                                                         # vệt vuốt
        d.line([(S * (.28 + .03 * abs(i - 1)), S * y), (S * .37, S * y)], fill=(255, 255, 255, 170), width=max(1, lw // 2))
    return im.resize((size, size), Image.LANCZOS)


def logo(widget, size):
    return _photo(widget, ("logo", size), lambda: logo_image(size))


def picture(widget, path: Path, size: int, radius: int):
    """Tranh minh họa cử chỉ: thu/phóng mượt về `size` px vuông, bo góc."""
    def build():
        im = Image.open(path).convert("RGBA").resize((size * 2, size * 2), Image.LANCZOS)
        im.putalpha(_mask(size * 2, size * 2, radius * 2))
        return im.resize((size, size), Image.LANCZOS)
    return _photo(widget, ("pic", str(path), size, radius), build)


def window_bg(widget, w, h, r, fill, key_color):
    """Nền bo góc cho cửa sổ không viền: phần ngoài góc là `key_color` (màu trong suốt của Windows).
    Viền khử răng cưa trộn với nền tối nên không lộ màu khóa."""
    def build():
        base = Image.new("RGBA", (w, h), rgba(key_color))
        base.alpha_composite(shape_image(w, h, r, fill=fill))
        # chỉ giữ điểm ảnh gần như đặc: điểm nửa trong suốt trộn với màu khóa sẽ thành viền lạ
        arr = np.array(base)
        inside = np.array(shape_image(w, h, r, fill=fill))[..., 3] > 40
        arr[~inside] = rgba(key_color)
        arr[inside, 3] = 255
        return Image.fromarray(arr, "RGBA")
    return _photo(widget, ("win", w, h, r, fill, key_color), build)
