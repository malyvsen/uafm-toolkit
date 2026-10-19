"""Week-helper tests against the anonymized two-week fixture."""

from pathlib import Path

import pytest

from plan_parser import (
    Event,
    UnknownWeekError,
    available_weeks,
    events_for_week,
    parse_pdf,
)

FIXTURES = Path(__file__).parent / "fixtures"
SINGLE = FIXTURES / "plan-single-week.pdf"
TWO = FIXTURES / "plan-two-weeks.pdf"


@pytest.fixture(scope="module")
def two_weeks() -> list[Event]:
    return parse_pdf(TWO)


def test_available_weeks_lists_mondays_oldest_first(two_weeks: list[Event]):
    assert available_weeks(parse_pdf(SINGLE)) == ["2026-10-19"]
    assert available_weeks(two_weeks) == ["2026-10-19", "2026-10-26"]


def test_events_for_week_filters_and_sorts(two_weeks: list[Event]):
    events = events_for_week(two_weeks, "2026-10-26")
    assert len(events) == 10
    assert all(e.date.isocalendar()[1] == 44 for e in events)
    assert [(e.date.day, e.start.hour) for e in events] == sorted(
        (e.date.day, e.start.hour) for e in events
    )


def test_events_for_week_rejects_non_monday(two_weeks: list[Event]):
    with pytest.raises(ValueError, match="Monday"):
        events_for_week(two_weeks, "2026-10-20")


def test_events_for_week_rejects_unknown_monday(two_weeks: list[Event]):
    with pytest.raises(UnknownWeekError):
        events_for_week(two_weeks, "2026-11-02")


def test_events_for_week_rejects_malformed_date(two_weeks: list[Event]):
    with pytest.raises(ValueError):
        events_for_week(two_weeks, "19-10-2026")
