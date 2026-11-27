# semester

Library that maps a date to its UAFM teaching period and semester identity.

## Usage

```python
from semester import semester_identity, semester_remainder

print(semester_remainder(date(2026, 10, 21)))
print(semester_identity(date(2026, 10, 21)))
```
