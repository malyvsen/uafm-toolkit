"""Command line: push the study plan to Google Calendar from your laptop."""

import sys
from collections.abc import Callable, Iterator
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import cyclopts

from auth import CredentialsError
from gcal_sync.events import (
    MARKER_KEY,
    MARKER_VALUE,
    TIMEZONE,
    GoogleEvent,
    SyncPlan,
    diff_bodies,
    events_to_bodies,
)
from gcal_sync.google_auth import (
    DEFAULT_CALENDAR_NAME,
    GcalError,
    authorize_interactively,
    build_service,
    default_token_path,
    load_cached_credentials,
    load_client_config,
    resolve_token_path,
)
from plan_downloader import DownloadError, download_timetable
from plan_parser import Event, parse_pdf
from semester import semester_remainder

app = cyclopts.App(
    name="gcal-sync",
    help="Push the study plan to Google Calendar from your laptop.",
)

DateFrom = Annotated[
    date | None,
    cyclopts.Parameter(
        help="First day to sync; needs --date-to.",
        show_default="remaining teaching period",
    ),
]
DateTo = Annotated[
    date | None,
    cyclopts.Parameter(
        help="Last day to sync; needs --date-from.",
        show_default="remaining teaching period",
    ),
]
CalendarName = Annotated[
    str, cyclopts.Parameter(help="Calendar name to find or create.")
]
CalendarId = Annotated[
    str | None,
    cyclopts.Parameter(
        help="Calendar ID; finds or creates --calendar-name when missing.",
        show_default="from --calendar-name",
    ),
]
TokenPath = Annotated[
    Path | None,
    cyclopts.Parameter(
        help="Token cache file (env GCAL_TOKEN_PATH).",
        show_default=lambda _: str(default_token_path()),
    ),
]
ClientSecrets = Annotated[
    Path | None,
    cyclopts.Parameter(
        help="OAuth client JSON (env GCAL_CLIENT_SECRETS_FILE or GCAL_CLIENT_ID/SECRET).",
        show_default="from env",
    ),
]
DryRun = Annotated[bool, cyclopts.Parameter(help="Preview counts without writing.")]


@app.default
def sync(
    *,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    calendar_name: CalendarName = DEFAULT_CALENDAR_NAME,
    calendar_id: CalendarId = None,
    token_path: TokenPath = None,
    dry_run: DryRun = False,
) -> None:
    """Sync the remaining teaching period (or an explicit range) to Google."""
    try:
        start, end = resolve_date_range(date_from, date_to, today=date.today())
        tokens = resolve_token_path(token_path)
        service = build_service(load_cached_credentials(tokens))
        target = resolve_calendar_id(service, calendar_name, calendar_id)
        data = download_timetable(start, end, on_progress=print)
        plan = diff_bodies(
            events_to_bodies(parse_events(data)),
            list_managed(service, target, start, end),
        )
        if dry_run:
            print(
                f"Próba: do dodania {len(plan.insert)}, "
                f"do aktualizacji {len(plan.update)}, "
                f"do usunięcia {len(plan.delete_ids)}."
            )
            return
        apply_plan(service, target, plan)
    except (GcalError, CredentialsError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        f"Dodano {len(plan.insert)}, "
        f"zaktualizowano {len(plan.update)}, "
        f"usunięto {len(plan.delete_ids)}."
    )


@app.command
def auth(
    *,
    token_path: TokenPath = None,
    client_secrets: ClientSecrets = None,
) -> None:
    """Authorize Google Calendar access once (opens a browser)."""
    try:
        config = load_client_config(client_secrets)
        tokens = resolve_token_path(token_path)
        authorize_interactively(tokens, config)
    except GcalError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Zapisano token {tokens}")


def resolve_date_range(
    date_from: date | None, date_to: date | None, *, today: date
) -> tuple[date, date]:
    """Remaining teaching period by default; explicit range needs both dates."""
    if date_from is None and date_to is None:
        return semester_remainder(today)
    if date_from is None or date_to is None:
        raise GcalError("Podaj obie daty: --date-from i --date-to.")
    if date_from > date_to:
        raise GcalError("--date-from nie może być późniejsze niż --date-to.")
    return date_from, date_to


def parse_events(data: bytes) -> list[Event]:
    """Parse downloaded PDF bytes, reporting an unrecognized layout in Polish."""
    try:
        return parse_pdf(data)
    except ValueError as exc:
        raise GcalError(
            "Nie udało się odczytać planu: nieoczekiwany format pliku."
        ) from exc


def resolve_calendar_id(service, calendar_name: str, calendar_id: str | None) -> str:
    """Use the explicit ID or find-or-create a dedicated calendar by name."""
    if calendar_id:
        return calendar_id
    for response in _pages(
        lambda token: service.calendarList().list(
            minAccessRole="writer", maxResults=250, pageToken=token
        )
    ):
        for entry in response.get("items", []):
            if entry.get("summary") == calendar_name:
                return entry["id"]
    created = (
        service.calendars()
        .insert(body={"summary": calendar_name, "timeZone": TIMEZONE})
        .execute()
    )
    return created["id"]


def list_managed(
    service, calendar_id: str, start: date, end: date
) -> dict[str, GoogleEvent]:
    """List sync-managed events in range, following every result page."""
    time_min, time_max = _bounds(start, end)
    found: dict[str, GoogleEvent] = {}
    for response in _pages(
        lambda token: service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            privateExtendedProperty=f"{MARKER_KEY}={MARKER_VALUE}",
            maxResults=2500,
            pageToken=token,
        )
    ):
        for item in response.get("items", []):
            if "id" in item and "start" in item and "end" in item:
                found[item["id"]] = item
    return found


def apply_plan(service, calendar_id: str, plan: SyncPlan) -> None:
    """Insert, patch, and delete every change in the plan."""
    for body in plan.insert:
        service.events().insert(calendarId=calendar_id, body=body).execute()
    for body in plan.update:
        service.events().patch(
            calendarId=calendar_id, eventId=body["id"], body=body
        ).execute()
    for event_id in plan.delete_ids:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


def _pages(list_call: Callable[[str | None], Any]) -> Iterator[dict]:
    """Yield every result page of a token-paginated Calendar API listing."""
    page_token: str | None = None
    while True:
        response = list_call(page_token).execute()
        yield response
        page_token = response.get("nextPageToken")
        if not page_token:
            return


def _bounds(start: date, end: date) -> tuple[str, str]:
    """Inclusive day range as RFC 3339 bounds in the plan timezone."""
    zone = ZoneInfo(TIMEZONE)
    time_min = datetime.combine(start, time.min).replace(tzinfo=zone).isoformat()
    time_max = (
        datetime.combine(end + timedelta(days=1), time.min)
        .replace(tzinfo=zone)
        .isoformat()
    )
    return time_min, time_max
