"""Print the current login code."""

import sys

from auth import CredentialsError, current_code


def main() -> None:
    """Print the current login code from .env (valid ~30 seconds)."""
    try:
        print(current_code())
    except CredentialsError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
