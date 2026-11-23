"""Turn a week's events into a Pillow image in the graphite-frost style."""

import random
import re
from collections.abc import Callable
from datetime import date, time, timedelta
from typing import Literal

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from calendar_grid.background import background_for_week
from calendar_grid.fonts import font
from plan_parser import Event

OFF_WHITE = (244, 245, 246)
SOFT_GREY = (185, 192, 201)
AXIS_LABEL = (244, 245, 246, 160)
HOUR_LINE = (255, 255, 255, 14)
EVENT_BORDER = (255, 255, 255, 90)
UNKNOWN_SPINE = (154, 163, 175)
WAR_YELLOW = (233, 202, 110)
WYK_ORANGE = (216, 142, 93)
KON_PINK = (229, 168, 178)

START_HOUR = 8
END_HOUR = 22
HOUR_H = 100
# Hour rows stop this far from event-block edges so lines never touch blocks.
HOUR_CLEARANCE = 4
COL_W = 300
GUTTER = 24
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

# Header geometry mirrors _draw_header: title line, gap, subtitle line,
# then day labels and gaps before the grid. Fixed offsets keep renders stable.
TITLE_H = 76
TITLE_GAP = 8
SUBTITLE_H = 40
DAY_LABEL_H = 30
DAY_LABEL_GAP = 36
GRID_GAP = 12
GRID_TOP = (
    MARGIN_TOP
    + TITLE_H
    + TITLE_GAP
    + SUBTITLE_H
    + DAY_LABEL_H
    + DAY_LABEL_GAP
    + GRID_GAP
)

# Class-block geometry: inset from the column edge, thick spine on the left,
# then text with a right inset. Text lines use 6pt leading.
BLOCK_PAD_X = 5
SPINE_W = 8
TEXT_GAP = 12
TEXT_PAD_RIGHT = 6
BLOCK_PAD_Y = 10
SUBJECT_STEP = 30
META_STEP = 27
LINE_SLACK = 8

# Frosted glass for event blocks: blur and white overlay, plus corner radius.
EVENT_BLUR_RADIUS = 14
EVENT_WHITE_ALPHA = 32
EVENT_RADIUS = 12

# Legend: bare spine bar plus label at a fixed gap, rows stacked with the same gap.
LEGEND_SPINE_W = 7
LEGEND_BAR_H = 28
LEGEND_GAP = 12

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

LineKind = Literal["subject", "meta"]
BlockLine = tuple[str, LineKind]
HourSegment = tuple[int, int]
BlockMeasure = Callable[[str, LineKind], float]
WidthMeasure = Callable[[str], float]

_BUILDING_RE = re.compile(r"^bud\.\S+\s*")
_GENERIC_ROOM_WORDS = {"SALA", "SALE", "PRACOWNIA", "AULA", "HALA"}


def render_week(events: list[Event]) -> Image.Image:
    """Render events from one Monday-to-Sunday week as a PNG-ready image."""
    if not events:
        raise ValueError("Cannot render a week with no events")
    first = min(e.date for e in events)
    monday = first - timedelta(days=first.weekday())
    weekend = any(e.date.weekday() >= 5 for e in events)
    days = [monday + timedelta(days=i) for i in range(7 if weekend else 5)]

    width = col_x(len(days) - 1) + COL_W + MARGIN_X
    grid_bottom = GRID_TOP + (END_HOUR - START_HOUR) * HOUR_H
    height = grid_bottom + MARGIN_BOTTOM

    # Two layers: `base` holds the background with frosted glass melted into it,
    # `overlay` holds lines, borders and text. They composite at the end.
    base = background_for_week(monday, width, height).convert("RGBA")

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    _draw_header(draw, width, monday, days[-1], events)
    _draw_grid(draw, days, GRID_TOP, hour_segments(days, events, GRID_TOP))
    for event in sorted(events, key=lambda e: (e.date, e.start)):
        _draw_event(base, draw, event, days, GRID_TOP)
    composited = Image.alpha_composite(base, overlay).convert("RGB")
    return apply_grain(composited, monday.toordinal())


def col_x(index: int) -> int:
    """Left edge of day column `index`."""
    return MARGIN_X + AXIS_W + index * (COL_W + GUTTER)


def hour_segments(
    days: list[date], events: list[Event], grid_top: int
) -> list[HourSegment]:
    """Left x and y of each hour-row segment, skipping rows covered by events."""
    spans: dict[int, list[tuple[float, float]]] = {}
    for event in events:
        col = (event.date - days[0]).days
        if 0 <= col < len(days):
            top = grid_top + _offset_minutes(event.start) * HOUR_H / 60
            bottom = grid_top + _offset_minutes(event.end) * HOUR_H / 60
            spans.setdefault(col, []).append((top, bottom))
    segments: list[HourSegment] = []
    for hour in range(START_HOUR, END_HOUR + 1):
        y = grid_top + (hour - START_HOUR) * HOUR_H
        for i in range(len(days)):
            covered = any(
                top - HOUR_CLEARANCE <= y <= bottom + HOUR_CLEARANCE
                for top, bottom in spans.get(i, [])
            )
            if not covered:
                segments.append((col_x(i), y))
    return segments


def legend_forms(events: list[Event]) -> list[str]:
    """Form codes in legend order: known forms first, then unknown alphabetically."""
    forms = [e.form for e in events]
    known = [form for form in FORM_STYLES if form in forms]
    # Unknown non-empty forms keep their code as the label; an empty form has no label to show.
    unknown = sorted({form for form in forms if form and form not in FORM_STYLES})
    return [*known, *unknown]


def apply_grain(
    image: Image.Image, seed: int, sigma: int = 28, opacity: float = 0.22
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


def _frost(base: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Frost an event block's background in place with blur + white."""
    left, top, right, bottom = (int(v) for v in box)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return
    region = base.crop((left, top, right, bottom)).filter(
        ImageFilter.GaussianBlur(EVENT_BLUR_RADIUS)
    )
    white = Image.new("RGBA", (width, height), (255, 255, 255, EVENT_WHITE_ALPHA))
    frosted = Image.alpha_composite(region.convert("RGBA"), white)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, width, height], radius=EVENT_RADIUS, fill=255
    )
    base.paste(frosted, (left, top), mask)


def _draw_header(
    draw: ImageDraw.ImageDraw,
    width: int,
    monday: date,
    last: date,
    events: list[Event],
) -> None:
    title = font("bold", TITLE_SIZE)
    subtitle_font = font("regular", SUBTITLE_SIZE)
    draw.text((MARGIN_X, MARGIN_TOP), "Plan zajęć", font=title, fill=OFF_WHITE)
    subtitle = _week_range(monday, last)
    subtitle_top = MARGIN_TOP + TITLE_H + TITLE_GAP
    draw.text((MARGIN_X, subtitle_top), subtitle, font=subtitle_font, fill=SOFT_GREY)
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
    draw: ImageDraw.ImageDraw,
    width: int,
    subtitle_bottom: float,
    events: list[Event],
) -> None:
    ordered = legend_forms(events)
    if not ordered:
        return
    label_font = font("regular", LEGEND_SIZE)
    styled = [FORM_STYLES.get(form, (form, UNKNOWN_SPINE)) for form in ordered]
    longest = max(draw.textlength(label, font=label_font) for label, _ in styled)
    block_x = width - MARGIN_X - LEGEND_SPINE_W - LEGEND_GAP - longest
    total_h = len(styled) * (LEGEND_BAR_H + LEGEND_GAP) - LEGEND_GAP
    y = subtitle_bottom - total_h
    for label, color in styled:
        draw.rectangle(
            [block_x, y, block_x + LEGEND_SPINE_W, y + LEGEND_BAR_H], fill=color
        )
        draw.text(
            (block_x + LEGEND_SPINE_W + LEGEND_GAP, y + LEGEND_BAR_H / 2),
            label,
            font=label_font,
            fill=OFF_WHITE,
            anchor="lm",
        )
        y += LEGEND_BAR_H + LEGEND_GAP


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    days: list[date],
    grid_top: int,
    segments: list[HourSegment],
) -> None:
    left = col_x(0)
    axis_font = font("regular", AXIS_SIZE)
    for hour in range(START_HOUR, END_HOUR + 1):
        y = grid_top + (hour - START_HOUR) * HOUR_H
        draw.text(
            (left - 12, y),
            f"{hour}:00",
            font=axis_font,
            fill=AXIS_LABEL,
            anchor="rm",
        )
    for x, y in segments:
        draw.line([(x, y), (x + COL_W, y)], fill=HOUR_LINE, width=2)
    day_font = font("regular", DAY_SIZE)
    for i, day in enumerate(days):
        x = col_x(i)
        draw.text(
            (x + 4, grid_top - DAY_LABEL_H),
            f"{DAY_NAMES[day.weekday()]}, {day.day}.{day.month:02d}",
            font=day_font,
            fill=OFF_WHITE,
            anchor="lm",
        )


def _draw_event(
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    event: Event,
    days: list[date],
    grid_top: int,
) -> None:
    col = (event.date - days[0]).days
    top = grid_top + _offset_minutes(event.start) * HOUR_H / 60
    bottom = grid_top + _offset_minutes(event.end) * HOUR_H / 60
    x = col_x(col) + BLOCK_PAD_X
    box = (x, top, x + COL_W - 2 * BLOCK_PAD_X, bottom)
    style = FORM_STYLES.get(event.form)
    spine_color = style[1] if style else UNKNOWN_SPINE
    _frost(
        base,
        (int(box[0]), int(box[1]), int(box[2]), int(box[3])),
    )
    draw.rounded_rectangle(box, radius=EVENT_RADIUS, outline=EVENT_BORDER, width=1)
    draw.rectangle([x, top, x + SPINE_W, bottom], fill=spine_color)

    text_w = COL_W - 2 * BLOCK_PAD_X - SPINE_W - TEXT_GAP - TEXT_PAD_RIGHT
    block_h = bottom - top
    time_range = f"{event.start.hour}:{event.start.minute:02d}–{event.end.hour}:{event.end.minute:02d}"
    room = format_room(event.room)
    subject_font = font("bold", SUBJECT_SIZE)
    meta_font = font("italic", META_SIZE)

    def measure(text: str, kind: LineKind) -> float:
        return draw.textlength(
            text, font=subject_font if kind == "subject" else meta_font
        )

    lines = layout_block(event.subject, time_range, room, text_w, block_h, measure)

    y = top + BLOCK_PAD_Y
    for text, kind in lines:
        draw.text(
            (x + SPINE_W + TEXT_GAP, y),
            text,
            font=subject_font if kind == "subject" else meta_font,
            fill=OFF_WHITE if kind == "subject" else SOFT_GREY,
        )
        y += _line_step(kind)


def layout_block(
    subject: str,
    time_range: str,
    room: str,
    text_w: float,
    block_h: float,
    measure: BlockMeasure,
) -> list[BlockLine]:
    def subject_width(text: str) -> float:
        return measure(text, "subject")

    def meta_width(text: str) -> float:
        return measure(text, "meta")

    subj_1: list[BlockLine] = [
        (line, "subject") for line in _wrap(subject, text_w, 1, subject_width)
    ]
    subj_2: list[BlockLine] = [
        (line, "subject") for line in _wrap(subject, text_w, 2, subject_width)
    ]
    time_line = _truncate(time_range, text_w, meta_width)
    room_line = _truncate(room, text_w, meta_width) if room else ""
    combined_line = _truncate(
        f"{time_range} · {room}" if room else time_range, text_w, meta_width
    )

    def fits(lines: list[BlockLine]) -> bool:
        y = BLOCK_PAD_Y
        for _, kind in lines:
            step = _line_step(kind)
            if y + step - LINE_SLACK > block_h - BLOCK_PAD_Y:
                return False
            y += step
        return True

    # Separate time/room beats a combined line; a truncated subject beats
    # combined or dropped metadata. The second subject line is only the
    # wraparound continuation, so it vanishes when the subject fits in one.
    subject_options = [subj_2, subj_1] if subj_2 != subj_1 else [subj_1]
    separate: list[BlockLine] = [(time_line, "meta"), (room_line, "meta")]
    meta_options: list[list[BlockLine]] = (
        [separate, [(combined_line, "meta")]] if room else [[(time_line, "meta")]]
    )
    for meta in meta_options:
        for subj in subject_options:
            candidate = [*subj, *meta]
            if fits(candidate):
                return candidate
    return subj_1 if fits(subj_1) else []


def _line_step(kind: LineKind) -> int:
    return SUBJECT_STEP if kind == "subject" else META_STEP


def _offset_minutes(moment: time) -> float:
    return (moment.hour - START_HOUR) * 60 + moment.minute


def format_room(raw: str) -> str:
    """Shorten a raw room cell (`bud.D D - 02 - SALA BALETOWA`) for display."""
    if " - " not in raw:
        return f"sala {_clean_code(raw)}"
    code, _, descriptor = raw.rpartition(" - ")
    code = _clean_code(code)
    words = [w for w in descriptor.split() if w not in _GENERIC_ROOM_WORDS]
    detail = " ".join(words).lower()
    if "-" in code and detail:
        return f"sala {code} · {detail}"
    return f"sala {code}"


def _clean_code(code: str) -> str:
    code = _BUILDING_RE.sub("", code)
    return re.sub(r"-\s+", "-", code).strip()


def _wrap(
    text: str, max_width: float, max_lines: int, measure: WidthMeasure
) -> list[str]:
    out: list[str] = []
    for word in text.split():
        if out and measure(out[-1] + " " + word) <= max_width:
            out[-1] += " " + word
        elif len(out) < max_lines:
            out.append(word)
        else:
            out[-1] += " " + word
    if out:
        out[-1] = _truncate(out[-1], max_width, measure)
    return out


def _truncate(text: str, max_width: float, measure: WidthMeasure) -> str:
    if measure(text) <= max_width:
        return text
    while text and measure(text + "…") > max_width:
        text = text[:-1]
    return text + "…"
