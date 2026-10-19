"""Select single Monday-to-Sunday weeks out of parsed events."""

from datetime import date, timedelta

from plan_parser.events import Event


class UnknownWeekError(ValueError):
    """A Monday-to-Sunday week holding no events in the parsed file."""


def available_weeks(events: list[Event]) -> list[str]:
    """Return ISO dates of the Mondays starting weeks that hold events."""
    mondays = {event.date - timedelta(days=event.date.weekday()) for event in events}
    return sorted(monday.isoformat() for monday in mondays)


def events_for_week(events: list[Event], week: str) -> list[Event]:
    """Return events from the Monday-to-Sunday week starting `week` (ISO date)."""
    monday = date.fromisoformat(week)
    if monday.weekday() != 0:
        raise ValueError(f"Week must start on a Monday, got {week}")
    sunday = monday + timedelta(days=6)
    selected = [event for event in events if monday <= event.date <= sunday]
    if not selected:
        raise UnknownWeekError(f"No events in the week starting {week}")
    return sorted(selected, key=lambda event: (event.date, event.start))
