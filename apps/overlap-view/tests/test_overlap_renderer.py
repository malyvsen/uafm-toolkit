"""Renderer tests: one typical-week image out of clustered events."""

from datetime import date, time
from pathlib import Path

import pytest

from overlap_view.clustering import Cluster, RoomVariant, TimeVariant, cluster_events
from overlap_view.renderer import alpha_for, render_typical
from plan_parser import parse_pdf
from plan_render.canvas import col_x
from plan_render.style import (
    BLOCK_PAD_X,
    COL_W,
    GRID_TOP,
    HOUR_H,
    START_HOUR,
    UNKNOWN_SPINE,
    WYK_ORANGE,
)

FIXTURES = (
    Path(__file__).resolve().parents[3] / "libs" / "plan-parser" / "tests" / "fixtures"
)
TWO = FIXTURES / "plan-two-weeks.pdf"


@pytest.fixture(scope="module")
def clusters() -> list[Cluster]:
    return cluster_events(parse_pdf(TWO.read_bytes()))


def test_render_has_five_column_dimensions(clusters: list[Cluster]):
    image = render_typical(
        clusters, date_from=date(2026, 10, 19), date_to=date(2026, 10, 30), weeks=2
    )
    assert image.mode == "RGB"
    assert image.size == (1744, 1698)


def test_render_is_deterministic(clusters: list[Cluster]):
    first = render_typical(
        clusters, date_from=date(2026, 10, 19), date_to=date(2026, 10, 30), weeks=2
    )
    second = render_typical(
        clusters, date_from=date(2026, 10, 19), date_to=date(2026, 10, 30), weeks=2
    )
    assert first.tobytes() == second.tobytes()


def test_render_rejects_empty_clusters():
    with pytest.raises(ValueError):
        render_typical(
            [], date_from=date(2026, 10, 19), date_to=date(2026, 10, 30), weeks=2
        )


def test_render_rejects_non_positive_weeks(clusters: list[Cluster]):
    with pytest.raises(ValueError):
        render_typical(
            clusters, date_from=date(2026, 10, 19), date_to=date(2026, 10, 30), weeks=0
        )


def test_every_week_is_solid_and_once_is_pale():
    assert alpha_for(5, 5) == 1.0
    assert alpha_for(10, 5) == 1.0
    assert alpha_for(1, 5) == pytest.approx(0.45 + 0.55 / 5)
    assert alpha_for(2, 5) > alpha_for(1, 5)


def test_colliding_clusters_render_side_by_side():
    left = Cluster(
        weekday=3,
        subject="Antropologia",
        form="Wyk",
        start=time(13, 0),
        end=time(15, 0),
        times=(TimeVariant(time(13, 0), time(15, 0), 5),),
        rooms=(RoomVariant("sala B 203", 5),),
        count=5,
        lane=0,
        lanes=2,
    )
    right = Cluster(
        weekday=3,
        subject="Bezpieczeństwo lokalne",
        form="",
        start=time(14, 0),
        end=time(16, 0),
        times=(TimeVariant(time(14, 0), time(16, 0), 5),),
        rooms=(RoomVariant("sala B 203", 5),),
        count=5,
        lane=1,
        lanes=2,
    )
    image = render_typical(
        [left, right],
        date_from=date(2026, 10, 19),
        date_to=date(2026, 10, 30),
        weeks=5,
    )
    lane_w = COL_W / 2
    y = GRID_TOP + int((14.5 - START_HOUR) * HOUR_H)
    left_spine = image.getpixel((int(col_x(3) + BLOCK_PAD_X + 4), y))
    right_spine = image.getpixel((int(col_x(3) + lane_w + BLOCK_PAD_X + 4), y))
    assert isinstance(left_spine, tuple) and _close(left_spine, WYK_ORANGE)
    assert isinstance(right_spine, tuple) and _close(right_spine, UNKNOWN_SPINE)


def _close(
    actual: tuple[int, ...], expected: tuple[int, ...], tolerance: int = 8
) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))
