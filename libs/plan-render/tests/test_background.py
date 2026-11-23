"""Background tests: seeded graphite wash is deterministic and sized."""

from datetime import date

from plan_render.background import background_for_date


def test_same_monday_yields_identical_pixels():
    first = background_for_date(date(2026, 10, 19), 1648, 1698)
    second = background_for_date(date(2026, 10, 19), 1648, 1698)
    assert first.tobytes() == second.tobytes()


def test_different_mondays_differ():
    first = background_for_date(date(2026, 10, 19), 1648, 1698)
    second = background_for_date(date(2026, 10, 26), 1648, 1698)
    assert first.tobytes() != second.tobytes()


def test_output_size_and_mode():
    image = background_for_date(date(2026, 10, 19), 800, 600)
    assert image.size == (800, 600)
    assert image.mode == "RGB"
