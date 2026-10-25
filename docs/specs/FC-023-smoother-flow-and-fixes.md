# FC-023 — Smoother flow and welcome fixes

Size: S · Status: in progress · Started: 2026-10-25 · Done: -

Finding U8: `sh bin/afc maintain` with no argument printed only "Missing state." Finding U9: the first welcome question was sometimes asked twice.

## Goal

Fewer wasted turns at session start and clearer maintenance commands, without changing what maintenance mode means.

## You'll know it works when

- `sh bin/afc maintain` with no argument returns status (same as `maintain status`).
- Session context tells Claude not to repeat the welcome when the user answers 1 or 2; `afc-start` matches.
- Tests cover bare `maintain` and the updated context line.

## Slices

- [x] 1. Default maintain to status — you'll check it by `tests/test_maintain.py` (`test_bare_maintain_shows_status`)
- [x] 2. No duplicate welcome — you'll check it by `tests/test_session_start.py` and the `afc-start` skill text

## Decisions
