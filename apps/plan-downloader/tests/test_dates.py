"""Date formatting: the masked widget accepts raw DDMMYYYY digits."""

from datetime import date

from plan_downloader.browser import format_date_for_typing


def test_november_date_matches_manual_typing():
    assert format_date_for_typing(date(2026, 11, 23)) == "23112026"


def test_single_digit_day_and_month_are_zero_padded():
    assert format_date_for_typing(date(2026, 1, 5)) == "05012026"
