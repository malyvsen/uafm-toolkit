"""Turn a week's events into a Pillow image in the humanistic timetable style."""

import re
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from plan_parser import Event

CREAM = (246, 241, 227)
INK = (43, 38, 33)
FAINT = (214, 202, 178)
MUTED = (122, 112, 94)
WAR_YELLOW = (233, 202, 110)
WYK_ORANGE = (216, 142, 93)
KON_PINK = (229, 168, 178)

START_HOUR = 8
END_HOUR = 22
HOUR_H = 100
COL_W = 300
AXIS_W = 76
MARGIN_X = 36
MARGIN_TOP = 48
MARGIN_BOTTOM = 48
TITLE_SIZE = 64
SUBTITLE_SIZE = 30
DAY_SIZE = 26
AXIS_SIZE = 20
SUBJECT_SIZE = 24
META_SIZE = 21
LEGEND_SIZE = 24
LONG_BLOCK_MINUTES = 120

DAY_NAMES = [
    "Poniedziałek",
    "Wtorek",
    "Środa",
    "Czwartek",
    "Piątek",
    "Sobota",
    "Niedziela",
]
MONTHS = [
    "stycznia",
    "lutego",
    "marca",
    "kwietnia",
    "maja",
    "czerwca",
    "lipca",
    "sierpnia",
    "września",
    "października",
    "listopada",
    "grudnia",
]
FORM_STYLES = {
    "War": ("Warsztaty", WAR_YELLOW),
    "Wyk": ("Wykład", WYK_ORANGE),
    "Kon": ("Konwersatorium", KON_PINK),
}

_FONT_DIR = Path("/System/Library/Fonts/Supplemental")
_FONT_FILES = {
    "regular": "Georgia.ttf",
    "bold": "Georgia Bold.ttf",
    "italic": "Georgia Italic.ttf",
}

_BUILDING_RE = re.compile(r"^bud\.\S+\s*")
_GENERIC_ROOM_WORDS = {"SALA", "SALE", "PRACOWNIA", "AULA", "HALA"}


def render_week(events: list[Event]) -> Image.Image:
    """Render events from one Monday-to-Sunday week as a PNG-ready image."""
    if not events:
        raise ValueError("Cannot render a week with no events")
    monday = min(e.date for e in events)
    monday -= timedelta(days=monday.weekday())
    weekend = any(e.date.weekday() >= 5 for e in events)
    days = [monday + timedelta(days=i) for i in range(7 if weekend else 5)]

    width = MARGIN_X + AXIS_W + len(days) * COL_W + MARGIN_X
    grid_top = MARGIN_TOP + 76 + 8 + 40 + 30 + 36 + 12
    height = grid_top + (END_HOUR - START_HOUR) * HOUR_H + MARGIN_BOTTOM

    image = Image.new("RGB", (width, height), CREAM)
    draw = ImageDraw.Draw(image)
    _draw_header(draw, width, monday, days[-1], events)
    _draw_grid(draw, days, grid_top)
    for event in sorted(events, key=lambda e: (e.date, e.start)):
        _draw_event(draw, event, days, grid_top)
    return image


def _draw_header(
    draw: ImageDraw.ImageDraw, width: int, monday: date, last: date, events: list[Event]
) -> None:
    title = _font("bold", TITLE_SIZE)
    subtitle_font = _font("regular", SUBTITLE_SIZE)
    draw.text((MARGIN_X, MARGIN_TOP), "Plan zajęć", font=title, fill=INK)
    subtitle = _week_range(monday, last)
    subtitle_top = MARGIN_TOP + 76 + 8
    draw.text((MARGIN_X, subtitle_top), subtitle, font=subtitle_font, fill=INK)
    bottom = draw.textbbox((MARGIN_X, subtitle_top), subtitle, font=subtitle_font)[3]
    _draw_legend(draw, width, bottom, events)


def _week_range(monday: date, last: date) -> str:
    if monday.month == last.month:
        return f"{monday.day}–{last.day} {MONTHS[last.month - 1]} {last.year}"
    if monday.year == last.year:
        return (
            f"{monday.day} {MONTHS[monday.month - 1]} – "
            f"{last.day} {MONTHS[last.month - 1]} {last.year}"
        )
    return (
        f"{monday.day} {MONTHS[monday.month - 1]} {monday.year} – "
        f"{last.day} {MONTHS[last.month - 1]} {last.year}"
    )


def _draw_legend(
    draw: ImageDraw.ImageDraw, width: int, subtitle_bottom: float, events: list[Event]
) -> None:
    forms = [e.form for e in events]
    ordered = [f for f in ("War", "Wyk", "Kon") if f in forms]
    # Unknown non-empty forms keep their code as the label; an empty form has no label to show.
    ordered += sorted({f for f in forms if f and f not in FORM_STYLES})
    font = _font("regular", LEGEND_SIZE)
    chip_w, chip_h, gap = 36, 28, 12
    total_h = len(ordered) * (chip_h + gap) - gap
    y = subtitle_bottom - total_h
    for form in ordered:
        label, color = FORM_STYLES.get(form, (form, INK))
        spine_color = CREAM if form not in FORM_STYLES else INK
        x = width - MARGIN_X - chip_w - 12 - draw.textlength(label, font=font)
        draw.rectangle([x, y, x + chip_w, y + chip_h], fill=color, outline=INK, width=2)
        draw.rectangle([x, y, x + 7, y + chip_h], fill=spine_color)
        draw.text(
            (x + chip_w + 12, y + chip_h / 2),
            label,
            font=font,
            fill=INK,
            anchor="lm",
        )
        y += chip_h + gap


def _draw_grid(draw: ImageDraw.ImageDraw, days: list[date], grid_top: int) -> None:
    left = MARGIN_X + AXIS_W
    right = left + len(days) * COL_W
    bottom = grid_top + (END_HOUR - START_HOUR) * HOUR_H
    axis_font = _font("regular", AXIS_SIZE)
    for hour in range(START_HOUR, END_HOUR + 1):
        y = grid_top + (hour - START_HOUR) * HOUR_H
        draw.line(
            [(left, y), (right, y)], fill=FAINT if hour > START_HOUR else INK, width=2
        )
        draw.text(
            (left - 12, y),
            f"{hour}:00",
            font=axis_font,
            fill=MUTED,
            anchor="rm",
        )
    day_font = _font("regular", DAY_SIZE)
    for i, day in enumerate(days):
        x = left + i * COL_W
        if i > 0:
            draw.line([(x, grid_top), (x, bottom)], fill=INK, width=2)
        draw.text(
            (x + COL_W / 2, grid_top - 12 - 18),
            f"{DAY_NAMES[day.weekday()]}, {day.day}.{day.month:02d}",
            font=day_font,
            fill=INK,
            anchor="mm",
        )
    draw.rectangle([left, grid_top, right, bottom], outline=INK, width=2)


def _draw_event(
    draw: ImageDraw.ImageDraw, event: Event, days: list[date], grid_top: int
) -> None:
    col = (event.date - days[0]).days
    top = grid_top + _minutes_since_start(event) * HOUR_H / 60
    bottom = grid_top + _minutes_until_end(event) * HOUR_H / 60
    x = MARGIN_X + AXIS_W + col * COL_W + 5
    box = [x, top, x + COL_W - 10, bottom]
    _, color = FORM_STYLES.get(event.form, (event.form, INK))
    dark = event.form not in FORM_STYLES
    draw.rectangle(box, fill=color, outline=INK, width=2)
    draw.rectangle([x, top, x + 8, bottom], fill=CREAM if dark else INK)

    text_w = COL_W - 10 - 8 - 18
    long = (event.end.hour * 60 + event.end.minute) - (
        event.start.hour * 60 + event.start.minute
    ) >= LONG_BLOCK_MINUTES
    time_range = f"{event.start.hour}:{event.start.minute:02d}–{event.end.hour}:{event.end.minute:02d}"
    room = format_room(event.room)
    subject_font = _font("bold", SUBJECT_SIZE)
    meta_font = _font("italic", META_SIZE)
    if long:
        lines = [
            (l, subject_font, 30)
            for l in _wrap(event.subject, subject_font, text_w, 2, draw)
        ]
        lines.append((time_range, meta_font, 27))
        if room:
            lines.append((room, meta_font, 27))
    else:
        lines = [
            (l, subject_font, 30)
            for l in _wrap(event.subject, subject_font, text_w, 1, draw)
        ]
        meta = time_range if not room else f"{time_range} · {room}"
        lines.append((_truncate(meta, meta_font, text_w, draw), meta_font, 27))

    available = bottom - top - 20
    y = top + 10
    for text, font, step in lines:
        if y + step - 8 > top + available + 10:
            break
        draw.text((x + 8 + 12, y), text, font=font, fill=CREAM if dark else INK)
        y += step


def _minutes_since_start(event: Event) -> float:
    return (event.start.hour - START_HOUR) * 60 + event.start.minute


def _minutes_until_end(event: Event) -> float:
    return (event.end.hour - START_HOUR) * 60 + event.end.minute


def format_room(raw: str) -> str:
    """Shorten a raw room cell (`bud.D D - 02 - SALA BALETOWA`) for display."""
    code, sep, descriptor = raw.rpartition(" - ")
    code = _BUILDING_RE.sub("", code if sep else raw)
    code = re.sub(r"-\s+", "-", code).strip()
    words = [w for w in descriptor.split() if w not in _GENERIC_ROOM_WORDS]
    detail = " ".join(words).lower()
    if "-" in code and detail:
        return f"sala {code} · {detail}"
    return f"sala {code}"


def _wrap(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: float,
    lines: int,
    draw: ImageDraw.ImageDraw,
) -> list[str]:
    out: list[str] = []
    for word in text.split():
        if out and draw.textlength(out[-1] + " " + word, font=font) <= max_width:
            out[-1] += " " + word
        elif len(out) < lines:
            out.append(word)
        else:
            out[-1] += " " + word
    if out:
        out[-1] = _truncate(out[-1], font, max_width, draw)
    return out


def _truncate(
    text: str, font: ImageFont.FreeTypeFont, max_width: float, draw: ImageDraw.ImageDraw
) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


@cache
def _font(style: str, size: int) -> ImageFont.FreeTypeFont:
    path = _FONT_DIR / _FONT_FILES[style]
    if not path.exists():
        raise RuntimeError(f"System font not found: {path}")
    return ImageFont.truetype(str(path), size)
