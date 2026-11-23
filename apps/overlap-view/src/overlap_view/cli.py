"""Command line: generate a typical-week PNG from the study plan."""

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import cyclopts
import platformdirs

from overlap_view.clustering import cluster_events
from overlap_view.renderer import render_typical
from overlap_view.semester import (
    SemesterIdentity,
    semester_identity,
    semester_remainder,
)
from plan_downloader import CredentialsError, DownloadError, download_timetable
from plan_parser import Event, parse_pdf

app = cyclopts.App(
    name="overlap-view",
    help="Generate a typical-week PNG from the study plan.",
)

DEFAULT_OUTPUT_DIR = Path(platformdirs.user_downloads_dir())


class OverlapError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@dataclass(frozen=True)
class SemesterDefault:
    """Default run: the remaining teaching period."""

    start: date
    end: date


@dataclass(frozen=True)
class CustomRange:
    """Explicit run: user-supplied dates."""

    start: date
    end: date


@app.default
def main(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    """Overlap every week in the range into one typical-week PNG."""
    try:
        date_range = resolve_date_range(date_from, date_to, today=date.today())
        data = download_timetable(date_range.start, date_range.end, on_progress=print)
        path = render_overlap(parse_pdf(data), output_dir, date_range)
    except (OverlapError, CredentialsError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Zapisano {path}")


def resolve_date_range(
    date_from: date | None, date_to: date | None, *, today: date
) -> SemesterDefault | CustomRange:
    """Fill missing dates with the remaining teaching period (see semester)."""
    if date_from is None and date_to is None:
        start, end = semester_remainder(today)
        return SemesterDefault(start, end)
    if date_from is None or date_to is None:
        raise OverlapError("Podaj obie daty: --date-from i --date-to.")
    return CustomRange(date_from, date_to)


def render_overlap(
    events: list[Event], output_dir: Path, date_range: SemesterDefault | CustomRange
) -> Path:
    """Render every event as one typical-week PNG and return its path."""
    clusters = cluster_events(events)
    if not clusters:
        raise OverlapError(
            "Plan nie zawiera zajęć od poniedziałku do piątku w podanym zakresie."
        )
    dates = [event.date for event in events]
    distinct_weeks = {(day.isocalendar().year, day.isocalendar().week) for day in dates}
    output_dir.mkdir(parents=True, exist_ok=True)
    date_from, date_to = min(dates), max(dates)
    match date_range:
        case SemesterDefault():
            filename = semester_output_name(semester_identity(date_from))
        case CustomRange():
            filename = custom_output_name(date_from, date_to)
    path = output_dir / filename
    render_typical(
        clusters,
        date_from=date_from,
        date_to=date_to,
        weeks=len(distinct_weeks),
    ).save(path)
    return path


def semester_output_name(identity: SemesterIdentity) -> str:
    """Semester PNG name, e.g. plan-2026-2027-semestr-zimowy.png."""
    return f"plan-{identity.start_year}-{identity.start_year + 1}-semestr-{identity.kind}.png"


def custom_output_name(date_from: date, date_to: date) -> str:
    """Dated PNG name so different ranges never overwrite each other."""
    return f"plan-{date_from.isoformat()}-{date_to.isoformat()}.png"
