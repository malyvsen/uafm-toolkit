# otp

CLI that prints the current login code and copies it to the clipboard.

## Usage

```sh
task -d apps/otp generate
```

The code comes from `.env` (see `libs/auth`) and is valid for ~30 seconds.
When no clipboard backend is available (e.g. missing `xclip`), the code is
still printed and only a warning is shown.
