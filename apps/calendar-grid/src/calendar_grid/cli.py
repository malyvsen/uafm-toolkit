"""Command line: render all weeks of a study-plan PDF as PNG timetables."""

import sys
from datetime import date
from pathlib import Path

import cyclopts

from calendar_grid.renderer import render_week
from plan_downloader import CredentialsError, DownloadError, download_timetable
from plan_parser import Event, available_weeks, events_for_week, parse_pdf

app = cyclopts.App(
    name="calendar-grid", help="Render all weeks of classes as PNG timetables."
)


class CalendarError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@app.default
def main(
    pdf: Path,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    headed: bool = False,
) -> None:
    """Render every week of PDF as dated PNGs, downloading it first if asked."""
    try:
        data = resolve_pdf_bytes(pdf, date_from, date_to, headed=headed)
        saved = render_weeks(parse_pdf(data), pdf)
    except (CalendarError, CredentialsError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    for path in saved:
        print(f"Zapisano {path}")


def resolve_pdf_bytes(
    pdf: Path,
    date_from: date | None,
    date_to: date | None,
    *,
    headed: bool = False,
) -> bytes:
    """Download the PDF for a date range, or read it from disk."""
    if date_from is not None and date_to is not None:
        data = download_timetable(date_from, date_to, headed=headed)
        pdf.write_bytes(data)
        return data
    if (date_from is None) != (date_to is None):
        raise CalendarError("Podaj obie daty: --date-from i --date-to.")
    if not pdf.exists():
        raise CalendarError(f"Nie znaleziono pliku: {pdf}.")
    return pdf.read_bytes()


def render_weeks(events: list[Event], pdf: Path) -> list[Path]:
    """Render each week, save the PNGs next to the PDF, and return the paths."""
    mondays = available_weeks(events)
    if not mondays:
        raise CalendarError(f"Plik nie zawiera żadnych zajęć: {pdf}.")
    saved: list[Path] = []
    for monday in mondays:
        path = pdf.parent / f"{pdf.stem}-{monday}.png"
        render_week(events_for_week(events, monday)).save(path)
        saved.append(path)
    return saved
