"""Turn a week's events into a Pillow image in the graphite-frost style."""

from datetime import date, timedelta

from PIL import Image, ImageDraw

from plan_parser import Event
from plan_render import canvas, style
from plan_render.text import block_measure, format_room, layout_block

TITLE = "Plan zajęć"


def render_week(events: list[Event]) -> Image.Image:
    """Render events from one Monday-to-Sunday week as a PNG-ready image."""
    if not events:
        raise ValueError("Cannot render a week with no events")
    first = min(e.date for e in events)
    monday = first - timedelta(days=first.weekday())
    weekend = any(e.date.weekday() >= 5 for e in events)
    days = [monday + timedelta(days=i) for i in range(7 if weekend else 5)]

    width, height = canvas.image_size(len(days))
    image = canvas.make_base(monday, width, height)
    overlay = canvas.make_overlay(width, height)
    draw = ImageDraw.Draw(overlay)
    canvas.draw_header(
        draw,
        width,
        TITLE,
        canvas.format_range(monday, days[-1]),
        [event.form for event in events],
    )
    canvas.draw_axis(draw, canvas.col_x(0), style.GRID_TOP)
    canvas.draw_hour_lines(draw, hour_segments(days, events, style.GRID_TOP))
    canvas.draw_day_labels(
        draw,
        [
            f"{style.DAY_NAMES[day.weekday()]}, {day.day}.{day.month:02d}"
            for day in days
        ],
        style.GRID_TOP,
    )
    for event in sorted(events, key=lambda e: (e.date, e.start)):
        _draw_event(image, overlay, event, days, style.GRID_TOP)
    return canvas.finish(image, overlay, monday)


def hour_segments(
    days: list[date], events: list[Event], grid_top: int
) -> list[tuple[int, int]]:
    """Left x and y of each hour-row segment, skipping rows covered by events."""
    blocked: dict[int, list[tuple[float, float]]] = {}
    for event in events:
        col = (event.date - days[0]).days
        if 0 <= col < len(days):
            blocked.setdefault(col, []).append(
                canvas.span_y(event.start, event.end, grid_top)
            )
    return canvas.hour_segments(
        [canvas.col_x(i) for i in range(len(days))], blocked, grid_top
    )


def _draw_event(
    image: Image.Image,
    overlay: Image.Image,
    event: Event,
    days: list[date],
    grid_top: int,
) -> None:
    col = (event.date - days[0]).days
    top, bottom = canvas.span_y(event.start, event.end, grid_top)
    x = canvas.col_x(col) + style.BLOCK_PAD_X
    box = (x, top, x + style.COL_W - 2 * style.BLOCK_PAD_X, bottom)

    text_w = style.text_width(style.COL_W)
    block_h = bottom - top
    time_range = (
        f"{event.start.hour}:{event.start.minute:02d}"
        f"–{event.end.hour}:{event.end.minute:02d}"
    )
    lines = layout_block(
        event.subject,
        time_range,
        format_room(event.room),
        text_w,
        block_h,
        block_measure(ImageDraw.Draw(overlay)),
    )
    canvas.draw_block(image, overlay, box, style.spine_for(event.form), lines)
