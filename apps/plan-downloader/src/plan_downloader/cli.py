"""Command line: download a timetable PDF via Firefox with 2FA login."""

import getpass
import sys
from datetime import date
from pathlib import Path

import cyclopts

from plan_downloader.browser import DownloadError, download_timetable

app = cyclopts.App(
    name="plan-downloader",
    help="Download a study-plan PDF by driving Firefox.",
)


class CliError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@app.default
def main(
    username: str,
    date_from: date,
    date_to: date,
    output: Path,
    *,
    password: str | None = None,
    headed: bool = False,
) -> None:
    """Download the timetable PDF for a date range (dates as YYYY-MM-DD)."""
    try:
        resolved_password = password or getpass.getpass("Hasło: ")
        saved = download_timetable(
            username,
            resolved_password,
            ask_otp,
            date_from,
            date_to,
            output,
            headed=headed,
        )
    except (CliError, DownloadError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Zapisano {saved}")


def ask_otp() -> str:
    """Prompt for the one-time 2FA code at the moment the site asks for it."""
    otp = input("Kod jednorazowy 2FA: ").strip()
    if not otp:
        raise CliError("Nie podano kodu jednorazowego.")
    return otp
