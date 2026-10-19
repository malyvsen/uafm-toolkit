"""Parse Polish university study-plan PDFs into typed events."""

from plan_parser.events import Event
from plan_parser.parser import parse_pdf
from plan_parser.weeks import UnknownWeekError, available_weeks, events_for_week

__all__ = [
    "Event",
    "UnknownWeekError",
    "available_weeks",
    "events_for_week",
    "parse_pdf",
]
