"""CLI tests: the full --week behavior matrix plus an end-to-end smoke test."""

import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from calendar_grid.cli import CalendarError, render_pdf_week

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "libs" / "plan-parser" / "tests" / "fixtures"
SINGLE = FIXTURES / "plan-single-week.pdf"
TWO = FIXTURES / "plan-two-weeks.pdf"


def test_single_week_needs_no_flag(tmp_path: Path):
    output = tmp_path / "tydzien.png"
    assert render_pdf_week(SINGLE, output, None) == output
    with Image.open(output) as image:
        image.load()
        assert image.size == (1648, 1698)


def test_single_week_accepts_its_monday(tmp_path: Path):
    output = tmp_path / "tydzien.png"
    render_pdf_week(SINGLE, output, "2026-10-19")
    assert output.exists()


def test_multi_week_needs_a_flag(tmp_path: Path):
    with pytest.raises(CalendarError) as exc:
        render_pdf_week(TWO, tmp_path / "tydzien.png", None)
    assert "2026-10-19" in str(exc.value) and "2026-10-26" in str(exc.value)


def test_multi_week_renders_each_week(tmp_path: Path):
    for monday in ("2026-10-19", "2026-10-26"):
        output = tmp_path / f"{monday}.png"
        render_pdf_week(TWO, output, monday)
        with Image.open(output) as image:
            image.load()
            assert image.mode == "RGB"


def test_week_must_be_a_monday(tmp_path: Path):
    with pytest.raises(CalendarError) as exc:
        render_pdf_week(TWO, tmp_path / "tydzien.png", "2026-10-20")
    assert "poniedziałek" in str(exc.value)


def test_unknown_monday_fails_with_available_weeks(tmp_path: Path):
    with pytest.raises(CalendarError) as exc:
        render_pdf_week(TWO, tmp_path / "tydzien.png", "2026-11-02")
    assert "2026-10-19" in str(exc.value) and "2026-10-26" in str(exc.value)


def test_malformed_week_fails(tmp_path: Path):
    with pytest.raises(CalendarError) as exc:
        render_pdf_week(TWO, tmp_path / "tydzien.png", "19-10-2026")
    assert "RRRR-MM-DD" in str(exc.value)


def test_missing_pdf_fails(tmp_path: Path):
    with pytest.raises(CalendarError):
        render_pdf_week(tmp_path / "nie-ma.pdf", tmp_path / "tydzien.png", None)


def test_console_script_end_to_end(tmp_path: Path):
    script = Path(sys.executable).parent / "calendar-grid"
    output = tmp_path / "tydzien.png"
    ok = subprocess.run(
        [str(script), str(SINGLE), "-o", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
    assert output.exists()
    failing = subprocess.run(
        [str(script), str(TWO), "-o", str(tmp_path / "x.png")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failing.returncode != 0
    assert "poniedziałki" in failing.stderr
