"""Command line: generate PNG timetables from the study plan."""

import sys
from datetime import date, timedelta
from pathlib import Path

import cyclopts
import platformdirs

from auth import CredentialsError
from plan_downloader import DownloadError, download_timetable
from plan_parser import Event, available_weeks, events_for_week, parse_pdf
from week_view.renderer import render_week

app = cyclopts.App(
    name="week-view",
    help="Generate PNG timetables from the study plan.",
)

DEFAULT_OUTPUT_DIR = Path(platformdirs.user_downloads_dir())


class WeekError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@app.default
def main(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    """Generate every week as dated PNGs."""
    try:
        start, end = resolve_date_range(date_from, date_to, today=date.today())
        data = download_timetable(start, end, on_progress=print)
        try:
            events = parse_pdf(data)
        except ValueError as exc:
            raise WeekError(
                "Nie udało się odczytać planu: nieoczekiwany format pliku."
            ) from exc
        saved = render_weeks(events, output_dir)
    except (WeekError, CredentialsError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    for path in saved:
        print(f"Zapisano {path}")


def resolve_date_range(
    date_from: date | None, date_to: date | None, *, today: date
) -> tuple[date, date]:
    """Full Monday–Sunday weeks covering the dates, defaulting to this week plus the next."""
    start = date_from if date_from is not None else date_to
    end = date_to if date_to is not None else date_from
    if start is None or end is None:
        monday = today - timedelta(days=today.weekday())
        return monday, monday + timedelta(days=13)
    if start > end:
        raise WeekError("--date-from nie może być późniejsze niż --date-to.")
    monday = start - timedelta(days=start.weekday())
    sunday = end + timedelta(days=6 - end.weekday())
    return monday, sunday


def render_weeks(events: list[Event], output_dir: Path) -> list[Path]:
    """Render each week, save the PNGs to the output dir, and return the paths."""
    mondays = available_weeks(events)
    if not mondays:
        raise WeekError("Plan nie zawiera żadnych zajęć w podanym zakresie.")
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for monday in mondays:
        path = output_dir / f"plan-{monday}.png"
        render_week(events_for_week(events, monday)).save(path)
        saved.append(path)
    return saved
