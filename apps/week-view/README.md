# week-view

CLI that generates PNG timetables from the study plan.

## Usage

```sh
task run --
task run -- --date-from 2026-10-01 --date-to 2026-10-31
task run -- --date-from 2026-10-01 --date-to 2026-10-31 --output-dir timetables
```

Without dates, the current week plus the next one is generated. Credentials
come from `.env` (see `libs/plan-downloader`). Everything stays in memory:
only `<output-dir>/plan-<MONDAY>.png` files are written (default output dir
`~/Downloads`).
