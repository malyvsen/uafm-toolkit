"""Turn study-plan PDF tables into typed events."""

import re
from datetime import date, time
from pathlib import Path

import pdfplumber

from plan_parser.events import Event

_DATE_PREFIX = "Data Zajęć:"
_SUBJECT_COLUMN = 4
_DATE_RE = re.compile(r"^Data Zajęć:\s*(\d{4})\.(\d{2})\.(\d{2})")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_HYPHEN_BREAK_RE = re.compile(r"(?<=\S)-\n\s*")
_COLUMN_COUNT = 12


def parse_pdf(path: Path | str) -> list[Event]:
    """Parse every class row in the PDF into events, in file order."""
    events: list[Event] = []
    current: date | None = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if _is_header(row):
                        continue
                    if _is_date_row(row):
                        current = _parse_date_row(row)
                    elif _is_class_row(row):
                        if current is None:
                            raise ValueError(
                                "Class row found before any Data Zajęć row"
                            )
                        events.append(_parse_event(row, current))
                    else:
                        raise ValueError(f"Unrecognized table row: {row!r}")
    return events


def _is_header(row: list[str | None]) -> bool:
    return len(row) > _SUBJECT_COLUMN and "Zajęcia" in (row[_SUBJECT_COLUMN] or "")


def _is_date_row(row: list[str | None]) -> bool:
    return (row[0] or "").startswith(_DATE_PREFIX)


def _parse_date_row(row: list[str | None]) -> date:
    match = _DATE_RE.match(row[0] or "")
    if match is None:
        raise ValueError(f"Malformed Data Zajęć row: {row[0]!r}")
    year, month, day = (int(part) for part in match.groups())
    return date(year, month, day)


def _is_class_row(row: list[str | None]) -> bool:
    return len(row) > 1 and bool((row[1] or "").strip())


def _parse_event(row: list[str | None], current: date) -> Event:
    if len(row) < _COLUMN_COUNT:
        raise ValueError(
            f"Class row has {len(row)} columns, expected {_COLUMN_COUNT}: {row!r}"
        )
    (
        start,
        end,
        duration,
        subject,
        form,
        groups,
        room,
        lecturer,
        credit_form,
        tracks,
        notes,
    ) = (_normalize(cell) for cell in row[1:_COLUMN_COUNT])
    return Event(
        date=current,
        start=_parse_time(start, row),
        end=_parse_time(end, row),
        duration=duration,
        subject=subject,
        form=form,
        groups=groups,
        room=room,
        lecturer=lecturer,
        credit_form=credit_form,
        tracks=tracks,
        notes=notes,
    )


def _parse_time(text: str, row: list[str | None]) -> time:
    match = _TIME_RE.match(text)
    if match is None:
        raise ValueError(f"Malformed time {text!r} in row: {row!r}")
    return time(int(match.group(1)), int(match.group(2)))


def _normalize(cell: str | None) -> str:
    """Collapse intra-cell newlines, rejoining words split with a hyphen."""
    joined = _HYPHEN_BREAK_RE.sub("-", cell or "")
    return " ".join(joined.split())
