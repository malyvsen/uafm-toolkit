"""Renderer tests: pure event list in, Pillow image out."""

from datetime import date, time
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from calendar_grid.background import background_for_week
from calendar_grid.renderer import (
    COL_W,
    UNKNOWN_SPINE,
    WAR_YELLOW,
    WYK_ORANGE,
    apply_grain,
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


def test_block_spines_follow_class_form(week_19: list[Event]):
    image = render_week(week_19)
    # 4px from the block left edge at the vertical center: Monday Warsztaty, Thursday Wykład.
    monday_spine = image.getpixel((121, 537))
    thursday_spine = image.getpixel((1021, 870))
    assert isinstance(monday_spine, tuple) and _close(monday_spine, WAR_YELLOW)
    assert isinstance(thursday_spine, tuple) and _close(thursday_spine, WYK_ORANGE)


def test_block_interiors_are_frosted_not_solid(week_19: list[Event]):
    image = render_week(week_19)
    interior = image.getpixel((262, 643))
    bare = background_for_week(date(2026, 10, 19), *image.size).getpixel((262, 643))
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
    spine = image.getpixel((121, 537))
    assert isinstance(spine, tuple) and _close(spine, UNKNOWN_SPINE)


def test_grain_is_deterministic(week_19: list[Event]):
    image = render_week(week_19)
    grained = apply_grain(image, date(2026, 10, 19).toordinal())
    regrained = apply_grain(image, date(2026, 10, 19).toordinal())
    assert grained.tobytes() == regrained.tobytes()


def test_grain_raises_variance_on_background_patch(week_19: list[Event]):
    image = render_week(week_19)
    bare = background_for_week(date(2026, 10, 19), *image.size)
    patch = (8, 8, 40, 40)
    grained_std = sum(ImageStat.Stat(image.crop(patch)).stddev)
    bare_std = sum(ImageStat.Stat(bare.crop(patch)).stddev)
    assert grained_std > bare_std


def _close(
    actual: tuple[int, ...], expected: tuple[int, ...], tolerance: int = 8
) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


def test_render_rejects_empty_week():
    with pytest.raises(ValueError):
        render_week([])
