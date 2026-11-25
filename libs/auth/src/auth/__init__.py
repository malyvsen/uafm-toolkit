"""Load UAFM credentials and generate TOTP login codes."""

from auth.codes import current_code, generate_otp
from auth.credentials import Credentials, CredentialsError, load_credentials

__all__ = [
    "Credentials",
    "CredentialsError",
    "current_code",
    "generate_otp",
    "load_credentials",
]
