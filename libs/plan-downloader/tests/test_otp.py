"""Printing the current login code."""

import pytest

from plan_downloader.auth import CredentialsError
from plan_downloader.otp import main


def test_prints_current_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr("plan_downloader.otp.current_code", lambda: "123456")
    main()
    assert capsys.readouterr().out == "123456\n"


def test_missing_secret_fails_fast(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    def missing_code() -> str:
        raise CredentialsError("Brak zmiennej UAFM_TOTP_SECRET w pliku .env.")

    monkeypatch.setattr("plan_downloader.otp.current_code", missing_code)
    with pytest.raises(SystemExit):
        main()
    assert "UAFM_TOTP_SECRET" in capsys.readouterr().err
