"""Browser-driven timetable download."""

from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from auth import Credentials
from plan_downloader import browser as browser_module
from plan_downloader.browser import (
    DownloadError,
    _set_date_range,
    _wait_for_results,
    download_timetable,
    format_date_for_typing,
)


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


def test_types_data_do_before_data_od(monkeypatch: pytest.MonkeyPatch):
    order: list[str] = []
    monkeypatch.setattr(
        browser_module,
        "_type_masked_date",
        lambda _page, field, _target: order.append(field),
    )
    monkeypatch.setattr(browser_module, "_verify_date_range", lambda *_args: None)
    monkeypatch.setattr(browser_module, "_wait_for_results", lambda *_args: None)
    page: Any = MagicMock()
    _set_date_range(page, date(2027, 12, 8), date(2027, 12, 29))
    assert order == ["DataDo", "DataOd"]


def test_rejects_clamped_date_range(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(browser_module, "_type_masked_date", lambda *_args: None)
    page: Any = MagicMock()
    boxes = {
        'input[name="DataOd"]': stub_date_box("25.11.2026"),
        'input[name="DataDo"]': stub_date_box("29.12.2027"),
    }
    page.locator.side_effect = lambda selector: boxes[selector]
    with pytest.raises(DownloadError, match="DataOd"):
        _set_date_range(page, date(2027, 12, 8), date(2027, 12, 29))


def test_search_waits_for_matching_week(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(browser_module, "_type_masked_date", lambda *_args: None)
    page: Any = MagicMock()
    page.locator.side_effect = lambda selector: stub_date_box(
        "08.12.2027" if "DataOd" in selector else "29.12.2027"
    )
    _set_date_range(page, date(2027, 12, 8), date(2027, 12, 29))
    page.wait_for_function.assert_called_once()
    predicate, kwargs = (
        page.wait_for_function.call_args[0][0],
        page.wait_for_function.call_args[1],
    )
    assert "Brak danych" in predicate
    assert "Data Zajęć" in predicate
    assert kwargs["arg"] == ["2027-12-08", "2027-12-29"]


def test_search_timeout_reports_missing_results():
    page: Any = MagicMock()
    page.wait_for_function.side_effect = PlaywrightTimeoutError("timeout")
    with pytest.raises(DownloadError, match="wyników"):
        _wait_for_results(page, date(2026, 12, 14), date(2026, 12, 20))


def stub_date_box(value: str) -> MagicMock:
    box = MagicMock()
    box.input_value.return_value = value
    return box


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
