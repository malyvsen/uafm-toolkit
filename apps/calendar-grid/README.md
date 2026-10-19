# calendar-grid

CLI that renders a single week of a study-plan PDF as a shareable PNG timetable.

## Usage

```sh
calendar-grid plan.pdf -o tydzien.png [--week RRRR-MM-DD]
```

`--week` takes the Monday starting the week. It is optional when the PDF holds
a single week and required when it holds several.
