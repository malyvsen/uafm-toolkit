"""One-time codes for the dziekanat login."""

from datetime import datetime

import pyotp

from auth.credentials import load_credentials


def current_code(at: datetime | None = None) -> str:
    """Read credentials from .env and generate the current login code."""
    return generate_otp(load_credentials().totp_secret, at)


def generate_otp(secret: str, at: datetime | None = None) -> str:
    """Generate the current 6-digit code for a TOTP shared secret."""
    totp = pyotp.TOTP("".join(secret.split()))
    return totp.at(at) if at is not None else totp.now()
