"""Shared timetable drawing: header, hour grid, and frosted event blocks."""

from collections.abc import Iterable
from datetime import date, time

from PIL import Image, ImageDraw

from plan_render import style
from plan_render.effects import apply_grain, frost
from plan_render.fonts import font
from plan_render.text import BlockLine, LineKind, place_lines

_INK: dict[LineKind, tuple[int, int, int]] = {
    "subject": style.OFF_WHITE,
    "meta": style.SOFT_GREY,
    "room": style.ROOM_GREY,
}


def span_y(start: time, end: time, grid_top: int) -> tuple[float, float]:
    """Pixel top and bottom of a time span hung below `grid_top`."""

    def y(moment: time) -> float:
        minutes = (moment.hour - style.START_HOUR) * 60 + moment.minute
        return grid_top + minutes * style.HOUR_H / 60

    return y(start), y(end)


def col_x(index: int) -> int:
    """Left edge of day column `index`."""
    return style.MARGIN_X + style.AXIS_W + index * (style.COL_W + style.GUTTER)


def image_size(cols: int) -> tuple[int, int]:
    """Full image size for a `cols`-column timetable."""
    return (
        col_x(cols - 1) + style.COL_W + style.MARGIN_X,
        style.GRID_TOP
        + (style.END_HOUR - style.START_HOUR) * style.HOUR_H
        + style.MARGIN_BOTTOM,
    )


def legend_forms(forms: Iterable[str]) -> list[str]:
    """Form codes in legend order: known forms first, then unknown alphabetically."""
    known = [form for form in style.FORM_STYLES if form in forms]
    # Unknown non-empty forms keep their code as the label; an empty form has no label to show.
    unknown = sorted({form for form in forms if form and form not in style.FORM_STYLES})
    return [*known, *unknown]


def format_range(start: date, end: date) -> str:
    """Format a date span the Polish way (`19–25 października 2026`)."""
    if start.month == end.month:
        return f"{start.day}–{end.day} {style.MONTHS[end.month - 1]} {end.year}"
    if start.year == end.year:
        return (
            f"{start.day} {style.MONTHS[start.month - 1]} – "
            f"{end.day} {style.MONTHS[end.month - 1]} {end.year}"
        )
    return (
        f"{start.day} {style.MONTHS[start.month - 1]} {start.year} – "
        f"{end.day} {style.MONTHS[end.month - 1]} {end.year}"
    )


def draw_header(
    draw: ImageDraw.ImageDraw,
    width: int,
    title: str,
    subtitle: str,
    forms: Iterable[str],
) -> None:
    """Draw the title, subtitle, and form legend at the top of the canvas."""
    title_font = font("bold", style.TITLE_SIZE)
    subtitle_font = font("regular", style.SUBTITLE_SIZE)
    draw.text(
        (style.MARGIN_X, style.MARGIN_TOP), title, font=title_font, fill=style.OFF_WHITE
    )
    subtitle_top = style.MARGIN_TOP + style.TITLE_H + style.TITLE_GAP
    draw.text(
        (style.MARGIN_X, subtitle_top),
        subtitle,
        font=subtitle_font,
        fill=style.SOFT_GREY,
    )
    bottom = draw.textbbox(
        (style.MARGIN_X, subtitle_top), subtitle, font=subtitle_font
    )[3]
    _draw_legend(draw, width, bottom, forms)


def draw_axis(draw: ImageDraw.ImageDraw, left: int, grid_top: int) -> None:
    """Draw the `H:00` hour labels left of the first column."""
    axis_font = font("regular", style.AXIS_SIZE)
    for hour in range(style.START_HOUR, style.END_HOUR + 1):
        y = grid_top + (hour - style.START_HOUR) * style.HOUR_H
        draw.text(
            (left - 12, y),
            f"{hour}:00",
            font=axis_font,
            fill=style.AXIS_LABEL,
            anchor="rm",
        )


def draw_hour_lines(draw: ImageDraw.ImageDraw, segments: list[tuple[int, int]]) -> None:
    """Draw hour-row segments, skipping gutters and block-covered rows."""
    for x, y in segments:
        draw.line([(x, y), (x + style.COL_W, y)], fill=style.HOUR_LINE, width=2)


def draw_day_labels(
    draw: ImageDraw.ImageDraw, labels: list[str], grid_top: int
) -> None:
    """Draw one label per day column above the grid."""
    day_font = font("regular", style.DAY_SIZE)
    for i, label in enumerate(labels):
        draw.text(
            (col_x(i) + 4, grid_top - style.DAY_LABEL_H),
            label,
            font=day_font,
            fill=style.OFF_WHITE,
            anchor="lm",
        )


def hour_segments(
    spans: Iterable[tuple[int, float, float]], cols: int, grid_top: int
) -> list[tuple[int, int]]:
    """Left x and y of each hour-row segment, skipping blocked rows.

    `spans` holds one (column, top, bottom) pixel span per event block.
    """
    blocked: dict[int, list[tuple[float, float]]] = {}
    for col, top, bottom in spans:
        blocked.setdefault(col, []).append((top, bottom))
    segments: list[tuple[int, int]] = []
    for hour in range(style.START_HOUR, style.END_HOUR + 1):
        y = grid_top + (hour - style.START_HOUR) * style.HOUR_H
        for i in range(cols):
            covered = any(
                top - style.HOUR_CLEARANCE <= y <= bottom + style.HOUR_CLEARANCE
                for top, bottom in blocked.get(i, [])
            )
            if not covered:
                segments.append((col_x(i), y))
    return segments


def draw_block(
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    spine_color: tuple[int, ...],
    lines: list[BlockLine],
    alpha: float = 1.0,
) -> None:
    """Render one frosted block, keeping borders, spine, and text opaque.

    The frost melts into `base` with strength `alpha`; borders, spine, and
    text go onto the overlay through `draw` fully opaque so rare clusters
    stay legible. Room lines render dimmer than time lines, with a gap
    separating the two groups.
    """
    left, top, right, bottom = (int(v) for v in box)
    if right - left <= 0 or bottom - top <= 0:
        return
    frost(base, (left, top, right, bottom), alpha)
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=style.EVENT_RADIUS,
        outline=style.EVENT_BORDER,
        width=1,
    )
    draw.rectangle([left, top, left + style.SPINE_W, bottom], fill=spine_color)

    text_x = left + style.SPINE_W + style.TEXT_GAP
    subject_font = font("bold", style.SUBJECT_SIZE)
    meta_font = font("italic", style.META_SIZE)
    for text, kind, dy in place_lines(lines):
        draw.text(
            (text_x, top + dy),
            text,
            font=subject_font if kind == "subject" else meta_font,
            fill=_INK[kind],
        )


def finish(base: Image.Image, overlay: Image.Image, seed: date) -> Image.Image:
    """Grain the background, then composite the crisp overlay over it."""
    grained = apply_grain(base, seed.toordinal())
    return Image.alpha_composite(grained.convert("RGBA"), overlay).convert("RGB")


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    width: int,
    subtitle_bottom: float,
    forms: Iterable[str],
) -> None:
    ordered = legend_forms(forms)
    if not ordered:
        return
    label_font = font("regular", style.LEGEND_SIZE)
    styled = [
        style.FORM_STYLES.get(form, (form, style.UNKNOWN_SPINE)) for form in ordered
    ]
    longest = max(draw.textlength(label, font=label_font) for label, _ in styled)
    block_x = width - style.MARGIN_X - style.LEGEND_SPINE_W - style.LEGEND_GAP - longest
    total_h = len(styled) * (style.LEGEND_BAR_H + style.LEGEND_GAP) - style.LEGEND_GAP
    y = subtitle_bottom - total_h
    for label, color in styled:
        draw.rectangle(
            [block_x, y, block_x + style.LEGEND_SPINE_W, y + style.LEGEND_BAR_H],
            fill=color,
        )
        draw.text(
            (
                block_x + style.LEGEND_SPINE_W + style.LEGEND_GAP,
                y + style.LEGEND_BAR_H / 2,
            ),
            label,
            font=label_font,
            fill=style.OFF_WHITE,
            anchor="lm",
        )
        y += style.LEGEND_BAR_H + style.LEGEND_GAP
