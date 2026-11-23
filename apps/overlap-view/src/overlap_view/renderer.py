"""Render overlapping clusters as one typical Monday-to-Friday week."""

from datetime import date, time

from PIL import Image, ImageDraw

from overlap_view.clustering import Cluster, overlap_components
from plan_render import canvas, style
from plan_render.background import background_for_date
from plan_render.text import (
    BlockMeasure,
    block_measure,
    layout_choice_block,
    layout_cluster,
)

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
    base = background_for_date(date_from, width, height)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    measure = block_measure(draw)
    canvas.draw_header(
        draw,
        width,
        TITLE,
        f"{canvas.format_range(date_from, date_to)} · {weeks} {_weeks_label(weeks)}",
        [cluster.form for cluster in clusters],
    )
    canvas.draw_axis(draw, canvas.col_x(0), style.GRID_TOP)
    components = overlap_components(clusters)
    canvas.draw_hour_lines(draw, _hour_segments(components, style.GRID_TOP))
    canvas.draw_day_labels(draw, style.DAY_NAMES[:5], style.GRID_TOP)
    for component in sorted(
        components,
        key=lambda comp: (
            comp[0].weekday,
            min(c.start for c in comp),
            max(c.end for c in comp),
        ),
    ):
        _draw_component(draw, base, component, weeks, style.GRID_TOP, measure)
    return canvas.finish(base, overlay, date_from)


def alpha_for(total: int, weeks: int) -> float:
    """Block solidity from weekly frequency: every-week is solid, once is pale."""
    return min(1.0, MIN_ALPHA + (1.0 - MIN_ALPHA) * total / weeks)


def _weeks_label(weeks: int) -> str:
    if weeks == 1:
        return "tydzień"
    if weeks % 10 in (2, 3, 4) and weeks % 100 not in (12, 13, 14):
        return "tygodnie"
    return "tygodni"


def _hour_segments(
    components: list[list[Cluster]], grid_top: int
) -> list[tuple[int, int]]:
    spans = [
        (
            component[0].weekday,
            *canvas.span_y(
                min(c.start for c in component),
                max(c.end for c in component),
                grid_top,
            ),
        )
        for component in components
    ]
    return canvas.hour_segments(spans, 5, grid_top)


def _draw_component(
    draw: ImageDraw.ImageDraw,
    base: Image.Image,
    component: list[Cluster],
    weeks: int,
    grid_top: int,
    measure: BlockMeasure,
) -> None:
    if len(component) == 1:
        _draw_cluster(draw, base, component[0], weeks, grid_top, measure)
        return
    start = min(c.start for c in component)
    end = max(c.end for c in component)
    top, bottom = canvas.span_y(start, end, grid_top)
    x = canvas.col_x(component[0].weekday)
    box = (x + style.BLOCK_PAD_X, top, x + style.COL_W - style.BLOCK_PAD_X, bottom)

    text_w = style.text_width(style.COL_W)
    block_h = bottom - top
    alternatives = [
        (
            cluster.subject,
            [
                _time_label(variant.start, variant.end, variant.count)
                for variant in cluster.times
            ],
        )
        for cluster in component
    ]
    laid_out = layout_choice_block(alternatives, text_w, block_h, measure)
    sections = (
        []
        if not laid_out
        else [
            (style.spine_for(cluster.form), section)
            for cluster, section in zip(component, laid_out, strict=True)
        ]
    )
    canvas.draw_choice_block(
        base,
        draw,
        box,
        sections,
        max(alpha_for(cluster.count, weeks) for cluster in component),
    )


def _draw_cluster(
    draw: ImageDraw.ImageDraw,
    base: Image.Image,
    cluster: Cluster,
    weeks: int,
    grid_top: int,
    measure: BlockMeasure,
) -> None:
    top, bottom = canvas.span_y(cluster.start, cluster.end, grid_top)
    x = canvas.col_x(cluster.weekday)
    box = (x + style.BLOCK_PAD_X, top, x + style.COL_W - style.BLOCK_PAD_X, bottom)

    text_w = style.text_width(style.COL_W)
    block_h = bottom - top
    lines = layout_cluster(
        cluster.subject,
        [
            _time_label(variant.start, variant.end, variant.count)
            for variant in cluster.times
        ],
        [],
        text_w,
        block_h,
        measure,
    )
    canvas.draw_block(
        base,
        draw,
        box,
        style.spine_for(cluster.form),
        lines,
        alpha_for(cluster.count, weeks),
    )


def _time_label(start: time, end: time, count: int) -> str:
    return f"{start.hour}:{start.minute:02d}–{end.hour}:{end.minute:02d} ×{count}"
