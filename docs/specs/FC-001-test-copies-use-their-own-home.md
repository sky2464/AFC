# FC-001 — Test copies use their own home

Size: S · Status: in progress · Started: 2026-10-24 · Done: -

Finding: 1.

## Goal

A second copy of Flight Control (a test or developer copy) must never write into the user's real
`~/.A-FC`. Today that depends on typing `AFC_HOME=…` every time; one missed prefix sent the whole
php-vuln-checker test into the real workspace and the real code folder.

## You'll know it works when

- When a copy has a home file set, then `claude` started there plainly uses that home, with no prefix.
- When the home in use isn't `~/.A-FC`, then Claude's start-up context says so (`The workspace is a
  test home <path>`); the welcome the user sees is unchanged.
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
- Welcome: `afc/hooks/session_start.py` tells Claude about a home that isn't the default, in the
  context only. A visible line was tried and dropped (see Decisions).
- CONTRIBUTING: replace the `AFC_HOME=… claude` instructions with `sh bin/afc home set …` once.

## Slices

- [x] 1. Launcher reads `.afc-home` — you'll check it by setting a home in a scratch copy and seeing
      `sh bin/afc home` report `file` (tests: env wins, file used, default when missing, bad path is
      a plain error)
- [x] 2. `home set|clear` commands and `.gitignore` entry — you'll check it by setting and clearing a
      home and seeing `git status` stay clean (tests in `tests/test_cli_home.py`)
- [x] 3. Claude knows about a test home — you'll check it by `sh bin/afc hook session_start` in the
      test copy: the context names the home, the welcome message doesn't (tests in
      `tests/test_session_start.py`)
- [ ] 4. CONTRIBUTING and README developer notes updated — you'll check it by following them on a
      fresh test copy

## Decisions

- 2026-10-24: The test home goes in Claude's context only, not the welcome. Only test copies set
  one, `.afc-home` already removes the forgotten-prefix risk, and a visible line wouldn't catch the
  case that went wrong (a copy with no home set using the real `~/.A-FC`; that belongs to FC-012).

## Shipped
