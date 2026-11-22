# plan-downloader

Drive Firefox to download the study-plan PDF (login with 2FA included).

## Usage

```sh
plan-downloader <username> <YYYY-MM-DD-from> <YYYY-MM-DD-to> <output.pdf>
```

Prompts for the password and the one-time 2FA code, so secrets never land
in shell history. Pass `--headed` to watch the browser.

## Record a manual run

```sh
task -d apps/plan-downloader browsers
task -d apps/plan-downloader record -- <login-url>
```

Paste the generated Python back with secrets redacted.
