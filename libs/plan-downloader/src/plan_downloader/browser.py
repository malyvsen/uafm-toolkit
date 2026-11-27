"""Drive Firefox through login, date selection, and PDF download."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, TimeoutError, sync_playwright

from auth import Credentials, generate_otp, load_credentials


class DownloadError(Exception):
    """A user-facing failure with a ready-to-print Polish message."""


def download_timetable(
    date_from: date,
    date_to: date,
    *,
    on_progress: Callable[[str], None],
    headed: bool = False,
    credentials: Credentials | None = None,
) -> bytes:
    """Log in with .env credentials and return the PDF for the date range."""
    resolved = credentials or load_credentials()
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=not headed)
        try:
            page = browser.new_page()
            on_progress("Otwieranie dziekanatu…")
            page.goto("https://dziekanat.uafm.edu.pl/")
            _dismiss_cookies(page)
            on_progress("Logowanie…")
            _login(page, resolved)
            on_progress("Otwieranie planów zajęć…")
            _open_plans(page)
            on_progress("Wyszukiwanie zajęć…")
            _set_date_range(page, date_from, date_to)
            on_progress("Pobieranie planu…")
            return _fetch_timetable_pdf(page)
        finally:
            browser.close()


def _dismiss_cookies(page: Page) -> None:
    """Decline non-essential cookies, waiting briefly for the banner to load."""
    try:
        page.get_by_role("button", name="Decline non-essential").click(timeout=5000)
    except TimeoutError:
        pass


def _login(page: Page, credentials: Credentials) -> None:
    """Sign in with username, password, and a one-time 2FA code."""
    page.get_by_role("link", name="Login").click()
    page.get_by_role("textbox", name="Username").fill(credentials.username)
    page.get_by_role("textbox", name="Password").fill(credentials.password)
    page.get_by_role("button", name="Sign In").click()
    otp_box = page.get_by_role("textbox", name="One-time code from the")
    try:
        otp_box.wait_for(timeout=15000)
    except TimeoutError:
        raise DownloadError("Nie udało się zalogować. Sprawdź login i hasło.") from None
    devices = _otp_devices(page)
    if not devices:
        if _try_otp(page, otp_box, credentials.totp_secret):
            return
    else:
        for device in devices:
            device.check()
            if _try_otp(page, otp_box, credentials.totp_secret):
                return
    raise DownloadError(
        "Nieprawidłowy kod uwierzytelniający. Sprawdź UAFM_TOTP_SECRET w pliku .env."
    )


def _try_otp(page: Page, otp_box: Locator, totp_secret: str) -> bool:
    """Fill a fresh code and submit it, reporting whether login succeeded."""
    otp_box.fill(generate_otp(totp_secret))
    page.get_by_role("button", name="Sign In").click()
    try:
        page.wait_for_function("!location.hostname.startsWith('auth.')", timeout=10000)
        return True
    except TimeoutError:
        return False


def _otp_devices(page: Page) -> list[Locator]:
    """List OTP device radios, toolkit-enrolled device first."""

    def label(radio: Locator) -> str:
        try:
            text = radio.evaluate("el => el.labels?.[0]?.textContent ?? ''") or ""
            return text.lower()
        except PlaywrightError:
            return ""

    radios = page.get_by_role("radio").all()
    return sorted(radios, key=lambda radio: "uafm-toolkit" not in label(radio))


def _open_plans(page: Page) -> None:
    """Navigate to the class-schedule search page."""
    page.get_by_role("link", name="Plany zajęć").click()


def _set_date_range(page: Page, date_from: date, date_to: date) -> None:
    """Type both dates, confirm the widget kept them, and run the search."""
    page.keyboard.press("Escape")
    # DataDo first: typing DataOd first lets the widget clamp it back to today
    # when it still lies past the old DataDo.
    _type_masked_date(page, "DataDo", date_to)
    _type_masked_date(page, "DataOd", date_from)
    _verify_date_range(page, date_from, date_to)
    page.get_by_role("link", name="Szukaj").click()
    _wait_for_results(page, date_from, date_to)


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


def _verify_date_range(page: Page, date_from: date, date_to: date) -> None:
    """Confirm the masked widget kept both dates instead of clamping them."""
    for field, target in (("DataOd", date_from), ("DataDo", date_to)):
        actual = page.locator(f'input[name="{field}"]').input_value()
        if _digits(actual) != format_date_for_typing(target):
            raise DownloadError(f"Nie udało się ustawić daty w polu {field}.")


def _digits(text: str) -> str:
    """Strip everything but digits so "08.12.2027" matches "08122027"."""
    return "".join(char for char in text if char.isdigit())


def _wait_for_results(page: Page, date_from: date, date_to: date) -> None:
    """Wait until the visible results belong to the requested search.

    The page keeps the previous search on screen until the new one loads,
    so any "Data Zajęć:" row is not enough: require a row inside the
    requested range. ISO dates sort lexicographically, so string comparison
    is sufficient.
    """
    try:
        page.wait_for_function(
            """([fromISO, toISO]) => {
                const text = document.body.innerText ?? "";
                if (text.includes("Brak danych")) return true;
                const rows = text.matchAll(/Data Zajęć:\\s*(\\d{4})\\.(\\d{2})\\.(\\d{2})/g);
                for (const row of rows) {
                    const iso = `${row[1]}-${row[2]}-${row[3]}`;
                    if (iso >= fromISO && iso <= toISO) return true;
                }
                return false;
            }""",
            arg=[date_from.isoformat(), date_to.isoformat()],
            timeout=30000,
        )
    except TimeoutError:
        raise DownloadError(
            "Nie znaleziono wyników wyszukiwania. Spróbuj ponownie."
        ) from None


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
