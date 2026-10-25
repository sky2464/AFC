# FC-027 — Quiet health check after an update

Size: M · Status: next · Started: - · Done: -

Found on 2026-10-25 while testing the v0.03a one-click update on a scratch copy of the previous
`main` (dd75b26 → v0.03a, 1034 tests passing). The update itself worked, but its summary said the
health check "found 28 problem(s) to look at" and listed eight of them: all account add-ons that
Flight Control keeps switched off in its own sessions. Nothing was wrong.

Found while speccing: the same 28 show on every `sh bin/afc check` in the real `A-FC` folder too.
`_addon_problems` in `afc/cli_health.py` reports every enabled add-on that isn't on the allowed
list (`addons.blocked`), whether or not Flight Control has already switched it off
(`session_dirs.blocked_addons`). So `check` is never `ok` for anyone with account add-ons, and
"Flight Control switched off …" is reported as a problem although it is a done fact.

## Goal

A health check, and the update summary built from it, only speaks up about things that need the
user or `repair`. Add-ons Flight Control has already switched off stay quiet; a healthy copy says
so in one line.

## You'll know it works when

- `sh bin/afc check` in a copy whose not-allowed add-ons are already switched off reports no
  add-on problems, and `ok` is true when nothing else is wrong.
- An add-on that is enabled, not allowed and not yet switched off is still one `addon_not_allowed`
  problem, and `sh bin/afc repair` still switches it off.
- The after-update summary is at most three sentences: what was updated, then either "Everything
  checks out." or how many things need a look with the first one in plain words. Add-ons are
  counted in one phrase ("28 add-ons will be switched off in Flight Control sessions"), never
  listed by name.
- Re-running the v0.03a update from a fresh scratch copy gives a summary with no add-on names.

## Out of scope

Changing which add-ons are allowed, or how they are switched off. The other problem kinds
(`missing_access`, `architecture_empty`, …) keep their meaning; only their share of the update
summary changes. The welcome's own wording.

## Design notes

- **Already switched off is not a problem.** In `_addon_problems`, skip a not-allowed add-on whose
  id is in `blocked_addons(root)`. The rest stay `addon_not_allowed`, with the detail in future
  tense: "… isn't on the allowed list; repair switches it off in Flight Control sessions."
- **A fresh copy.** A new clone has no Flight Control settings yet, so its add-ons aren't switched
  off until the first `repair` or session start. That is why the update summary groups all add-on
  kinds into one counted phrase instead of a line each.
- **Summary shape.** `afc/update_apply.py` builds the summary from the check: add-on kinds grouped
  and counted, every other kind by its detail, the first one shown plus "and N more". The full list
  stays in the JSON `check` field for anyone who asks.

## Slices

- [ ] 1. Switched-off add-ons are quiet — you'll check it by `sh bin/afc check` in the real `A-FC`
      folder no longer listing the add-ons Flight Control already switched off, and
      `tests/test_cli_health.py` covering: switched off → no problem; enabled, not allowed, not
      switched off → one problem with the future-tense detail; repair then check → none
- [ ] 2. Short update summary — you'll check it by `tests/test_update_apply.py` cases for a clean
      check ("Everything checks out."), add-ons only (one counted phrase, no names), and one other
      problem plus add-ons ("and N more" past the first), each summary three sentences or fewer
- [ ] 3. Live re-run — you'll check it by repeating the v0.03a update from a fresh scratch copy
      with its own `AFC_HOME`: a summary with no add-on names, then `sh bin/afc check` with no
      add-on problems after `sh bin/afc repair`

## Decisions

## Shipped
