"""Default download window: the remaining UAFM full-time teaching period.

Grounding: the rector's ordinances on the academic-year organization
(https://bip.uafm.edu.pl/prawo-uczelniane/organizacja-roku-akademickiego/);
e.g. in 2026/27 winter teaching runs from early October to late January and
summer teaching from early March to mid-June. Exact dates shift a little every
year, and the plan PDF only contains days that actually hold classes anyway,
so approximations are sufficient — explicit --date-from/--date-to wins.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

# Approximate teaching periods as (month, day); winter spans the year boundary.
WINTER_START = (10, 1)
WINTER_END = (1, 31)
SUMMER_START = (3, 1)
SUMMER_END = (6, 30)


SemesterKind = Literal["zimowy", "letni"]

# February already points at the upcoming summer; July–September at the upcoming winter.
SUMMER_MONTHS = range(2, 7)
ACADEMIC_YEAR_START_MONTH = 7


@dataclass(frozen=True)
class SemesterIdentity:
    """Academic-year start plus winter/summer kind for a calendar date."""

    start_year: int
    kind: SemesterKind


def semester_identity(day: date) -> SemesterIdentity:
    """Classify `day` into its semester (Feb → summer, Jul–Sep → winter)."""
    kind: SemesterKind = "letni" if day.month in SUMMER_MONTHS else "zimowy"
    start_year = day.year if day.month >= ACADEMIC_YEAR_START_MONTH else day.year - 1
    return SemesterIdentity(start_year=start_year, kind=kind)


def semester_remainder(today: date) -> tuple[date, date]:
    """Return the remaining teaching period containing (or following) `today`."""
    year = today.year
    if today >= date(year, *WINTER_START):
        return today, date(year + 1, *WINTER_END)
    if today <= date(year, *WINTER_END):
        return today, date(year, *WINTER_END)
    if today < date(year, *SUMMER_START):
        return date(year, *SUMMER_START), date(year, *SUMMER_END)
    if today <= date(year, *SUMMER_END):
        return today, date(year, *SUMMER_END)
    return date(year, *WINTER_START), date(year + 1, *WINTER_END)
