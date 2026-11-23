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
`semester.py`). Credentials come from `.env` (see `libs/plan-downloader`).
Everything stays in memory: only `<output-dir>/plan-overlap-<FROM>-<TO>.png` is written
(default output dir `~/Downloads`).

## Reading the image

Each block spans the merged time of overlapping class instances; a real break
always splits the block. Inside, time variants are sorted by start with weekly
counts (`14:40–17:05 ×3`), then rooms with counts (`sala D -02 ×4`). Solid
blocks happen every week, pale ones are rare. Colliding classes share the
column side by side.
