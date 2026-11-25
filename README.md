# uafm-toolkit

Makes life easier for students of [UAFM](https://uafm.edu.pl/).

## Development

Start with:

```sh
task init
```

Generate timetables:

```sh
task -d apps/week-view run --
task -d apps/overlap-view run --
```

Print the current login code (also copied to the clipboard):

```sh
task -d apps/otp generate
```

Check everything:

```sh
task check
```
