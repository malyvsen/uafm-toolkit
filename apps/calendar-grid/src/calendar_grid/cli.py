"""Command line: render one week of a study-plan PDF as a PNG timetable."""

import sys
from datetime import date
from pathlib import Path
from typing import Annotated

import cyclopts

from calendar_grid.renderer import render_week
from plan_parser import UnknownWeekError, available_weeks, events_for_week, parse_pdf

app = cyclopts.App(
    name="calendar-grid", help="Render a week of classes as a PNG timetable."
)


class CalendarError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@app.default
def main(
    pdf: Path,
    output: Annotated[Path, cyclopts.Parameter(alias="-o")],
    week: Annotated[str | None, cyclopts.Parameter(name="--week")] = None,
) -> None:
    """Render PDF's week (optionally chosen with --week, a Monday) into output PNG."""
    try:
        saved = render_pdf_week(pdf, output, week)
    except CalendarError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Zapisano {saved}")


def render_pdf_week(pdf: Path, output: Path, week: str | None) -> Path:
    """Resolve the week, render it, save the PNG, and return the saved path."""
    if not pdf.exists():
        raise CalendarError(f"Nie znaleziono pliku: {pdf}.")
    events = parse_pdf(pdf)
    mondays = available_weeks(events)
    if not mondays:
        raise CalendarError(f"Plik nie zawiera żadnych zajęć: {pdf}.")
    if week is None:
        if len(mondays) > 1:
            raise CalendarError(
                "Plik zawiera kilka tygodni. Podaj --week (RRRR-MM-DD). "
                f"Dostępne poniedziałki: {', '.join(mondays)}."
            )
        week = mondays[0]
    else:
        try:
            date.fromisoformat(week)
        except ValueError:
            raise CalendarError(
                f"Nieprawidłowa data: {week!r}. Użyj formatu RRRR-MM-DD (np. 2026-10-19)."
            ) from None
    try:
        selected = events_for_week(events, week)
    except UnknownWeekError:
        raise CalendarError(
            f"Brak zajęć w tygodniu {week}. Dostępne poniedziałki: {', '.join(mondays)}."
        ) from None
    except ValueError:
        # The date format was validated above, so only a non-Monday lands here.
        raise CalendarError(
            "Tydzień musi zaczynać się w poniedziałek. "
            f"Dostępne poniedziałki: {', '.join(mondays)}."
        ) from None
    output.parent.mkdir(parents=True, exist_ok=True)
    render_week(selected).save(output)
    return output
