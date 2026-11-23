"""Semester tests: the default window covers the remaining teaching period."""

from datetime import date

from overlap_view.semester import semester_remainder


def test_winter_stays_within_the_winter_teaching_period():
    assert semester_remainder(date(2026, 10, 15)) == (
        date(2026, 10, 15),
        date(2027, 1, 31),
    )
    assert semester_remainder(date(2027, 1, 10)) == (
        date(2027, 1, 10),
        date(2027, 1, 31),
    )


def test_february_points_at_the_upcoming_summer():
    assert semester_remainder(date(2027, 2, 5)) == (
        date(2027, 3, 1),
        date(2027, 6, 30),
    )


def test_summer_stays_within_the_summer_teaching_period():
    assert semester_remainder(date(2027, 4, 5)) == (
        date(2027, 4, 5),
        date(2027, 6, 30),
    )


def test_break_points_at_the_upcoming_winter():
    assert semester_remainder(date(2027, 8, 5)) == (
        date(2027, 10, 1),
        date(2028, 1, 31),
    )
