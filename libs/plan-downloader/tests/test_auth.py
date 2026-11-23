"""Credentials loading and TOTP generation."""

from datetime import datetime

import pytest

from plan_downloader.auth import (
    CredentialsError,
    current_code,
    generate_otp,
    load_credentials,
)

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def test_known_vector_matches_authenticator_app():
    assert generate_otp(RFC_SECRET, datetime.fromtimestamp(59)) == "287082"


def test_secret_with_spaces_and_lowercase_still_works():
    spaced = "gezd gnbv gy3t qojq gezd gnbv gy3t qojq"
    assert generate_otp(spaced, datetime.fromtimestamp(59)) == "287082"


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


def test_current_code_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("UAFM_USERNAME", raising=False)
    monkeypatch.delenv("UAFM_PASSWORD", raising=False)
    monkeypatch.delenv("UAFM_TOTP_SECRET", raising=False)
    (tmp_path / ".env").write_text(
        f"UAFM_USERNAME=jan\nUAFM_PASSWORD=tajne\nUAFM_TOTP_SECRET={RFC_SECRET}\n"
    )
    monkeypatch.chdir(tmp_path)
    assert current_code(datetime.fromtimestamp(59)) == "287082"
