"""Download study-plan PDFs by driving Firefox."""

from plan_downloader.auth import Credentials, CredentialsError
from plan_downloader.browser import DownloadError, download_timetable

__all__ = [
    "Credentials",
    "CredentialsError",
    "DownloadError",
    "download_timetable",
]
