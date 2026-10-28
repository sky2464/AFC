    # FC-055 — Calm welcome, honest update check

Size: M · Status: in progress · Started: 2026-10-27 · Done: -
Area: updates (and welcome wording)

Found on 2026-10-27 alongside FC-054. The welcome every session prints calls Flight Control "your
AI architect, project manager and security officer in one" (`INTRO` in
`afc/hooks/session_start.py`, quoted twice in `README.md`). Security-flavoured words in the very
first line a session sees can make an AI tool's safety layer treat an ordinary build session as
security work. The same day, `sh bin/afc update --check` answered from a saved look up to a day
old instead of looking now, and `sh bin/afc update` refused a copy whose only "edits" were new
untracked files with "has local edits", which sends the user looking for changes they never made.

Research (2026-10-27): `update.check` (`afc/update.py`) only looks at origin when `_due` says the
day has passed; its only caller is `cmd_update --check` (`afc/cli_version.py`). The welcome uses
`update.offer`, which keeps its own daily claim and never waits. `update_apply.apply`
(`afc/update_apply.py`) refuses on any non-empty `git status --porcelain`, untracked (`??`) lines
included, with one message for both.

## Goal

The first line of every session introduces Flight Control in calm, brand-safe words. When the user
asks "is there an update?", Flight Control looks now and says what it found. When an update is
refused because of stray files, the reason names those files as new, untracked ones.

## Reaches the apps

Yes. The welcome (`afc/hooks/session_start.py` `INTRO`) is printed at the start of every session
in every project, and `sh bin/afc update` / `update --check` are the commands every user runs to
stay current.

## You'll know it works when

- A1. The `INTRO` string in `afc/hooks/session_start.py` reads "your AI architect, project manager
  and calm co-pilot in one" and contains 0 of the words security, cyber, officer, guard, vuln;
  `rg -i "security officer"` across the repo (outside `docs/specs/archive/`) finds 0 lines,
  `README.md` included. A live session start prints the new line.
- A2. On a non-developer copy (on `main`, maintenance off), two `sh bin/afc update --check` runs a
  few seconds apart each look at origin: `checked_at` in the workspace's `update.json` changes on
  both runs. The welcome's `offer` still looks at most once a day (`checked_at` unchanged by a
  second session start within the day).
- A3. On a copy on `main` with only an untracked file added (`git status --porcelain` shows only
  `??` lines), `sh bin/afc update` refuses with a reason that says the copy has new files git is
  not tracking and suggests putting them away or removing them. With a tracked file edited, the
  reason is still "Flight Control's own copy has local edits, so nothing was changed; put them
  away first." Nothing is changed in either case.

## Out of scope

Proving how any AI vendor's safety classifier scores the welcome, or tuning its thresholds: this
spec proves the wording only. Renaming `php-vuln-checker` or any user project. Changing `DAY` or
the welcome's once-a-day update offer. Anything in FC-054 (maintenance-mode switch, deliver in
maintenance mode). Removing or moving untracked files on the user's behalf.

## Assumptions to confirm

- [x] "your AI architect, project manager and calm co-pilot in one" is the new line; it matches the
  "calm co-pilot" voice in `CLAUDE.md` and uses none of security, cyber, officer, guard, vuln.
  The README heading changes to the same words.
- [x] A developer copy (on `dev`, or maintenance mode on) keeps answering `update --check` with
  "none" without looking, as today; A2 is proven on a copy on `main` (a scratch clone or worktree).

## Design notes

- Slice 1 is a text change only: `INTRO` in `afc/hooks/session_start.py`, the README heading and
  the README's quoted welcome block. Keep the second `INTRO` line ("Spec-driven from day one: …")
  as it is. `docs/specs/archive/` keeps its history unchanged.
- Slice 2: `update.check` skips `_due` and always calls `refresh` for the explicit `--check`; the
  module docstring says "at most once a day" of the welcome only. `offer`, `_due` and `DAY` stay
  as they are; `check` is called from nowhere but `cmd_update --check`. The look keeps its
  `TIMEOUT` budget and still says "none" when offline.
- Slice 3: in `update_apply.apply`, split the porcelain lines. If every non-empty line starts with
  `??`, refuse with the untracked message (it may name up to a few of the paths); otherwise keep
  today's "local edits" message word for word. Refusal still changes nothing.
- No new core test file: Flight Control keeps five tests on guards (FC-030). Prove with live runs:
  a session start, two `update --check` runs on a `main` scratch copy with `update.json` read
  between them, and `update` on that copy with an untracked file, then with a tracked edit.

## Slices

- [x] 1. Calm SessionStart wording — you'll see it by a live session start printing "your AI
      architect, project manager and calm co-pilot in one" and `rg -i "security officer"` outside
      the spec archive returning 0 lines (proves A1)
- [x] 2. --check always refreshes — you'll see it by two `sh bin/afc update --check` runs on a
      `main` scratch copy, seconds apart, each changing `checked_at` in `update.json` (2 of 2
      changed), while a second session start the same day leaves it unchanged (proves A2)
- [ ] 3. Clearer refuse for untracked-only dirt — you'll see it by `sh bin/afc update` on that copy
      with one untracked file refusing with the untracked-files reason, then with one tracked edit
      refusing with the "local edits" reason, and `git status --short` identical before and after
      both runs (proves A3)

## Tasks

Slice 1:
- `afc/hooks/session_start.py`: `INTRO` first line → "your AI architect, project manager and calm
  co-pilot in one".
- `README.md`: heading and quoted welcome to the same words.
- `rg -i "security officer"` (excluding `docs/specs/archive/`) → 0; live session start.

Slice 2:
- `afc/update.py`: `check` always calls `refresh` (no `_due` gate); docstring says the once-a-day
  look is the welcome's.
- `afc/cli_version.py`: `--check` help text says it looks now.
- Live: scratch copy on `main`, two `--check` runs, read `update.json` between them; one session
  start to confirm `offer` unchanged.

Slice 3:
- `afc/update_apply.py`: untracked-only (`??`) porcelain → new refusal naming new untracked files
  and suggesting put away or remove; tracked edits → existing message unchanged.
- Live: untracked file, then tracked edit, on the scratch copy; `git status --short` before/after.

## Decisions

## Shipped
