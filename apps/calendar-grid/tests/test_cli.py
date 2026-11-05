"""CLI tests: batch rendering of all plan weeks plus an end-to-end smoke test."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from calendar_grid.cli import CalendarError, render_pdf_weeks

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "libs" / "plan-parser" / "tests" / "fixtures"
SINGLE = FIXTURES / "plan-single-week.pdf"
TWO = FIXTURES / "plan-two-weeks.pdf"


def copy_fixture(source: Path, tmp_path: Path) -> Path:
    copied = tmp_path / source.name
    shutil.copy(source, copied)
    return copied


def test_single_week_produces_dated_png(tmp_path: Path):
    pdf = copy_fixture(SINGLE, tmp_path)
    assert render_pdf_weeks(pdf) == [tmp_path / "plan-single-week-2026-10-19.png"]
    with Image.open(tmp_path / "plan-single-week-2026-10-19.png") as image:
        image.load()
        assert image.size == (1744, 1698)


def test_two_weeks_produce_both_dated_pngs(tmp_path: Path):
    pdf = copy_fixture(TWO, tmp_path)
    assert render_pdf_weeks(pdf) == [
        tmp_path / "plan-two-weeks-2026-10-19.png",
        tmp_path / "plan-two-weeks-2026-10-26.png",
    ]
    for monday in ("2026-10-19", "2026-10-26"):
        with Image.open(tmp_path / f"plan-two-weeks-{monday}.png") as image:
            image.load()
            assert image.mode == "RGB"


def test_rerun_overwrites_silently(tmp_path: Path):
    pdf = copy_fixture(SINGLE, tmp_path)
    first = render_pdf_weeks(pdf)
    second = render_pdf_weeks(pdf)
    assert first == second
    assert first[0].exists()


def test_missing_pdf_fails(tmp_path: Path):
    with pytest.raises(CalendarError):
        render_pdf_weeks(tmp_path / "nie-ma.pdf")


def test_console_script_end_to_end(tmp_path: Path):
    script = Path(sys.executable).parent / "calendar-grid"
    pdf = copy_fixture(SINGLE, tmp_path)
    ok = subprocess.run(
        [str(script), str(pdf)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
    assert (tmp_path / "plan-single-week-2026-10-19.png").exists()
