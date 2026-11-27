# gcal-sync

CLI that pushes the study plan to Google Calendar from your laptop. No server.

## Setup (once)

1. Create a Desktop-app OAuth client in Google Cloud Console, enable the Calendar API.
2. Fill in `.env` (see `.env.example`):
   ```sh
   GCAL_CLIENT_ID=
   GCAL_CLIENT_SECRET=
   ```
   Or point at the downloaded JSON: `--client-secrets client_secrets.json`.
3. Authorize (opens a browser, caches a refresh token outside the repo):
   ```sh
   task auth
   ```

## Usage

```sh
task run --
task run -- --date-from 2026-10-01 --date-to 2026-10-31
task run -- --calendar-name "UAFM Plan" --dry-run
```

Without dates, the remaining teaching period is synced. Events live in a dedicated calendar (default `UAFM Plan`,
created on first run), each run inserts new events, updates changed ones,
and deletes removed ones. Re-running is a no-op. Past days are left alone.
