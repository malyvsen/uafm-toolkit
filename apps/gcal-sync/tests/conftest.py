"""Shared builders for gcal-sync tests."""

from collections.abc import Callable
from datetime import date, time

import pytest

from plan_parser import Event


@pytest.fixture
def make_event() -> Callable[..., Event]:
    """One class with sane defaults, overridable per test."""

    def build(**overrides) -> Event:
        fields: dict = {
            "date": date(2026, 10, 19),
            "start": time(8, 0),
            "end": time(9, 30),
            "duration": "2",
            "subject": "Algebra",
            "form": "Wykład",
            "groups": "A",
            "room": "s. 101",
            "lecturer": "dr Nowak",
            "credit_form": "Egzamin",
            "tracks": "Ogólna",
            "notes": "",
        }
        fields.update(overrides)
        return Event(**fields)

    return build
