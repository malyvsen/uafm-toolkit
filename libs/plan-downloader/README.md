# plan-downloader

Library that drives Firefox to download the study-plan PDF, logging in with credentials from `.env` and an auto-generated TOTP code.

## Setup

Copy the repo-root `.env.example` to `.env` and fill in `UAFM_USERNAME`, `UAFM_PASSWORD`, and `UAFM_TOTP_SECRET` (the authenticator secret from 2FA enrollment, not a one-time code).
Verify the authenticator wiring with:

```sh
task otp
```

## Usage

```python
from datetime import date
from pathlib import Path

from plan_downloader import download_timetable

Path("plan.pdf").write_bytes(download_timetable(date(2026, 10, 1), date(2026, 10, 31)))
```

## Record a manual run

```sh
task browsers
task record -- <login-url>
```

Paste the generated Python back with secrets redacted.
