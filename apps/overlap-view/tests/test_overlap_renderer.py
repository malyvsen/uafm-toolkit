"""Renderer tests: one typical-week image out of clustered events."""

from datetime import date, time
from pathlib import Path
from unittest.mock import patch

import pytest

from overlap_view.clustering import Cluster, RoomVariant, TimeVariant, cluster_events
from overlap_view.renderer import alpha_for, render_typical
from plan_parser import parse_pdf
from plan_render import canvas as canvas_module
from plan_render.canvas import col_x
from plan_render.style import (
    BLOCK_PAD_X,
    CHOICE_CHIP_H,
    COL_W,
    GRID_TOP,
    HOUR_H,
    META_STEP,
    START_HOUR,
    SUBJECT_STEP,
    UNKNOWN_SPINE,
    WYK_ORANGE,
)
from plan_render.text import place_choice_sections

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


def test_colliding_clusters_render_as_one_combined_block():
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
    boxes: list[tuple[float, float, float, float]] = []
    captured: list[list[tuple[tuple[int, ...], list]]] = []
    block_calls: list[tuple] = []
    real_choice = canvas_module.draw_choice_block
    real_block = canvas_module.draw_block

    def recording_choice(base, draw, box, sections, alpha=1.0):
        boxes.append(box)
        captured.append(sections)
        return real_choice(base, draw, box, sections, alpha)

    def recording_block(base, draw, box, spine_color, lines, alpha=1.0):
        block_calls.append((box, spine_color, lines))
        return real_block(base, draw, box, spine_color, lines, alpha)

    with (
        patch.object(canvas_module, "draw_choice_block", side_effect=recording_choice),
        patch.object(canvas_module, "draw_block", side_effect=recording_block),
    ):
        image = render_typical(
            [left, right],
            date_from=date(2026, 10, 19),
            date_to=date(2026, 10, 30),
            weeks=5,
        )
    assert block_calls == []
    assert len(boxes) == 1
    box = boxes[0]
    assert box[0] == col_x(3) + BLOCK_PAD_X
    assert box[2] == col_x(3) + COL_W - BLOCK_PAD_X
    assert box[1] == GRID_TOP + (13 - START_HOUR) * HOUR_H
    assert box[3] == GRID_TOP + (16 - START_HOUR) * HOUR_H

    (sections,) = captured
    assert len(sections) == 2
    assert tuple(sections[0][0]) == tuple(WYK_ORANGE)
    assert tuple(sections[1][0]) == tuple(UNKNOWN_SPINE)
    first_subject = " ".join(text for text, kind in sections[0][1] if kind == "subject")
    second_subject = " ".join(
        text for text, kind in sections[1][1] if kind == "subject"
    )
    assert first_subject == "Antropologia"
    assert second_subject == "Bezpieczeństwo lokalne"
    assert any("×5" in text for text, kind in sections[0][1] if kind == "meta")
    assert any("×5" in text for text, kind in sections[1][1] if kind == "meta")

    x_chip = int(col_x(3) + BLOCK_PAD_X + 4)
    placed = place_choice_sections([lines for _, lines in sections])
    for (color, _), placed_lines in zip(sections, placed, strict=True):
        assert placed_lines
        _, first_kind, first_dy = placed_lines[0]
        step = SUBJECT_STEP if first_kind == "subject" else META_STEP
        chip_y = int(box[1]) + first_dy + (step - CHOICE_CHIP_H) // 2 + 2
        pixel = image.getpixel((x_chip, chip_y))
        assert _pixel_close(pixel, tuple(color))


def _pixel_close(actual: object, expected: tuple[int, ...], tolerance: int = 8) -> bool:
    return isinstance(actual, tuple) and _close(actual, expected, tolerance)


def _close(
    actual: tuple[int, ...], expected: tuple[int, ...], tolerance: int = 8
) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))
