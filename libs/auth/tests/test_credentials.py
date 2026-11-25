"""Loading UAFM credentials from .env."""

import pytest

from auth import CredentialsError, load_credentials

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def test_loads_credentials_from_dotenv_file(tmp_path, monkeypatch):
    monkeypatch.delenv("UAFM_USERNAME", raising=False)
    monkeypatch.delenv("UAFM_PASSWORD", raising=False)
    monkeypatch.delenv("UAFM_TOTP_SECRET", raising=False)
    (tmp_path / ".env").write_text(
        f"UAFM_USERNAME=jan\nUAFM_PASSWORD=tajne\nUAFM_TOTP_SECRET={RFC_SECRET}\n"
    )
    credentials = load_credentials(tmp_path / ".env")
    assert credentials.username == "jan"
    assert credentials.password == "tajne"
    assert credentials.totp_secret == RFC_SECRET


def test_missing_variable_fails_fast(tmp_path, monkeypatch):
    monkeypatch.delenv("UAFM_USERNAME", raising=False)
    monkeypatch.delenv("UAFM_PASSWORD", raising=False)
    monkeypatch.delenv("UAFM_TOTP_SECRET", raising=False)
    (tmp_path / ".env").write_text("UAFM_USERNAME=jan\n")
    with pytest.raises(CredentialsError, match="UAFM_PASSWORD"):
        load_credentials(tmp_path / ".env")
