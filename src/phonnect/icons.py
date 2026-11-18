"""App and tray icons, drawn from Lucide's "monitor-smartphone" icon.

Lucide (https://lucide.dev) is ISC licensed, (c) Lucide Icons and Contributors.
Pillow can't render SVG, so the icon's paths (24x24 grid, stroke width 2, round
caps and joins) are reproduced here as polylines and drawn with supersampling.

    <path d="M18 8V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h8" />
    <path d="M10 19v-3.96 3.15" />
    <path d="M7 19h5" />
    <rect width="6" height="10" x="16" y="12" rx="2" />
"""

from __future__ import annotations

import math
from pathlib import Path

from phonnect import paths
from phonnect.osutil import IS_WINDOWS

GREEN = (61, 220, 132, 255)  # a phone is connected
RED = (235, 87, 87, 255)  # adb/scrcpy not found
BACKGROUND = (32, 33, 36, 255)  # app icon tile
WHITE = (245, 245, 245, 255)
DARK = (40, 40, 40, 255)


def _arc(cx: float, cy: float, r: float, start: float, end: float, steps: int = 10):
    """Points on a circle, angles in degrees, screen coordinates (y down)."""
    return [
        (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
        for a in (start + (end - start) * i / steps for i in range(steps + 1))
    ]


MONITOR = [
    (18, 8),
    *_arc(16, 6, 2, 0, -90),  # (18,6) -> (16,4)
    *_arc(4, 6, 2, -90, -180),  # (4,4) -> (2,6)
    *_arc(4, 13, 2, 180, 90),  # (2,13) -> (4,15)
    (12, 15),
]
STAND = [(10, 15.04), (10, 19)]
BASE = [(7, 19), (12, 19)]
PHONE = (16, 12, 22, 22)  # x0, y0, x1, y1, corner radius 2


def draw_symbol(size: int, stroke, phone_fill=None, supersample: int = 4):
    """The bare Lucide symbol on a transparent background."""
    from PIL import Image, ImageDraw

    big = size * supersample
    k = big / 24
    w = 2 * k
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for line in (MONITOR, STAND, BASE):
        pts = [(x * k, y * k) for x, y in line]
        d.line(pts, fill=stroke, width=round(w), joint="curve")
        for x, y in (pts[0], pts[-1]):  # round caps
            d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=stroke)
    x0, y0, x1, y1 = (v * k for v in PHONE)
    if phone_fill is not None:
        d.rounded_rectangle((x0, y0, x1, y1), radius=2 * k, fill=phone_fill)
    # Pillow draws outlines inside the box; grow it so the stroke is centred on the path.
    d.rounded_rectangle(
        (x0 - w / 2, y0 - w / 2, x1 + w / 2, y1 + w / 2), radius=2 * k + w / 2, outline=stroke, width=round(w)
    )
    return img.resize((size, size), Image.LANCZOS)


def app_icon(size: int = 256):
    """Symbol on a dark rounded tile, with a green phone."""
    from PIL import Image, ImageDraw

    big = size * 4
    tile = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, big - 1, big - 1), radius=big * 0.22, fill=BACKGROUND)
    tile = tile.resize((size, size), Image.LANCZOS)
    inner = round(size * 0.72)
    symbol = draw_symbol(inner, WHITE, phone_fill=GREEN)
    offset = (size - inner) // 2
    tile.alpha_composite(symbol, (offset, offset))
    return tile


def tray_icon(state: str):
    """state: 'connected' (green phone), 'waiting' (outline only) or 'problem' (red phone)."""
    if IS_WINDOWS:
        from phonnect.theme import system_is_light

        stroke = DARK if system_is_light() else WHITE
    else:
        stroke = (160, 160, 160, 255)  # readable on light and dark menu bars / panels
    fill = {"connected": GREEN, "problem": RED}.get(state)
    return draw_symbol(64, stroke, phone_fill=fill)


ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def ensure_icon_files() -> tuple[Path, Path]:
    """Write icon.ico (Windows shortcuts) and icon.png (Linux, Tk windows). Returns (ico, png)."""
    folder = paths.state_dir()
    folder.mkdir(parents=True, exist_ok=True)
    ico, png = folder / "icon.ico", folder / "icon.png"
    big = app_icon(256)
    big.save(png)
    # Each size drawn separately: much crisper at 16-32 px than downscaling the 256 px image.
    frames = [app_icon(s) for s in ICO_SIZES]
    frames[-1].save(ico, sizes=[(s, s) for s in ICO_SIZES], append_images=frames[:-1])
    return ico, png
