"""Google OAuth for desktop: read client config, cache tokens, build service."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import platformdirs
from dotenv import find_dotenv, load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_CALENDAR_NAME = "UAFM Plan"


class GcalError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


@dataclass(frozen=True, slots=True)
class ClientConfig:
    """OAuth client ID and secret from Google Cloud Console."""

    client_id: str
    client_secret: str


def resolve_token_path(token_path: Path | None) -> Path:
    """Explicit token path or the default cache outside the repo."""
    if token_path is not None:
        return token_path.expanduser()
    return default_token_path()


def default_token_path() -> Path:
    """Token cache outside the repo, overridable via GCAL_TOKEN_PATH."""
    load_dotenv(find_dotenv(usecwd=True))
    override = os.environ.get("GCAL_TOKEN_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_config_dir("uafm-toolkit")) / "gcal-token.json"


def load_client_config(client_secrets: Path | None = None) -> ClientConfig:
    """Read the OAuth client from a secrets file or GCAL_CLIENT_* env vars."""
    load_dotenv(find_dotenv(usecwd=True))
    path = client_secrets or _env_path("GCAL_CLIENT_SECRETS_FILE")
    if path is not None:
        return _read_secrets_file(path)
    client_id = os.environ.get("GCAL_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GCAL_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise GcalError(
            "Brak GCAL_CLIENT_ID lub GCAL_CLIENT_SECRET w pliku .env "
            "(albo podaj --client-secrets z danymi klienta Desktop)."
        )
    return ClientConfig(client_id=client_id, client_secret=client_secret)


def authorize_interactively(
    token_path: Path, client_config: ClientConfig
) -> Credentials:
    """Run the interactive browser flow and cache the refresh token."""
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_config.client_id,
                "client_secret": client_config.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        SCOPES,
    )
    creds = flow.run_local_server(port=0)
    _save(token_path, creds)
    return creds


def load_cached_credentials(token_path: Path) -> Credentials:
    """Load cached credentials, refreshing silently; fail fast when absent."""
    if not token_path.exists():
        raise GcalError(
            "Brak autoryzacji Google. Uruchom najpierw `task -d apps/gcal-sync auth`."
        )
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    except (ValueError, OSError) as exc:
        raise GcalError(
            f"Nieprawidłowy token w {token_path}. Uruchom ponownie "
            "`task -d apps/gcal-sync auth`."
        ) from exc
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as exc:
            raise GcalError(
                "Nie udało się odświeżyć tokenu Google. Uruchom ponownie "
                "`task -d apps/gcal-sync auth`."
            ) from exc
        _save(token_path, creds)
        return creds
    raise GcalError(
        "Wygasła autoryzacja Google. Uruchom `task -d apps/gcal-sync auth`."
    )


def build_service(creds: Credentials) -> Resource:
    """Build the Calendar API client."""
    return build("calendar", "v3", credentials=creds)


def _read_secrets_file(path: Path) -> ClientConfig:
    """Parse Google's downloaded JSON with the Desktop client data."""
    try:
        data = json.loads(path.expanduser().read_text())
    except (OSError, ValueError) as exc:
        raise GcalError(f"Nie udało się odczytać {path}: {exc}.") from exc
    section = data.get("installed", data)
    try:
        return ClientConfig(
            client_id=section["client_id"], client_secret=section["client_secret"]
        )
    except KeyError as exc:
        raise GcalError(f"Plik {path} nie zawiera danych klienta OAuth.") from exc


def _env_path(name: str) -> Path | None:
    """Optional path from env, None when unset."""
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value else None


def _save(token_path: Path, creds: Credentials) -> None:
    """Persist the refresh token with owner-only permissions."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    try:
        token_path.chmod(0o600)
    except OSError:
        pass
