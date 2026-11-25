"""CLI tests: in-memory download, default date range, plus a console smoke test."""

import subprocess
import sys
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pytest
from PIL import Image

from plan_downloader import Credentials
from plan_parser import Event, parse_pdf
from week_view.cli import WeekError, main, render_weeks, resolve_date_range

FIXTURES = (
    Path(__file__).resolve().parents[3] / "libs" / "plan-parser" / "tests" / "fixtures"
)
SINGLE = FIXTURES / "plan-single-week.pdf"
TWO = FIXTURES / "plan-two-weeks.pdf"


@pytest.fixture(scope="module")
def single_events() -> list[Event]:
    return parse_pdf(SINGLE.read_bytes())


@pytest.fixture(scope="module")
def two_events() -> list[Event]:
    return parse_pdf(TWO.read_bytes())


def stub_download(
    monkeypatch: pytest.MonkeyPatch, data: bytes
) -> list[tuple[date, date]]:
    """Replace the timetable download with in-memory `data`, recording ranges."""
    calls: list[tuple[date, date]] = []

    def fake_download(
        date_from: date,
        date_to: date,
        *,
        on_progress: Callable[[str], None],
        credentials: Credentials | None = None,
    ) -> bytes:
        calls.append((date_from, date_to))
        on_progress("Pobieranie planu…")
        return data

    monkeypatch.setattr("week_view.cli.download_timetable", fake_download)
    return calls


def test_single_week_produces_dated_png(tmp_path: Path, single_events: list[Event]):
    expected = tmp_path / "plan-2026-10-19.png"
    assert render_weeks(single_events, tmp_path) == [expected]
    with Image.open(expected) as image:
        image.load()
        assert image.size == (1744, 1698)


def test_two_weeks_produce_both_dated_pngs(tmp_path: Path, two_events: list[Event]):
    expected = [
        tmp_path / "plan-2026-10-19.png",
        tmp_path / "plan-2026-10-26.png",
    ]
    assert render_weeks(two_events, tmp_path) == expected
    for path in expected:
        with Image.open(path) as image:
            image.load()
            assert image.mode == "RGB"


def test_rerun_overwrites_silently(tmp_path: Path, single_events: list[Event]):
    first = render_weeks(single_events, tmp_path)
    second = render_weeks(single_events, tmp_path)
    assert first == second
    assert first[0].exists()


def test_empty_events_fail(tmp_path: Path):
    with pytest.raises(WeekError):
        render_weeks([], tmp_path)


def test_default_range_is_current_plus_next_week():
    assert resolve_date_range(None, None, today=date(2026, 10, 21)) == (
        date(2026, 10, 19),
        date(2026, 11, 1),
    )


def test_explicit_dates_snap_to_full_weeks():
    assert resolve_date_range(
        date(2026, 10, 19), date(2026, 10, 25), today=date(2026, 10, 21)
    ) == (date(2026, 10, 19), date(2026, 10, 25))
    assert resolve_date_range(
        date(2026, 10, 1), date(2026, 10, 31), today=date(2026, 10, 21)
    ) == (date(2026, 9, 28), date(2026, 11, 1))


def test_single_date_gives_containing_week(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    assert resolve_date_range(date(2026, 10, 1), None, today=date(2026, 10, 21)) == (
        date(2026, 9, 28),
        date(2026, 10, 4),
    )
    assert resolve_date_range(None, date(2026, 10, 31), today=date(2026, 10, 21)) == (
        date(2026, 10, 26),
        date(2026, 11, 1),
    )

    calls = stub_download(monkeypatch, SINGLE.read_bytes())
    main(date_from=date(2026, 10, 1), output_dir=tmp_path)
    assert calls == [(date(2026, 9, 28), date(2026, 10, 4))]

    calls = stub_download(monkeypatch, SINGLE.read_bytes())
    main(date_to=date(2026, 10, 31), output_dir=tmp_path)
    assert calls == [(date(2026, 10, 26), date(2026, 11, 1))]


def test_reversed_range_fails_fast(tmp_path: Path):
    with pytest.raises(WeekError):
        resolve_date_range(
            date(2026, 10, 31), date(2026, 10, 1), today=date(2026, 10, 21)
        )
    with pytest.raises(SystemExit):
        main(
            date_from=date(2026, 10, 31),
            date_to=date(2026, 10, 1),
            output_dir=tmp_path,
        )


def test_main_downloads_in_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = stub_download(monkeypatch, SINGLE.read_bytes())
    main(
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
        output_dir=tmp_path,
    )
    assert calls == [(date(2026, 9, 28), date(2026, 11, 1))]
    assert list(tmp_path.glob("*.pdf")) == []
    assert (tmp_path / "plan-2026-10-19.png").exists()


def test_main_defaults_to_two_weeks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = stub_download(monkeypatch, SINGLE.read_bytes())
    main(output_dir=tmp_path)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    assert calls == [(monday, monday + timedelta(days=13))]
    assert (tmp_path / "plan-2026-10-19.png").exists()


def test_console_script_help():
    script = Path(sys.executable).parent / "week-view"
    ok = subprocess.run(
        [str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
