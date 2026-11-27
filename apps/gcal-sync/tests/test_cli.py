"""CLI tests: date windows, calendar lookup, and a dry sync without network."""

import subprocess
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from gcal_sync.cli import (
    apply_plan,
    list_managed,
    resolve_calendar_id,
    resolve_date_range,
    sync,
)
from gcal_sync.events import SyncPlan, to_google_event
from gcal_sync.google_auth import GcalError
from semester import semester_remainder

FIXTURES = (
    Path(__file__).resolve().parents[3] / "libs" / "plan-parser" / "tests" / "fixtures"
)
SINGLE = FIXTURES / "plan-single-week.pdf"


class Request:
    """Google client stub: .execute() returns the canned response."""

    def __init__(self, response: dict):
        self.response = response

    def execute(self) -> dict:
        return self.response


class FakeService:
    """Minimal Calendar API double recording every write."""

    def __init__(
        self,
        *,
        calendars: tuple[dict, ...] = (),
        event_pages: tuple[dict, ...] = ({"items": []},),
        created_id: str = "cal-1",
    ):
        self._calendars = list(calendars)
        self._event_pages = list(event_pages)
        self._created_id = created_id
        self.list_kwargs: dict = {}
        self.created: list[dict] = []
        self.inserted: list[tuple[str, dict]] = []
        self.patched: list[tuple[str, str, dict]] = []
        self.deleted: list[tuple[str, str]] = []

    def calendarList(self):
        outer = self
        return SimpleNamespace(
            list=lambda **kwargs: Request({"items": outer._calendars})
        )

    def calendars(self):
        outer = self

        def insert(*, body):
            outer.created.append(body)
            return Request({"id": outer._created_id})

        return SimpleNamespace(insert=insert)

    def events(self):
        outer = self

        def list(**kwargs):
            outer.list_kwargs = kwargs
            page = outer._event_pages.pop(0) if outer._event_pages else {"items": []}
            return Request(page)

        def insert(*, calendarId, body):
            outer.inserted.append((calendarId, body))
            return Request(body)

        def patch(*, calendarId, eventId, body):
            outer.patched.append((calendarId, eventId, body))
            return Request(body)

        def delete(*, calendarId, eventId):
            outer.deleted.append((calendarId, eventId))
            return Request({})

        return SimpleNamespace(list=list, insert=insert, patch=patch, delete=delete)


def stub_sync(monkeypatch: pytest.MonkeyPatch, data: bytes) -> FakeService:
    """Stub the download, credentials, and service building behind `sync`."""
    monkeypatch.setattr(
        "gcal_sync.cli.download_timetable",
        lambda start, end, *, on_progress, credentials=None: data,
    )
    service = FakeService()
    monkeypatch.setattr(
        "gcal_sync.cli.load_cached_credentials", lambda tokens: object()
    )
    monkeypatch.setattr("gcal_sync.cli.build_service", lambda creds: service)
    return service


def test_default_range_is_the_remaining_teaching_period():
    assert resolve_date_range(None, None, today=date(2026, 10, 15)) == (
        semester_remainder(date(2026, 10, 15))
    )
    assert resolve_date_range(None, None, today=date(2027, 2, 5)) == (
        semester_remainder(date(2027, 2, 5))
    )


def test_explicit_range_passes_through():
    assert resolve_date_range(
        date(2026, 10, 1), date(2026, 10, 31), today=date(2026, 10, 21)
    ) == (date(2026, 10, 1), date(2026, 10, 31))


def test_half_range_fails():
    with pytest.raises(GcalError):
        resolve_date_range(date(2026, 10, 1), None, today=date(2026, 10, 21))


def test_reversed_range_fails():
    with pytest.raises(GcalError):
        resolve_date_range(
            date(2026, 10, 31), date(2026, 10, 1), today=date(2026, 10, 21)
        )


def test_resolve_calendar_id_uses_explicit_id():
    assert resolve_calendar_id(FakeService(), "UAFM Plan", "explicit") == "explicit"


def test_resolve_calendar_id_finds_by_name():
    service = FakeService(calendars=({"id": "found", "summary": "UAFM Plan"},))
    assert resolve_calendar_id(service, "UAFM Plan", None) == "found"
    assert service.created == []


def test_resolve_calendar_id_creates_missing():
    service = FakeService()
    assert resolve_calendar_id(service, "UAFM Plan", None) == "cal-1"
    assert service.created == [{"summary": "UAFM Plan", "timeZone": "Europe/Warsaw"}]


def test_list_managed_follows_pages_and_skips_malformed(make_event):
    good = to_google_event(make_event())
    service = FakeService(
        event_pages=(
            {"items": [dict(good), {"summary": "broken"}], "nextPageToken": "next"},
            {"items": [dict(good)]},
        )
    )
    found = list_managed(service, "cal-1", date(2026, 10, 1), date(2026, 10, 31))
    assert found == {good["id"]: good}
    assert service.list_kwargs["privateExtendedProperty"] == "uafmToolkit=1"
    assert service.list_kwargs["singleEvents"] is True


def test_apply_plan_writes_every_change(make_event):
    insert = to_google_event(make_event())
    update = to_google_event(make_event(room="s. 202"))
    plan = SyncPlan(insert=(insert,), update=(update,), delete_ids=("stale",))
    service = FakeService()
    apply_plan(service, "cal-1", plan)
    assert [body for _, body in service.inserted] == [dict(insert)]
    assert [(calendar, eid) for calendar, eid, _ in service.patched] == [
        ("cal-1", update["id"])
    ]
    assert service.deleted == [("cal-1", "stale")]


def test_sync_dry_run_lists_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    service = stub_sync(monkeypatch, SINGLE.read_bytes())
    sync(
        date_from=date(2026, 10, 19),
        date_to=date(2026, 10, 25),
        token_path=tmp_path / "token.json",
        dry_run=True,
    )
    assert service.inserted == [] and service.patched == [] and service.deleted == []
    out = capsys.readouterr().out
    assert "do dodania" in out


def test_sync_writes_inserts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    service = stub_sync(monkeypatch, SINGLE.read_bytes())
    sync(
        date_from=date(2026, 10, 19),
        date_to=date(2026, 10, 25),
        token_path=tmp_path / "token.json",
    )
    assert service.inserted
    assert all(calendar == "cal-1" for calendar, _ in service.inserted)
    assert "Dodano" in capsys.readouterr().out


def test_sync_missing_auth_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    def fail(tokens):
        raise GcalError("Brak autoryzacji Google.")

    monkeypatch.setattr("gcal_sync.cli.load_cached_credentials", fail)
    with pytest.raises(SystemExit):
        sync(
            date_from=date(2026, 10, 19),
            date_to=date(2026, 10, 25),
            token_path=tmp_path / "token.json",
        )
    assert "autoryzacji" in capsys.readouterr().err


def test_console_script_help():
    script = Path(sys.executable).parent / "gcal-sync"
    ok = subprocess.run(
        [str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
