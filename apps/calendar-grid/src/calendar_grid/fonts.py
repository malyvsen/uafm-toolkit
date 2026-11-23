"""Find a serif font across macOS, Windows, and Linux."""

from functools import cache
from pathlib import Path
from typing import Literal

from PIL import ImageFont

FontStyle = Literal["regular", "bold", "italic"]

_FONT_DIRS = [
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path.home() / "Library" / "Fonts",
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts"),
    Path.home() / ".fonts",
    Path.home() / ".local" / "share" / "fonts",
]
_FONT_CANDIDATES: dict[FontStyle, list[str]] = {
    "regular": [
        "Georgia.ttf",
        "georgia.ttf",
        "DejaVuSerif.ttf",
        "LiberationSerif-Regular.ttf",
        "NotoSerif-Regular.ttf",
    ],
    "bold": [
        "Georgia Bold.ttf",
        "georgiab.ttf",
        "DejaVuSerif-Bold.ttf",
        "LiberationSerif-Bold.ttf",
        "NotoSerif-Bold.ttf",
    ],
    "italic": [
        "Georgia Italic.ttf",
        "georgiai.ttf",
        "DejaVuSerif-Italic.ttf",
        "LiberationSerif-Italic.ttf",
        "NotoSerif-Italic.ttf",
    ],
}


@cache
def font(style: FontStyle, size: int) -> ImageFont.FreeTypeFont:
    """Return the cached serif font for `style` at `size` points."""
    for directory in _FONT_DIRS:
        for candidate in _FONT_CANDIDATES[style]:
            path = directory / candidate
            if path.exists():
                return ImageFont.truetype(str(path), size)
    raise RuntimeError(f"No serif font found for style {style!r}")
