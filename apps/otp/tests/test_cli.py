"""Printing the current login code and copying it to the clipboard."""

import subprocess
import sys
from pathlib import Path

import pyperclip
import pytest

from auth import CredentialsError
from otp.cli import main


def test_prints_current_code_and_copies_to_clipboard(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    copied: list[str] = []
    monkeypatch.setattr("otp.cli.current_code", lambda: "123456")
    monkeypatch.setattr("otp.cli.pyperclip.copy", copied.append)
    main()
    assert capsys.readouterr().out == "123456\n"
    assert copied == ["123456"]


def test_missing_secret_fails_fast(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    def missing_code() -> str:
        raise CredentialsError("Brak zmiennej UAFM_TOTP_SECRET w pliku .env.")

    monkeypatch.setattr("otp.cli.current_code", missing_code)
    with pytest.raises(SystemExit):
        main()
    assert "UAFM_TOTP_SECRET" in capsys.readouterr().err


def test_clipboard_failure_still_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr("otp.cli.current_code", lambda: "123456")

    def fail_copy(_code: str) -> None:
        raise pyperclip.PyperclipException("no clipboard backend")

    monkeypatch.setattr("otp.cli.pyperclip.copy", fail_copy)
    main()
    out = capsys.readouterr()
    assert out.out == "123456\n"
    assert "schowka" in out.err


def test_console_script_help():
    script = Path(sys.executable).parent / "otp"
    ok = subprocess.run(
        [str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ok.returncode == 0, ok.stderr
