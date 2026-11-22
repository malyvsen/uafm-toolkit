"""Drive Firefox through login, date selection, and PDF download."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

from playwright.sync_api import Page, TimeoutError, sync_playwright


class DownloadError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


def download_timetable(
    username: str,
    password: str,
    otp_provider: Callable[[], str],
    date_from: date,
    date_to: date,
    output: Path,
    *,
    headed: bool = False,
) -> Path:
    """Log in with 2FA, set the date range, and save the timetable PDF."""
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=not headed)
        try:
            page = browser.new_page()
            page.goto("https://dziekanat.uafm.edu.pl/")
            dismiss_cookies(page)
            login_with_otp(page, username, password, otp_provider)
            open_plans(page)
            set_date_range(page, date_from, date_to)
            save_timetable_pdf(page, output)
        finally:
            browser.close()
    return output


def dismiss_cookies(page: Page) -> None:
    """Decline non-essential cookies, waiting briefly for the banner to load."""
    try:
        page.get_by_role("button", name="Decline non-essential").click(timeout=5000)
    except TimeoutError:
        pass


def login_with_otp(
    page: Page, username: str, password: str, otp_provider: Callable[[], str]
) -> None:
    """Sign in with username, password, and a one-time 2FA code."""
    page.get_by_role("link", name="Login").click()
    page.get_by_role("textbox", name="Username").fill(username)
    page.get_by_role("textbox", name="Password").fill(password)
    page.get_by_role("button", name="Sign In").click()
    otp = otp_provider()
    page.get_by_role("textbox", name="One-time code from the").fill(otp)
    page.get_by_role("button", name="Sign In").click()


def open_plans(page: Page) -> None:
    """Navigate to the class-schedule search page."""
    page.get_by_role("link", name="Plany zajęć").click()


def set_date_range(page: Page, date_from: date, date_to: date) -> None:
    """Enter both dates keystroke by keystroke, then run the search."""
    page.keyboard.press("Escape")
    type_masked_date(page, "DataOd", date_from)
    type_masked_date(page, "DataDo", date_to)
    page.get_by_role("link", name="Szukaj").click()


def type_masked_date(page: Page, field: str, day: date) -> None:
    """Type a date the way the masked widget expects: raw DDMMYYYY digits."""
    box = page.locator(f'input[name="{field}"]')
    box.click()
    box.press("ControlOrMeta+A")
    box.press("Delete")
    box.press_sequentially(format_date_for_typing(day), delay=30)
    box.press("Tab")
    if not box.input_value().strip():
        raise DownloadError(f"Nie udało się wpisać daty w pole {field}.")


def save_timetable_pdf(page: Page, output: Path) -> None:
    """Click the PDF export and save the download to output."""
    with page.expect_download() as download_info:
        page.get_by_role("link", name="Zapisz jako PDF").click()
    download = download_info.value
    download.save_as(output)
    if not output.exists():
        raise DownloadError(f"Nie pobrano pliku: {output}.")


def format_date_for_typing(day: date) -> str:
    """Format a date as the digit string the masked widget accepts."""
    return f"{day:%d%m%Y}"
