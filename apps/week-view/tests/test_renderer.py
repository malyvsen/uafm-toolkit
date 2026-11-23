"""Renderer tests: pure event list in, Pillow image out."""

from collections import Counter
from datetime import date, time, timedelta
from pathlib import Path

import pytest
from PIL import Image

from plan_parser import Event, events_for_week, parse_pdf
from plan_render.background import background_for_date
from plan_render.canvas import col_x, legend_forms
from plan_render.style import (
    BLOCK_PAD_X,
    COL_W,
    GRID_TOP,
    GUTTER,
    HOUR_H,
    LEGEND_SPINE_W,
    MARGIN_TOP,
    START_HOUR,
    UNKNOWN_SPINE,
    WAR_YELLOW,
    WYK_ORANGE,
)
from week_view.renderer import hour_segments, render_week

FIXTURES = (
    Path(__file__).resolve().parents[3] / "libs" / "plan-parser" / "tests" / "fixtures"
)
SINGLE = FIXTURES / "plan-single-week.pdf"


@pytest.fixture(scope="module")
def week_19() -> list[Event]:
    return events_for_week(parse_pdf(SINGLE.read_bytes()), "2026-10-19")


def saturday_event(base: Event) -> Event:
    return Event(
        date=date(2026, 10, 24),
        start=time(10, 0),
        end=time(11, 30),
        duration=base.duration,
        subject="Próba sobotnia",
        form="War",
        groups=base.groups,
        room=base.room,
        lecturer=base.lecturer,
        credit_form=base.credit_form,
        tracks=base.tracks,
        notes=base.notes,
    )


def test_render_is_valid_png_with_expected_dimensions(
    tmp_path: Path, week_19: list[Event]
):
    image = render_week(week_19)
    assert image.mode == "RGB"
    assert image.size == (1744, 1698)
    output = tmp_path / "week.png"
    image.save(output)
    with Image.open(output) as reopened:
        reopened.load()
        assert reopened.size == (1744, 1698)


def test_render_is_deterministic(week_19: list[Event]):
    assert render_week(week_19).tobytes() == render_week(week_19).tobytes()


def test_weekend_columns_appear_only_with_weekend_events(week_19: list[Event]):
    plain = render_week(week_19)
    with_weekend = render_week([*week_19, saturday_event(week_19[0])])
    assert with_weekend.size == (plain.width + 2 * (COL_W + GUTTER), plain.height)


def test_render_rejects_empty_week():
    with pytest.raises(ValueError):
        render_week([])


def test_block_spines_follow_class_form(week_19: list[Event]):
    image = render_week(week_19)
    monday = min(e.date for e in week_19)
    first = min(week_19, key=lambda e: (e.date, e.start))
    last = max(week_19, key=lambda e: (e.date, e.start))
    first_spine = image.getpixel(_spine_pixel(first, monday))
    last_spine = image.getpixel(_spine_pixel(last, monday))
    assert isinstance(first_spine, tuple) and _close(first_spine, WAR_YELLOW)
    assert isinstance(last_spine, tuple) and _close(last_spine, WYK_ORANGE)


def test_block_interiors_are_frosted_not_solid(week_19: list[Event]):
    image = render_week(week_19)
    monday = min(e.date for e in week_19)
    first = min(week_19, key=lambda e: (e.date, e.start))
    pixel = _interior_pixel(first, monday)
    interior = image.getpixel(pixel)
    bare = background_for_date(date(2026, 10, 19), *image.size).getpixel(pixel)
    assert isinstance(interior, tuple) and isinstance(bare, tuple)
    assert interior != WAR_YELLOW
    assert sum(interior) > sum(bare)


def test_unknown_form_renders_light_spine(week_19: list[Event]):
    base = week_19[0]
    event = Event(
        date=base.date,
        start=base.start,
        end=base.end,
        duration=base.duration,
        subject=base.subject,
        form="Ćw",
        groups=base.groups,
        room=base.room,
        lecturer=base.lecturer,
        credit_form=base.credit_form,
        tracks=base.tracks,
        notes=base.notes,
    )
    image = render_week([event])
    monday = event.date - timedelta(days=event.date.weekday())
    spine = image.getpixel(_spine_pixel(event, monday))
    assert isinstance(spine, tuple) and _close(spine, UNKNOWN_SPINE)


def test_hour_segments_omit_covered_hours():
    monday = date(2026, 10, 19)
    days = [monday + timedelta(days=i) for i in range(5)]
    event = Event(
        date=monday,
        start=time(9, 40),
        end=time(12, 5),
        duration="",
        subject="",
        form="War",
        groups="",
        room="",
        lecturer="",
        credit_form="",
        tracks="",
        notes="",
    )
    segments = hour_segments(days, [event], GRID_TOP)
    by_hour: dict[int, list[int]] = {}
    for x, y in segments:
        hour = START_HOUR + (y - GRID_TOP) // HOUR_H
        by_hour.setdefault(hour, []).append(x)
    assert col_x(0) in by_hour[9]
    assert col_x(0) not in by_hour[10]
    assert col_x(0) not in by_hour[11]
    assert col_x(0) not in by_hour[12]
    assert col_x(0) in by_hour[13]
    assert col_x(1) in by_hour[10]


def test_legend_orders_known_forms_then_unknown():
    assert legend_forms(["Wyk", "War"]) == ["War", "Wyk"]
    assert legend_forms(["War", "Ćw", "Zaj"]) == ["War", "Zaj", "Ćw"]
    assert legend_forms([""]) == []


def test_hour_lines_break_at_gutters_and_blocks(week_19: list[Event]):
    image = render_week(week_19)
    y10 = GRID_TOP + (10 - START_HOUR) * HOUR_H
    free_xs = list(range(col_x(1) + 20, col_x(1) + COL_W - 20, 10))
    gutter_xs = list(range(col_x(0) + COL_W + 6, col_x(0) + COL_W + GUTTER - 6, 2))
    free_avg = _avg_pixel_sum(image, free_xs, y10)
    free_off = _avg_pixel_sum(image, free_xs, y10 + 10)
    gutter_avg = _avg_pixel_sum(image, gutter_xs, y10)
    gutter_off = _avg_pixel_sum(image, gutter_xs, y10 + 10)
    assert free_avg > free_off + 15
    assert free_avg > gutter_avg + 10
    assert abs(gutter_avg - gutter_off) < 15
    covered_edge = _avg_pixel_sum(
        image, [col_x(0) + 1, col_x(0) + 2, col_x(0) + 3], y10
    )
    free_edge = _avg_pixel_sum(image, [col_x(1) + 1, col_x(1) + 2, col_x(1) + 3], y10)
    assert abs(covered_edge - gutter_avg) < 25
    assert free_edge > covered_edge + 20


def test_legend_bars_share_one_x_and_stack(week_19: list[Event]):
    image = render_week(week_19)
    war_left, war_right, war_top, _ = _legend_bar_bounds(image, WAR_YELLOW, GRID_TOP)
    wyk_left, wyk_right, wyk_top, _ = _legend_bar_bounds(image, WYK_ORANGE, GRID_TOP)
    assert war_left == wyk_left
    assert war_right - war_left == LEGEND_SPINE_W
    assert wyk_right - wyk_left == LEGEND_SPINE_W
    assert war_top < wyk_top


def test_legend_is_bare_not_frosted(week_19: list[Event]):
    image = render_week(week_19)
    bar_left, _, bar_top, bar_bottom = _legend_bar_bounds(image, WAR_YELLOW, GRID_TOP)
    # Mid-bar y keeps clear of text; gap xs sit between the spine and the label.
    y = (bar_top + bar_bottom) // 2
    gap_xs = list(
        range(bar_left + LEGEND_SPINE_W + 2, bar_left + LEGEND_SPINE_W + 10, 2)
    )
    rendered = _avg_pixel_sum(image, gap_xs, y)
    bare = background_for_date(date(2026, 10, 19), *image.size)
    expected = _avg_pixel_sum(bare, gap_xs, y)
    assert abs(rendered - expected) < 15


def test_legend_unknown_form_fallback(week_19: list[Event]):
    base = week_19[0]
    event = Event(
        date=base.date,
        start=base.start,
        end=base.end,
        duration=base.duration,
        subject=base.subject,
        form="Ćw",
        groups=base.groups,
        room=base.room,
        lecturer=base.lecturer,
        credit_form=base.credit_form,
        tracks=base.tracks,
        notes=base.notes,
    )
    image = render_week([event])
    left, right, _, _ = _legend_bar_bounds(image, UNKNOWN_SPINE, GRID_TOP)
    assert right - left == LEGEND_SPINE_W


def _block_top_bottom(event: Event) -> tuple[float, float]:
    top = GRID_TOP + _minutes(event.start) * HOUR_H / 60
    bottom = GRID_TOP + _minutes(event.end) * HOUR_H / 60
    return top, bottom


def _minutes(moment: time) -> float:
    return (moment.hour - START_HOUR) * 60 + moment.minute


def _block_left(event: Event, monday: date) -> int:
    col = (event.date - monday).days
    return col_x(col) + BLOCK_PAD_X


def _spine_pixel(event: Event, monday: date) -> tuple[int, int]:
    # 4px from the block left edge at the block vertical center.
    top, bottom = _block_top_bottom(event)
    return int(_block_left(event, monday) + 4), int((top + bottom) / 2)


def _interior_pixel(event: Event, monday: date) -> tuple[int, int]:
    # Block horizontal center near the bottom edge, clear of text.
    _, bottom = _block_top_bottom(event)
    return (
        int(_block_left(event, monday) + (COL_W - 2 * BLOCK_PAD_X) // 2),
        int(bottom - 15),
    )


def _close(
    actual: tuple[int, ...], expected: tuple[int, ...], tolerance: int = 8
) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


def _avg_pixel_sum(image: Image.Image, xs: list[int], y: int) -> float:
    total = 0
    for x in xs:
        pixel = image.getpixel((x, y))
        assert isinstance(pixel, tuple)
        total += sum(pixel[:3])
    return total / len(xs)


def _legend_bar_bounds(
    image: Image.Image, color: tuple[int, ...], grid_top: int
) -> tuple[int, int, int, int]:
    matches: list[tuple[int, int]] = []
    for y in range(MARGIN_TOP, grid_top):
        for x in range(image.width - 500, image.width - 10):
            pixel = image.getpixel((x, y))
            assert isinstance(pixel, tuple)
            if _close(pixel, color):
                matches.append((x, y))
    assert matches, "no legend bar found"
    counts = Counter(x for x, _ in matches)
    dense = {x for x, count in counts.items() if count >= 15}
    assert dense, "no dense legend bar found"
    ys = [y for x, y in matches if x in dense]
    return min(dense), max(dense), min(ys), max(ys)
