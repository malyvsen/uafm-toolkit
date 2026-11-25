"""Browser-driven timetable download."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from auth import Credentials
from plan_downloader import browser as browser_module
from plan_downloader.browser import download_timetable, format_date_for_typing


def test_reports_progress_in_order(monkeypatch: pytest.MonkeyPatch):
    stub_browser(monkeypatch)
    messages: list[str] = []
    download_timetable(
        date(2026, 10, 1),
        date(2026, 10, 31),
        on_progress=messages.append,
        credentials=Credentials(username="u", password="p", totp_secret="s"),
    )
    assert messages == [
        "Otwieranie dziekanatu…",
        "Logowanie…",
        "Otwieranie planów zajęć…",
        "Wyszukiwanie zajęć…",
        "Pobieranie planu…",
    ]


def test_november_date_matches_manual_typing():
    assert format_date_for_typing(date(2026, 11, 23)) == "23112026"


def test_single_digit_day_and_month_are_zero_padded():
    assert format_date_for_typing(date(2026, 1, 5)) == "05012026"


def stub_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace Playwright and page steps with no-op mocks."""
    page = MagicMock()
    browser = MagicMock()
    browser.new_page.return_value = page
    playwright = MagicMock()
    playwright.firefox.launch.return_value = browser
    context = MagicMock()
    context.__enter__.return_value = playwright
    monkeypatch.setattr(browser_module, "sync_playwright", lambda: context)
    monkeypatch.setattr(browser_module, "_dismiss_cookies", lambda _page: None)
    monkeypatch.setattr(browser_module, "_login", lambda _page, _creds: None)
    monkeypatch.setattr(browser_module, "_open_plans", lambda _page: None)
    monkeypatch.setattr(
        browser_module, "_set_date_range", lambda _page, _from, _to: None
    )
    monkeypatch.setattr(browser_module, "_fetch_timetable_pdf", lambda _page: b"%PDF")
