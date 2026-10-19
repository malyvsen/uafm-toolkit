"""Renderer tests: pure event list in, Pillow image out."""

from datetime import date, time, timedelta
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from calendar_grid.background import background_for_week
from calendar_grid.renderer import (
    BLOCK_PAD_X,
    COL_W,
    DAY_LABEL_GAP,
    DAY_LABEL_H,
    GRID_GAP,
    HOUR_H,
    MARGIN_TOP,
    START_HOUR,
    SUBTITLE_H,
    TITLE_GAP,
    TITLE_H,
    UNKNOWN_SPINE,
    WAR_YELLOW,
    WYK_ORANGE,
    BlockLine,
    LineKind,
    apply_grain,
    col_x,
    format_room,
    layout_block,
    render_week,
)
from plan_parser import Event, events_for_week, parse_pdf

FIXTURES = (
    Path(__file__).resolve().parents[3] / "libs" / "plan-parser" / "tests" / "fixtures"
)
SINGLE = FIXTURES / "plan-single-week.pdf"


@pytest.fixture(scope="module")
def week_19() -> list[Event]:
    return events_for_week(parse_pdf(SINGLE), "2026-10-19")


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
    assert image.size == (1648, 1698)
    output = tmp_path / "week.png"
    image.save(output)
    with Image.open(output) as reopened:
        reopened.load()
        assert reopened.size == (1648, 1698)


def test_render_is_deterministic(week_19: list[Event]):
    assert render_week(week_19).tobytes() == render_week(week_19).tobytes()


def test_weekend_columns_appear_only_with_weekend_events(week_19: list[Event]):
    plain = render_week(week_19)
    with_weekend = render_week([*week_19, saturday_event(week_19[0])])
    assert with_weekend.size == (plain.width + 2 * COL_W, plain.height)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("bud.D D 319 - PRACOWNIA AKTORSKA", "sala D 319"),
        ("bud.B B 020", "sala B 020"),
        ("bud.D D - 02 - SALA BALETOWA", "sala D -02 · baletowa"),
    ],
)
def test_format_room(raw: str, expected: str):
    assert format_room(raw) == expected


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
    bare = background_for_week(date(2026, 10, 19), *image.size).getpixel(pixel)
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


def test_grain_is_deterministic():
    bare = background_for_week(date(2026, 10, 19), 800, 600)
    seed = date(2026, 10, 19).toordinal()
    assert apply_grain(bare, seed).tobytes() == apply_grain(bare, seed).tobytes()


def test_grain_raises_variance_on_background_patch():
    bare = background_for_week(date(2026, 10, 19), 800, 600)
    grained = apply_grain(bare, date(2026, 10, 19).toordinal())
    patch = (8, 8, 40, 40)
    grained_std = sum(ImageStat.Stat(grained.crop(patch)).stddev)
    bare_std = sum(ImageStat.Stat(bare.crop(patch)).stddev)
    assert grained_std > bare_std


def _fake_measure(text: str, kind: LineKind) -> float:
    return float(len(text) * (10 if kind == "subject" else 8))


def _layout(
    subject: str, time_range: str, room: str, text_w: float, minutes: float
) -> list[BlockLine]:
    return layout_block(
        subject, time_range, room, text_w, minutes * HOUR_H / 60, _fake_measure
    )


def test_short_subject_uses_separate_meta():
    lines = _layout("Wymowa", "10:00–11:30", "sala D 319", 200, 145)
    assert [kind for _, kind in lines] == ["subject", "meta", "meta"]
    assert lines[0][0] == "Wymowa"
    assert lines[1][0] == "10:00–11:30"
    assert lines[2][0] == "sala D 319"


def test_long_subject_wraps_to_two_lines_with_separate_meta():
    lines = _layout(
        "Elementarne zadania aktorskie", "10:00–12:25", "sala D 319", 150, 145
    )
    kinds = [kind for _, kind in lines]
    assert kinds == ["subject", "subject", "meta", "meta"]
    assert lines[0][0] == "Elementarne"
    assert lines[2][0] == "10:00–12:25"
    assert lines[3][0] == "sala D 319"


def test_medium_block_keeps_separate_meta():
    # Fitting is purely visual: a 95-minute block still separates time and
    # room when the lines fit.
    lines = _layout("Wymowa", "10:00–11:35", "sala D 319", 200, 95)
    assert [kind for _, kind in lines] == ["subject", "meta", "meta"]


def test_tight_block_falls_back_to_combined_meta():
    lines = _layout(
        "Elementarne zadania aktorskie", "10:00–10:45", "sala D 319", 150, 45
    )
    assert [kind for _, kind in lines] == ["subject", "meta"]
    assert "·" in lines[1][0]


def test_tiny_block_yields_no_lines():
    assert _layout("Wymowa", "10:00–10:20", "sala D 319", 200, 20) == []


def test_subject_only_when_meta_does_not_fit():
    lines = _layout("Wymowa", "10:00–10:30", "sala D 319", 200, 30)
    assert [kind for _, kind in lines] == ["subject"]


def test_empty_room_renders_time_only():
    lines = _layout("Wymowa", "10:00–11:30", "", 200, 145)
    assert [kind for _, kind in lines] == ["subject", "meta"]
    assert lines[1][0] == "10:00–11:30"


def _grid_top() -> int:
    return (
        MARGIN_TOP
        + TITLE_H
        + TITLE_GAP
        + SUBTITLE_H
        + DAY_LABEL_H
        + DAY_LABEL_GAP
        + GRID_GAP
    )


def _block_top_bottom(event: Event) -> tuple[float, float]:
    top = _grid_top() + _minutes(event.start) * HOUR_H / 60
    bottom = _grid_top() + _minutes(event.end) * HOUR_H / 60
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
