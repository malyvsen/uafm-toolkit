"""CLI tests: rendering weeks, downloading on demand, plus an end-to-end smoke test."""

import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from calendar_grid.cli import CalendarError, main, render_weeks
from plan_downloader import Credentials
from plan_parser import Event, parse_pdf

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


def test_single_week_produces_dated_png(tmp_path: Path, single_events: list[Event]):
    expected = tmp_path / "plan-single-week-2026-10-19.png"
    assert render_weeks(single_events, tmp_path / "plan-single-week.pdf") == [expected]
    with Image.open(expected) as image:
        image.load()
        assert image.size == (1744, 1698)


def test_two_weeks_produce_both_dated_pngs(tmp_path: Path, two_events: list[Event]):
    expected = [
        tmp_path / "plan-two-weeks-2026-10-19.png",
        tmp_path / "plan-two-weeks-2026-10-26.png",
    ]
    assert render_weeks(two_events, tmp_path / "plan-two-weeks.pdf") == expected
    for path in expected:
        with Image.open(path) as image:
            image.load()
            assert image.mode == "RGB"


def test_rerun_overwrites_silently(tmp_path: Path, single_events: list[Event]):
    pdf = tmp_path / "plan-single-week.pdf"
    first = render_weeks(single_events, pdf)
    second = render_weeks(single_events, pdf)
    assert first == second
    assert first[0].exists()


def test_missing_pdf_fails(tmp_path: Path):
    with pytest.raises(SystemExit):
        main(tmp_path / "nie-ma.pdf")


def test_empty_events_fail(tmp_path: Path):
    with pytest.raises(CalendarError):
        render_weeks([], tmp_path / "plan-empty.pdf")


def test_console_script_end_to_end(tmp_path: Path):
    script = Path(sys.executable).parent / "calendar-grid"
    pdf = tmp_path / SINGLE.name
    shutil.copy(SINGLE, pdf)
    ok = subprocess.run(
        [str(script), str(pdf)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
    assert (tmp_path / "plan-single-week-2026-10-19.png").exists()


def test_only_one_date_fails_fast(tmp_path: Path):
    with pytest.raises(SystemExit):
        main(tmp_path / "plan.pdf", date_from=date(2026, 10, 1))


def test_both_dates_download_before_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    pdf = tmp_path / "plan.pdf"
    data = SINGLE.read_bytes()
    calls: list[tuple[date, date, bool]] = []

    def fake_download(
        date_from: date,
        date_to: date,
        *,
        headed: bool = False,
        credentials: Credentials | None = None,
    ) -> bytes:
        calls.append((date_from, date_to, headed))
        return data

    monkeypatch.setattr("calendar_grid.cli.download_timetable", fake_download)
    main(pdf, date_from=date(2026, 10, 1), date_to=date(2026, 10, 31))
    assert calls == [(date(2026, 10, 1), date(2026, 10, 31), False)]
    assert pdf.read_bytes() == data
    assert (tmp_path / "plan-2026-10-19.png").exists()
