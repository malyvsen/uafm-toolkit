# week-view

CLI that generates PNG timetables from the study plan.

## Usage

```sh
task run --
task run -- --date-from 2026-10-01
task run -- --date-from 2026-10-01 --date-to 2026-10-31
task run -- --date-from 2026-10-01 --date-to 2026-10-31 --output-dir timetables
```

Without dates, the current week plus the next one is generated. Explicit
dates expand to full weeks: `--date-from` snaps back to the Monday on or
before it and `--date-to` snaps forward to the Sunday on or after it, so
passing just one of them generates the single week containing that date.
Credentials come from `.env` (see `libs/plan-downloader`). Everything stays
in memory: only `<output-dir>/plan-<MONDAY>.png` files are written (default
output dir `~/Downloads`).
