"""Generating TOTP login codes."""

from datetime import datetime

from auth import current_code, generate_otp

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def test_known_vector_matches_authenticator_app():
    assert generate_otp(RFC_SECRET, datetime.fromtimestamp(59)) == "287082"


def test_secret_with_spaces_and_lowercase_still_works():
    spaced = "gezd gnbv gy3t qojq gezd gnbv gy3t qojq"
    assert generate_otp(spaced, datetime.fromtimestamp(59)) == "287082"


def test_current_code_reads_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("UAFM_USERNAME", raising=False)
    monkeypatch.delenv("UAFM_PASSWORD", raising=False)
    monkeypatch.delenv("UAFM_TOTP_SECRET", raising=False)
    (tmp_path / ".env").write_text(
        f"UAFM_USERNAME=jan\nUAFM_PASSWORD=tajne\nUAFM_TOTP_SECRET={RFC_SECRET}\n"
    )
    monkeypatch.chdir(tmp_path)
    assert current_code(datetime.fromtimestamp(59)) == "287082"
