# FC-001 — Test copies use their own home

Size: S · Status: next · Started: - · Done: -

Finding: 1.

## Goal

A second copy of Flight Control (a test or developer copy) must never write into the user's real
`~/.A-FC`. Today that depends on typing `AFC_HOME=…` every time; one missed prefix sent the whole
php-vuln-checker test into the real workspace and the real code folder.

## You'll know it works when

- When a copy has a home file set, then `claude` started there plainly uses that home, with no prefix.
- When the home in use isn't `~/.A-FC`, then the welcome says so on its own line: `Test home: <path>`.
- When nothing is set, then everything behaves exactly as today.
- When `AFC_HOME` is given explicitly, then it still wins over the home file.

## Out of scope

Separate add-on settings per copy; containers.

## Design notes

- Home file: `.afc-home` at the copy's root holding one absolute path, git-ignored (add to
  `.gitignore`). `bin/afc` reads it when `AFC_HOME` is unset and exports `AFC_HOME`. All of Flight
  Control's code already reads `AFC_HOME`, so only the launcher changes.
- New commands in a new module `afc/cli_home.py` (`afc/cli.py` is at 483 of 500 lines):
  `sh bin/afc home` (shows the home in use and where it came from: `env`, `file` or `default`),
  `sh bin/afc home set <path>`, `sh bin/afc home clear`. Changing it needs maintenance mode, since
  the file lives in the Flight Control folder.
- Welcome: `afc/hooks/session_start.py` adds the `Test home:` line to the message when the home isn't
  the default, so a mixed-up start is visible at once.
- CONTRIBUTING: replace the `AFC_HOME=… claude` instructions with `sh bin/afc home set …` once.

## Slices

- [ ] 1. Launcher reads `.afc-home` — you'll check it by setting a home in a scratch copy and seeing
      `sh bin/afc home` report `file` (tests: env wins, file used, default when missing, bad path is
      a plain error)
- [ ] 2. `home set|clear` commands and `.gitignore` entry — you'll check it by setting and clearing a
      home and seeing `git status` stay clean (tests in `tests/test_cli_home.py`)
- [ ] 3. Welcome shows `Test home:` — you'll check it by starting `claude` in the test copy (tests in
      `tests/test_session_start.py`)
- [ ] 4. CONTRIBUTING and README developer notes updated — you'll check it by following them on a
      fresh test copy

## Decisions

## Shipped
