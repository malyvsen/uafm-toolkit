"""Map study-plan events to Google Calendar bodies and diff sync plans."""

import base64
import hashlib
from dataclasses import dataclass
from typing import NotRequired, TypedDict

from plan_parser import Event

TIMEZONE = "Europe/Warsaw"
MARKER_KEY = "uafmToolkit"
MARKER_VALUE = "1"


class DateTime(TypedDict):
    """RFC 3339 wall time plus the IANA zone Google should interpret it in."""

    dateTime: str
    timeZone: str


class ExtendedProperties(TypedDict):
    """Private marker so sync only touches events it created."""

    private: dict[str, str]


class GoogleEvent(TypedDict):
    """Minimal Calendar API body managed by the sync."""

    id: str
    summary: str
    location: NotRequired[str]
    description: NotRequired[str]
    start: DateTime
    end: DateTime
    extendedProperties: ExtendedProperties


@dataclass(frozen=True)
class SyncPlan:
    """Pure diff result: what to insert, update, and delete."""

    insert: tuple[GoogleEvent, ...]
    update: tuple[GoogleEvent, ...]
    delete_ids: tuple[str, ...]


def events_to_bodies(events: list[Event]) -> dict[str, GoogleEvent]:
    """Index Google bodies by deterministic ID."""
    bodies: dict[str, GoogleEvent] = {}
    for event in events:
        body = to_google_event(event)
        bodies[body["id"]] = body
    return bodies


def diff_bodies(
    desired: dict[str, GoogleEvent], existing: dict[str, GoogleEvent]
) -> SyncPlan:
    """Diff desired against existing bodies into insert/update/delete."""
    insert = tuple(body for key, body in desired.items() if key not in existing)
    update = tuple(
        body
        for key, body in desired.items()
        if key in existing and not bodies_equal(body, existing[key])
    )
    delete_ids = tuple(key for key in existing if key not in desired)
    return SyncPlan(insert=insert, update=update, delete_ids=delete_ids)


def bodies_equal(first: GoogleEvent, second: GoogleEvent) -> bool:
    """Compare only the fields the sync manages, tolerating missing empties."""
    return (
        _normalized(first["summary"]) == _normalized(second.get("summary", ""))
        and _normalized(first.get("location", ""))
        == _normalized(second.get("location", ""))
        and _normalized(first.get("description", ""))
        == _normalized(second.get("description", ""))
        and first["start"]["dateTime"] == second["start"]["dateTime"]
        and first["end"]["dateTime"] == second["end"]["dateTime"]
    )


def to_google_event(event: Event) -> GoogleEvent:
    """Convert one study-plan event into a Calendar API body."""
    return GoogleEvent(
        id=event_id(event),
        summary=_summary(event),
        location=event.room,
        description=_description(event),
        start=_date_time(event.date.isoformat(), event.start.strftime("%H:%M:%S")),
        end=_date_time(event.date.isoformat(), event.end.strftime("%H:%M:%S")),
        extendedProperties={"private": {MARKER_KEY: MARKER_VALUE}},
    )


def event_id(event: Event) -> str:
    """Deterministic base32hex ID: stable across re-syncs, distinct per class slot.

    Only identity fields feed the hash (date, times, subject, form, groups),
    so room or lecturer corrections become updates rather than delete+insert.
    """
    key = f"{event.date.isoformat()}|{event.start.isoformat()}|{event.end.isoformat()}|{event.subject}|{event.form}|{event.groups}"
    digest = hashlib.sha256(key.encode()).digest()
    suffix = base64.b32hexencode(digest).decode().lower().rstrip("=")[:26]
    return f"uafm{suffix}"


def _summary(event: Event) -> str:
    """Human title: subject plus class form when known."""
    return f"{event.subject} ({event.form})" if event.form else event.subject


def _description(event: Event) -> str:
    """Human details: only the fields the plan actually filled in."""
    lines = [
        f"Prowadzący: {event.lecturer}" if event.lecturer else "",
        f"Grupy: {event.groups}" if event.groups else "",
        f"Forma: {event.form}" if event.form else "",
        f"Zaliczenie: {event.credit_form}" if event.credit_form else "",
        f"Ścieżka: {event.tracks}" if event.tracks else "",
        event.notes,
    ]
    return "\n".join(line for line in lines if line)


def _date_time(day: str, clock: str) -> DateTime:
    """Wall time plus zone; Google resolves the UTC offset (incl. DST)."""
    return DateTime(dateTime=f"{day}T{clock}", timeZone=TIMEZONE)


def _normalized(text: str) -> str:
    """Treat missing and blank API fields as equal."""
    return " ".join(text.split())
