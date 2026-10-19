"""Typed events parsed out of study-plan PDFs."""

from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class Event:
    """One class from the study plan: when, what, where, and for whom."""

    date: date
    start: time
    end: time
    duration: str
    subject: str
    form: str
    groups: str
    room: str
    lecturer: str
    credit_form: str
    tracks: str
    notes: str
