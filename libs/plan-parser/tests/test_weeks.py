"""Week-helper tests against the anonymized two-week fixture."""

from pathlib import Path

import pytest

from plan_parser import UnknownWeekError, available_weeks, events_for_week, parse_pdf

EVENTS = parse_pdf(Path(__file__).parent / "fixtures" / "plan-two-weeks.pdf")


def test_available_weeks_lists_mondays_oldest_first():
    assert available_weeks(
        parse_pdf(Path(__file__).parent / "fixtures" / "plan-single-week.pdf")
    ) == ["2026-10-19"]
    assert available_weeks(EVENTS) == ["2026-10-19", "2026-10-26"]


def test_events_for_week_filters_and_sorts():
    events = events_for_week(EVENTS, "2026-10-26")
    assert len(events) == 10
    assert all(e.date.isocalendar()[1] == 44 for e in events)
    assert [(e.date.day, e.start.hour) for e in events] == sorted(
        (e.date.day, e.start.hour) for e in events
    )


def test_events_for_week_rejects_non_monday():
    with pytest.raises(ValueError, match="Monday"):
        events_for_week(EVENTS, "2026-10-20")


def test_events_for_week_rejects_unknown_monday():
    with pytest.raises(UnknownWeekError):
        events_for_week(EVENTS, "2026-11-02")


def test_events_for_week_rejects_malformed_date():
    with pytest.raises(ValueError):
        events_for_week(EVENTS, "19-10-2026")
