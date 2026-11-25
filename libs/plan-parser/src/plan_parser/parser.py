"""Turn study-plan PDF tables into typed events."""

import io
import re
from datetime import date, time

import pdfplumber

from plan_parser.events import Event

_DATE_PREFIX = "Data Zajęć:"
_DATE_RE = re.compile(r"^Data Zajęć:\s*(\d{4})\.(\d{2})\.(\d{2})")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
_HYPHEN_BREAK_RE = re.compile(r"(?<=\S)-\n\s*")
_COLUMN_COUNT = 12

Row = list[str | None]
Table = list[Row]


def parse_pdf(data: bytes) -> list[Event]:
    """Parse every class row in the PDF bytes into events, in file order."""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        tables: list[Table] = [
            table for page in pdf.pages for table in page.extract_tables()
        ]
    return parse_tables(tables)


def parse_tables(tables: list[Table]) -> list[Event]:
    """Parse already-extracted tables into events, in table order."""
    events: list[Event] = []
    current: date | None = None
    for table in tables:
        for row in table:
            if _is_header(row):
                continue
            if _is_date_row(row):
                current = _parse_date_row(row)
            elif _is_class_row(row):
                if current is None:
                    raise ValueError("Class row found before any Data Zajęć row")
                events.append(_parse_event(row, current))
            else:
                raise ValueError(f"Unrecognized table row: {row!r}")
    return events


def _is_header(row: Row) -> bool:
    # The header carries a None spacer in 12-column tables but not in the
    # 11-column header-only shape, so match any cell instead of one column.
    return any("Zajęcia" in (cell or "") for cell in row)


def _is_date_row(row: Row) -> bool:
    return len(row) > 0 and (row[0] or "").startswith(_DATE_PREFIX)


def _parse_date_row(row: Row) -> date:
    match = _DATE_RE.match(row[0] or "")
    if match is None:
        raise ValueError(f"Malformed Data Zajęć row: {row[0]!r}")
    year, month, day = (int(part) for part in match.groups())
    return date(year, month, day)


def _is_class_row(row: Row) -> bool:
    return len(row) > 1 and bool((row[1] or "").strip())


def _parse_event(row: Row, current: date) -> Event:
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


def _parse_time(text: str, row: Row) -> time:
    match = _TIME_RE.match(text)
    if match is None:
        raise ValueError(f"Malformed time {text!r} in row: {row!r}")
    return time(int(match.group(1)), int(match.group(2)))


def _normalize(cell: str | None) -> str:
    """Collapse intra-cell newlines, rejoining words split with a hyphen."""
    joined = _HYPHEN_BREAK_RE.sub("-", cell or "")
    return " ".join(joined.split())
