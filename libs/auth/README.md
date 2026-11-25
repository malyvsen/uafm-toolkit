# auth

Library that loads UAFM credentials from `.env` and generates TOTP login codes.

## Usage

```python
from auth import current_code, load_credentials

print(current_code())  # e.g. "123456"
print(load_credentials().username)
```
