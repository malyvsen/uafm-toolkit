# plan-parser

Pure library that turns Polish university study-plan PDFs into typed events.

## Usage

```python
from pathlib import Path

from plan_parser import available_weeks, events_for_week, parse_pdf

events = parse_pdf(Path("plan.pdf").read_bytes())
print(available_weeks(events))  # e.g. ["2026-10-19", "2026-10-26"]
week = events_for_week(events, "2026-10-19")
```
