"""Render overlapping clusters as one typical Monday-to-Friday week."""

from datetime import date, time

from PIL import Image, ImageDraw

from overlap_view.clustering import Cluster
from plan_render import canvas, style
from plan_render.text import block_measure, layout_cluster

TITLE = "Typowy tydzień"
# The palest a once-only cluster gets; every-week clusters stay fully solid.
MIN_ALPHA = 0.45


def render_typical(
    clusters: list[Cluster], *, date_from: date, date_to: date, weeks: int
) -> Image.Image:
    """Render clusters as a PNG-ready typical-week image."""
    if not clusters:
        raise ValueError("Cannot render a typical week with no clusters")
    if weeks < 1:
        raise ValueError(f"Cannot render a typical week spanning {weeks} weeks")

    width, height = canvas.image_size(5)
    image = canvas.make_base(date_from, width, height)
    overlay = canvas.make_overlay(width, height)
    draw = ImageDraw.Draw(overlay)
    canvas.draw_header(
        draw,
        width,
        TITLE,
        f"{canvas.format_range(date_from, date_to)} · {weeks} {_weeks_label(weeks)}",
        [cluster.form for cluster in clusters],
    )
    canvas.draw_axis(draw, canvas.col_x(0), style.GRID_TOP)
    canvas.draw_hour_lines(draw, _hour_segments(clusters, style.GRID_TOP))
    canvas.draw_day_labels(draw, style.DAY_NAMES[:5], style.GRID_TOP)
    for cluster in sorted(
        clusters, key=lambda c: (c.weekday, c.start, c.end, c.subject)
    ):
        _draw_cluster(draw, image, overlay, cluster, weeks, style.GRID_TOP)
    return canvas.finish(image, overlay, date_from)


def alpha_for(total: int, weeks: int) -> float:
    """Block solidity from weekly frequency: every-week is solid, once is pale."""
    return min(1.0, MIN_ALPHA + (1.0 - MIN_ALPHA) * total / weeks)


def _weeks_label(weeks: int) -> str:
    if weeks == 1:
        return "tydzień"
    if weeks % 10 in (2, 3, 4) and weeks % 100 not in (12, 13, 14):
        return "tygodnie"
    return "tygodni"


def _hour_segments(clusters: list[Cluster], grid_top: int) -> list[tuple[int, int]]:
    blocked: dict[int, list[tuple[float, float]]] = {}
    for cluster in clusters:
        blocked.setdefault(cluster.weekday, []).append(
            canvas.span_y(cluster.start, cluster.end, grid_top)
        )
    return canvas.hour_segments([canvas.col_x(i) for i in range(5)], blocked, grid_top)


def _draw_cluster(
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    overlay: Image.Image,
    cluster: Cluster,
    weeks: int,
    grid_top: int,
) -> None:
    top, bottom = canvas.span_y(cluster.start, cluster.end, grid_top)
    lane_w = style.COL_W / cluster.lanes
    x = canvas.col_x(cluster.weekday) + cluster.lane * lane_w
    box = (x + style.BLOCK_PAD_X, top, x + lane_w - style.BLOCK_PAD_X, bottom)

    text_w = style.text_width(lane_w)
    block_h = bottom - top
    lines = layout_cluster(
        cluster.subject,
        [
            _time_label(variant.start, variant.end, variant.count)
            for variant in cluster.times
        ],
        [f"{variant.room} ×{variant.count}" for variant in cluster.rooms],
        text_w,
        block_h,
        block_measure(draw),
    )
    canvas.draw_block(
        image,
        overlay,
        box,
        style.spine_for(cluster.form),
        lines,
        alpha_for(cluster.count, weeks),
    )


def _time_label(start: time, end: time, count: int) -> str:
    return f"{start.hour}:{start.minute:02d}–{end.hour}:{end.minute:02d} ×{count}"
