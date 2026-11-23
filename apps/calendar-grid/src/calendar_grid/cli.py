"""Command line: generate PNG timetables from the study plan."""

import sys
from datetime import date, timedelta
from pathlib import Path

import cyclopts
import platformdirs

from calendar_grid.renderer import render_week
from plan_downloader import CredentialsError, DownloadError, download_timetable
from plan_parser import Event, available_weeks, events_for_week, parse_pdf

app = cyclopts.App(
    name="calendar-grid",
    help="Generate PNG timetables from the study plan.",
)

DEFAULT_OUTPUT_DIR = Path(platformdirs.user_downloads_dir())


class CalendarError(Exception):
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
        saved = render_weeks(parse_pdf(data), output_dir)
    except (CalendarError, CredentialsError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    for path in saved:
        print(f"Zapisano {path}")


def resolve_date_range(
    date_from: date | None, date_to: date | None, *, today: date
) -> tuple[date, date]:
    """Fill missing dates with the current week plus the next one."""
    if date_from is None and date_to is None:
        monday = today - timedelta(days=today.weekday())
        return monday, monday + timedelta(days=13)
    if date_from is None or date_to is None:
        raise CalendarError("Podaj obie daty: --date-from i --date-to.")
    return date_from, date_to


def render_weeks(events: list[Event], output_dir: Path) -> list[Path]:
    """Render each week, save the PNGs to the output dir, and return the paths."""
    mondays = available_weeks(events)
    if not mondays:
        raise CalendarError("Plan nie zawiera żadnych zajęć w podanym zakresie.")
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for monday in mondays:
        path = output_dir / f"plan-{monday}.png"
        render_week(events_for_week(events, monday)).save(path)
        saved.append(path)
    return saved
