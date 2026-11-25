# overlap-view

CLI that generates a single typical-week PNG from the study plan, overlapping
all weeks in the range into Monday-to-Friday columns.

## Usage

```sh
task run --
task run -- --date-from 2026-10-01 --date-to 2027-01-31
task run -- --date-from 2026-10-01 --date-to 2027-01-31 --output-dir timetables
```

Without dates, the remaining UAFM full-time teaching period is used (see
`semester.py`). Credentials come from `.env` (see `libs/auth`).
Everything stays in memory: only one PNG is written (default output dir
`~/Downloads`): `plan-<YEAR>-<YEAR+1>-semestr-<kind>.png` for default runs
(e.g. `plan-2026-2027-semestr-zimowy.png`, `plan-2026-2027-semestr-letni.png`,
from the earliest event's semester) and `plan-<FROM>-<TO>.png` for custom
`--date-from/--date-to` runs (e.g. `plan-2026-10-19-2026-10-30.png`, from
actual event min/max dates).

## Reading the image

Each block spans the merged time of its classes; a real break always splits
the block. A block holds one section per colliding class: subject lines plus
time variants sorted by start with weekly counts (`14:00–15:25 ×4`). There are
no room lines. A small chip in the class color marks each section instead of a
shared spine. Solid blocks happen every week, pale ones are rare; a combined
block uses its most solid member's opacity.
