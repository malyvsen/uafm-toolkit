"""Film grain and frosted-glass effects shared by the timetable renderers."""

import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from plan_render import style


def apply_grain(
    image: Image.Image, seed: int, sigma: int = 28, opacity: float = 0.14
) -> Image.Image:
    """Overlay deterministic monochrome film grain over the whole image."""
    width, height = image.size
    rng = random.Random(seed)
    raw = rng.randbytes(width * height)
    noise = Image.frombytes("L", (width, height), raw)
    scale = sigma / 64
    lut = [max(0, min(255, int(128 + (i - 128) * scale))) for i in range(256)]
    centered = noise.point(lut).convert("RGB")
    overlaid = ImageChops.overlay(image, centered)
    return Image.blend(image, overlaid, opacity)


def frost(
    canvas: Image.Image, box: tuple[int, int, int, int], alpha: float = 1.0
) -> None:
    """Frost an event block's background in place; `alpha` scales the white."""
    left, top, right, bottom = (int(v) for v in box)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return
    region = canvas.crop((left, top, right, bottom)).filter(
        ImageFilter.GaussianBlur(style.EVENT_BLUR_RADIUS)
    )
    white_alpha = round(style.EVENT_WHITE_ALPHA * alpha)
    white = Image.new("RGBA", (width, height), (255, 255, 255, white_alpha))
    frosted = Image.alpha_composite(region.convert("RGBA"), white)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, width, height], radius=style.EVENT_RADIUS, fill=255
    )
    canvas.paste(frosted, (left, top), mask)
