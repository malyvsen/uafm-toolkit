"""Command line: print the current login code and copy it to the clipboard."""

import sys

import cyclopts
import pyperclip

from auth import CredentialsError, current_code

app = cyclopts.App(
    name="otp",
    help="Print the current login code and copy it to the clipboard.",
)


@app.default
def main() -> None:
    """Print the current login code from .env and copy it to the clipboard."""
    try:
        code = current_code()
    except CredentialsError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(code)
    try:
        pyperclip.copy(code)
    except pyperclip.PyperclipException as exc:
        print(f"Ostrzeżenie: nie skopiowano kodu do schowka ({exc}).", file=sys.stderr)
