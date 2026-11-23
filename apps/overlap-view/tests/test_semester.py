"""Semester tests: the default window covers the remaining teaching period."""

from datetime import date

from overlap_view.semester import (
    SemesterIdentity,
    semester_identity,
    semester_remainder,
)


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


def test_autumn_months_are_winter_of_the_same_year():
    assert semester_identity(date(2026, 10, 19)) == SemesterIdentity(
        kind="zimowy", start_year=2026
    )
    assert semester_identity(date(2026, 11, 5)) == SemesterIdentity(
        kind="zimowy", start_year=2026
    )
    assert semester_identity(date(2026, 12, 31)) == SemesterIdentity(
        kind="zimowy", start_year=2026
    )


def test_january_is_winter_of_the_previous_year():
    assert semester_identity(date(2027, 1, 10)) == SemesterIdentity(
        kind="zimowy", start_year=2026
    )


def test_spring_months_are_summer_of_the_previous_year():
    for month in (2, 3, 4, 5, 6):
        assert semester_identity(date(2027, month, 15)) == SemesterIdentity(
            kind="letni", start_year=2026
        )


def test_summer_break_is_winter_of_the_same_year():
    for month in (7, 8, 9):
        assert semester_identity(date(2027, month, 15)) == SemesterIdentity(
            kind="zimowy", start_year=2027
        )


def test_semester_identity_is_stable_across_the_year_boundary():
    assert semester_identity(date(2026, 10, 19)).start_year == 2026
    assert semester_identity(date(2027, 1, 10)).start_year == 2026
    assert semester_identity(date(2027, 3, 15)).start_year == 2026
    assert semester_identity(date(2027, 8, 15)) == SemesterIdentity(
        kind="zimowy", start_year=2027
    )
