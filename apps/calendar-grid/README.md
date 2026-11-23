# calendar-grid

CLI that renders all weeks of a study-plan PDF as shareable PNG timetables.

## Usage

```sh
task run -- plan.pdf
task run -- --date-from 2026-10-01 --date-to 2026-10-31 plan.pdf
```

With `--date-from` and `--date-to`, the PDF is downloaded first using
credentials from `.env` (see `libs/plan-downloader`), then rendered.
Pass `--headed` to watch the download browser.
Each Monday in the plan produces `<stem>-<MONDAY>.png` next to the PDF
(e.g. `plan-2026-10-19.png`).
