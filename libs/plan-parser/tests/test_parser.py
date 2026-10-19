"""Parser tests against anonymized study-plan fixtures."""

from pathlib import Path

import pdfplumber
import pytest

from plan_parser import available_weeks, parse_pdf

FIXTURES = Path(__file__).parent / "fixtures"
SINGLE = FIXTURES / "plan-single-week.pdf"
TWO = FIXTURES / "plan-two-weeks.pdf"

REAL_SURNAMES = [
    "Sośnierz",
    "Nowak",
    "Iwański",
    "Miękina",
    "Kowalska",
    "Kalisz",
    "Baluch",
    "Majka",
    "Skowroński",
    "Oleszkowicz",
    "Gałka",
]


def test_single_week_holds_eight_events_on_one_monday():
    events = parse_pdf(SINGLE)
    assert len(events) == 8
    assert available_weeks(events) == ["2026-10-19"]


def test_two_weeks_hold_eighteen_events_on_two_mondays():
    events = parse_pdf(TWO)
    assert len(events) == 18
    assert available_weeks(events) == ["2026-10-19", "2026-10-26"]


def test_first_event_spot_check():
    event = parse_pdf(SINGLE)[0]
    assert event.date.isoformat() == "2026-10-19"
    assert (event.start.hour, event.start.minute) == (9, 40)
    assert (event.end.hour, event.end.minute) == (12, 5)
    assert event.subject == "Interpretacja prozy"
    assert event.form == "War"
    assert event.room == "bud.D D 319 - PRACOWNIA AKTORSKA"
    assert event.lecturer == "dr hab. Eleonora Rutkowska"
    assert event.duration == "3h00m"


def test_multigroup_lecture_spot_check():
    event = next(e for e in parse_pdf(SINGLE) if e.subject == "Antropologia")
    assert event.date.isoformat() == "2026-10-22"
    assert (event.start.hour, event.start.minute) == (13, 0)
    assert "B 203" in event.room
    assert "Aktorstwo" in event.groups
    assert "FIR" in event.groups
    assert "Finanse i rachunkowość" in event.tracks
    assert event.lecturer == "dr Serafin Górecki"
    assert event.credit_form == "Egzamin"


def test_hyphenated_surname_is_rejoined():
    event = next(e for e in parse_pdf(TWO) if e.date.isoformat() == "2026-10-30")
    assert event.subject == "Język filmu i telewizji"
    assert event.lecturer == "mgr Leokadia Piotrowska-Ostrowska"


def test_separator_hyphens_keep_their_spaces():
    event = next(e for e in parse_pdf(SINGLE) if e.subject == "Świadomość ciała")
    assert event.room == "bud.D D - 02 - SALA BALETOWA"


def test_date_carries_across_page_breaks():
    events = parse_pdf(TWO)
    carried = [e for e in events if e.date.isoformat() == "2026-10-26"]
    assert [e.subject for e in carried] == [
        "Interpretacja prozy",
        "Elementarne zadania aktorskie",
        "Emisja głosu",
        "Bezpieczeństwo lokalne",
    ]
    friday = [e for e in events if e.date.isoformat() == "2026-10-30"]
    assert len(friday) == 1


@pytest.mark.parametrize("fixture", [SINGLE, TWO])
def test_no_real_lecturer_surname_survives(fixture: Path):
    with pdfplumber.open(fixture) as pdf:
        text = " ".join((page.extract_text() or "") for page in pdf.pages)
    for surname in REAL_SURNAMES:
        assert surname not in text
