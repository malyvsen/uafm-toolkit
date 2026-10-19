"""Renderer tests: pure event list in, Pillow image out."""

from datetime import date, time
from pathlib import Path

import pytest
from PIL import Image

from calendar_grid.renderer import (
    COL_W,
    INK,
    WAR_YELLOW,
    WYK_ORANGE,
    format_room,
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


def test_block_colors_follow_class_form(week_19: list[Event]):
    image = render_week(week_19)
    # Block interiors near the bottom edge, clear of text: Monday Warsztaty, Thursday Wykład.
    assert image.getpixel((262, 643)) == WAR_YELLOW
    assert image.getpixel((1162, 976)) == WYK_ORANGE


def test_unknown_form_renders_dark(week_19: list[Event]):
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
    assert image.getpixel((262, 643)) == INK


def test_render_rejects_empty_week():
    with pytest.raises(ValueError):
        render_week([])
