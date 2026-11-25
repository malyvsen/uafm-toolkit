"""Load UAFM credentials and generate TOTP login codes."""

from auth.credentials import Credentials, CredentialsError, load_credentials
from auth.otp import current_code, generate_otp

__all__ = [
    "Credentials",
    "CredentialsError",
    "current_code",
    "generate_otp",
    "load_credentials",
]
