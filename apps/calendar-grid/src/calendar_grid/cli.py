"""Command line: render all weeks of a study-plan PDF as PNG timetables."""

import sys
from pathlib import Path

import cyclopts

from calendar_grid.renderer import render_week
from plan_parser import available_weeks, events_for_week, parse_pdf

app = cyclopts.App(
    name="calendar-grid", help="Render all weeks of classes as PNG timetables."
)


class CalendarError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@app.default
def main(pdf: Path) -> None:
    """Render every week of PDF as a dated PNG timetable next to it."""
    try:
        saved = render_pdf_weeks(pdf)
    except CalendarError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    for path in saved:
        print(f"Zapisano {path}")


def render_pdf_weeks(pdf: Path) -> list[Path]:
    """Render each week, save the PNGs, and return the saved paths."""
    if not pdf.exists():
        raise CalendarError(f"Nie znaleziono pliku: {pdf}.")
    events = parse_pdf(pdf)
    mondays = available_weeks(events)
    if not mondays:
        raise CalendarError(f"Plik nie zawiera żadnych zajęć: {pdf}.")
    saved = []
    for monday in mondays:
        selected = events_for_week(events, monday)
        path = pdf.parent / f"{pdf.stem}-{monday}.png"
        render_week(selected).save(path)
        saved.append(path)
    return saved
