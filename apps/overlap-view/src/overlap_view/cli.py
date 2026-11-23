"""Command line: generate a typical-week PNG from the study plan."""

import sys
from datetime import date
from pathlib import Path

import cyclopts
import platformdirs

from overlap_view.clustering import cluster_events
from overlap_view.renderer import render_typical
from overlap_view.semester import semester_remainder
from plan_downloader import CredentialsError, DownloadError, download_timetable
from plan_parser import Event, parse_pdf

app = cyclopts.App(
    name="overlap-view",
    help="Generate a typical-week PNG from the study plan.",
)

DEFAULT_OUTPUT_DIR = Path(platformdirs.user_downloads_dir())
OUTPUT_NAME = "plan-overlap.png"


class OverlapError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@app.default
def main(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    """Overlap every week in the range into one typical-week PNG."""
    try:
        start, end = resolve_date_range(date_from, date_to, today=date.today())
        data = download_timetable(start, end, on_progress=print)
        path = render_overlap(parse_pdf(data), output_dir)
    except (OverlapError, CredentialsError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Zapisano {path}")


def resolve_date_range(
    date_from: date | None, date_to: date | None, *, today: date
) -> tuple[date, date]:
    """Fill missing dates with the remaining teaching period (see semester)."""
    if date_from is None and date_to is None:
        return semester_remainder(today)
    if date_from is None or date_to is None:
        raise OverlapError("Podaj obie daty: --date-from i --date-to.")
    return date_from, date_to


def render_overlap(events: list[Event], output_dir: Path) -> Path:
    """Render every event as one typical-week PNG and return its path."""
    clusters = cluster_events(events)
    if not clusters:
        raise OverlapError(
            "Plan nie zawiera zajęć od poniedziałku do piątku w podanym zakresie."
        )
    dates = [event.date for event in events]
    distinct_weeks = {(day.isocalendar().year, day.isocalendar().week) for day in dates}
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / OUTPUT_NAME
    render_typical(
        clusters,
        date_from=min(dates),
        date_to=max(dates),
        weeks=len(distinct_weeks),
    ).save(path)
    return path
