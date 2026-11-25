"""Load UAFM credentials from .env."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


class CredentialsError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@dataclass(frozen=True, slots=True)
class Credentials:
    username: str
    password: str
    totp_secret: str


def load_credentials(dotenv_path: Path | str | None = None) -> Credentials:
    """Read UAFM_USERNAME, UAFM_PASSWORD, and UAFM_TOTP_SECRET from .env."""
    if dotenv_path is not None:
        load_dotenv(dotenv_path)
    else:
        load_dotenv(find_dotenv(usecwd=True))
    username = os.environ.get("UAFM_USERNAME", "").strip()
    password = os.environ.get("UAFM_PASSWORD", "")
    totp_secret = "".join(os.environ.get("UAFM_TOTP_SECRET", "").split())
    missing = next(
        (
            name
            for name, value in (
                ("UAFM_USERNAME", username),
                ("UAFM_PASSWORD", password),
                ("UAFM_TOTP_SECRET", totp_secret),
            )
            if not value
        ),
        None,
    )
    if missing is not None:
        raise CredentialsError(f"Brak zmiennej {missing} w pliku .env.")
    return Credentials(username=username, password=password, totp_secret=totp_secret)
