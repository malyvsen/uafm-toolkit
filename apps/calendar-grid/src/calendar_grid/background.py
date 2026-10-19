"""Seeded parametric graphite background for the weekly timetable."""

import random
from datetime import date

from PIL import Image, ImageDraw, ImageFilter

BASE = (32, 36, 43)
SLATE_TONES = [
    (74, 85, 104),
    (47, 58, 70),
    (107, 122, 144),
    (23, 27, 33),
]
SMALL_WIDTH = 384
BLUR_RADIUS = 25


def background_for_week(monday: date, width: int, height: int) -> Image.Image:
    """Render a deterministic graphite wash seeded by the week-start Monday."""
    rng = random.Random(monday.toordinal())
    small_height = max(1, round(height * SMALL_WIDTH / width))
    canvas = Image.new("RGB", (SMALL_WIDTH, small_height), BASE)
    draw = ImageDraw.Draw(canvas)
    for _ in range(rng.randint(5, 7)):
        color = rng.choice(SLATE_TONES)
        blob_w = rng.randint(SMALL_WIDTH // 2, int(SMALL_WIDTH * 1.2))
        blob_h = rng.randint(small_height // 2, int(small_height * 1.2))
        x0 = rng.randint(-blob_w // 2, SMALL_WIDTH - blob_w // 2)
        y0 = rng.randint(-blob_h // 2, small_height - blob_h // 2)
        draw.ellipse([x0, y0, x0 + blob_w, y0 + blob_h], fill=color)
    full = canvas.resize((width, height), Image.Resampling.BICUBIC)
    return full.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
