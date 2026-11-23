"""Drive Firefox through login, date selection, and PDF download."""

from datetime import date
from pathlib import Path

from playwright.sync_api import Page, TimeoutError, sync_playwright

from plan_downloader.auth import Credentials, generate_otp, load_credentials


class DownloadError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


def download_timetable(
    date_from: date,
    date_to: date,
    *,
    headed: bool = False,
    credentials: Credentials | None = None,
) -> bytes:
    """Log in with .env credentials and return the PDF for the date range."""
    resolved = credentials or load_credentials()
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=not headed)
        try:
            page = browser.new_page()
            page.goto("https://dziekanat.uafm.edu.pl/")
            _dismiss_cookies(page)
            _login_with_otp(
                page,
                resolved.username,
                resolved.password,
                generate_otp(resolved.totp_secret),
            )
            _open_plans(page)
            _set_date_range(page, date_from, date_to)
            return _fetch_timetable_pdf(page)
        finally:
            browser.close()


def _dismiss_cookies(page: Page) -> None:
    """Decline non-essential cookies, waiting briefly for the banner to load."""
    try:
        page.get_by_role("button", name="Decline non-essential").click(timeout=5000)
    except TimeoutError:
        pass


def _login_with_otp(page: Page, username: str, password: str, otp: str) -> None:
    """Sign in with username, password, and a one-time 2FA code."""
    page.get_by_role("link", name="Login").click()
    page.get_by_role("textbox", name="Username").fill(username)
    page.get_by_role("textbox", name="Password").fill(password)
    page.get_by_role("button", name="Sign In").click()
    page.get_by_role("textbox", name="One-time code from the").fill(otp)
    page.get_by_role("button", name="Sign In").click()


def _open_plans(page: Page) -> None:
    """Navigate to the class-schedule search page."""
    page.get_by_role("link", name="Plany zajęć").click()


def _set_date_range(page: Page, date_from: date, date_to: date) -> None:
    """Enter both dates keystroke by keystroke, then run the search."""
    page.keyboard.press("Escape")
    _type_masked_date(page, "DataOd", date_from)
    _type_masked_date(page, "DataDo", date_to)
    page.get_by_role("link", name="Szukaj").click()


def _type_masked_date(page: Page, field: str, target: date) -> None:
    """Type a date the way the masked widget expects: raw DDMMYYYY digits."""
    box = page.locator(f'input[name="{field}"]')
    box.click()
    box.press("ControlOrMeta+A")
    box.press("Delete")
    box.press_sequentially(format_date_for_typing(target), delay=30)
    box.press("Tab")
    if not box.input_value().strip():
        raise DownloadError(f"Nie udało się wpisać daty w pole {field}.")


def _fetch_timetable_pdf(page: Page) -> bytes:
    """Click the PDF export and return the downloaded bytes."""
    with page.expect_download() as download_info:
        page.get_by_role("link", name="Zapisz jako PDF").click()
    download = download_info.value
    if download.failure() is not None:
        raise DownloadError(f"Nie pobrano pliku: {download.failure()}.")
    data = Path(str(download.path())).read_bytes()
    if not data:
        raise DownloadError("Pobrany plik jest pusty.")
    return data


def format_date_for_typing(target: date) -> str:
    """Format a date as the digit string the masked widget accepts."""
    return f"{target:%d%m%Y}"
