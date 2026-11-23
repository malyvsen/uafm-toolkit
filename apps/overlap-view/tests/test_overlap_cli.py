"""CLI tests: in-memory download plus the semester-based default range."""

import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from overlap_view.cli import (
    OverlapError,
    main,
    output_name,
    render_overlap,
    resolve_date_range,
)
from overlap_view.semester import semester_remainder
from plan_downloader import Credentials
from plan_parser import Event, parse_pdf

FIXTURES = (
    Path(__file__).resolve().parents[3] / "libs" / "plan-parser" / "tests" / "fixtures"
)
TWO = FIXTURES / "plan-two-weeks.pdf"


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

    monkeypatch.setattr("overlap_view.cli.download_timetable", fake_download)
    return calls


def test_overlap_produces_single_png(tmp_path: Path, two_events: list[Event]):
    expected = tmp_path / "plan-overlap-2026-10-19-2026-10-30.png"
    assert render_overlap(two_events, tmp_path) == expected
    with Image.open(expected) as image:
        image.load()
        assert image.size == (1744, 1698)


def test_rerun_overwrites_silently(tmp_path: Path, two_events: list[Event]):
    first = render_overlap(two_events, tmp_path)
    second = render_overlap(two_events, tmp_path)
    assert first == second
    assert first.exists()


def test_different_dates_give_different_names(two_events: list[Event]):
    full = output_name(min(e.date for e in two_events), max(e.date for e in two_events))
    first_week = [e for e in two_events if e.date < date(2026, 10, 26)]
    partial = output_name(
        min(e.date for e in first_week), max(e.date for e in first_week)
    )
    assert full == "plan-overlap-2026-10-19-2026-10-30.png"
    assert partial != full
    assert partial.startswith("plan-overlap-2026-10-19-")


def test_output_name_encodes_range():
    assert output_name(date(2026, 10, 19), date(2026, 10, 30)) == (
        "plan-overlap-2026-10-19-2026-10-30.png"
    )


def test_empty_events_fail(tmp_path: Path):
    with pytest.raises(OverlapError):
        render_overlap([], tmp_path)


def test_default_range_is_the_remaining_semester():
    today = date(2026, 10, 21)
    assert resolve_date_range(None, None, today=today) == semester_remainder(today)
    assert resolve_date_range(None, None, today=today) == (
        date(2026, 10, 21),
        date(2027, 1, 31),
    )


def test_explicit_dates_pass_through():
    assert resolve_date_range(
        date(2026, 10, 1), date(2026, 10, 31), today=date(2026, 10, 21)
    ) == (date(2026, 10, 1), date(2026, 10, 31))


def test_only_one_date_fails_fast(tmp_path: Path):
    with pytest.raises(SystemExit):
        main(date_from=date(2026, 10, 1), output_dir=tmp_path)
    with pytest.raises(SystemExit):
        main(date_to=date(2026, 10, 31), output_dir=tmp_path)


def test_main_downloads_in_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = stub_download(monkeypatch, TWO.read_bytes())
    main(
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
        output_dir=tmp_path,
    )
    assert calls == [(date(2026, 10, 1), date(2026, 10, 31))]
    assert list(tmp_path.glob("*.pdf")) == []
    assert (tmp_path / "plan-overlap-2026-10-19-2026-10-30.png").exists()


def test_main_defaults_to_semester_remainder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    calls = stub_download(monkeypatch, TWO.read_bytes())
    main(output_dir=tmp_path)
    today = date.today()
    assert calls == [semester_remainder(today)]
    assert (tmp_path / "plan-overlap-2026-10-19-2026-10-30.png").exists()


def test_console_script_help():
    script = Path(sys.executable).parent / "overlap-view"
    ok = subprocess.run(
        [str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
