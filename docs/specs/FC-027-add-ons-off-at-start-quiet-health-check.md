# FC-027 — Add-ons off at start, quiet health check

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Found on 2026-10-25 while testing the v0.03a one-click update on a scratch copy of the previous
`main` (dd75b26 → v0.03a, 1034 tests passing). The update worked, but its summary said the health
check "found 28 problem(s) to look at" and listed eight account add-ons by name. The same day an
`A-FC-test` session answered "hi" with "a health check found 30 problems" and used 75,950 tokens.

Found while speccing: neither the real `A-FC` folder nor `A-FC-test` has any add-on switched off.
`.claude/settings.local.json` has no `afcBlockedAddons` and no `enabledPlugins: false`. The
toolkit-layers design switches add-ons off only on `sh bin/afc repair`, which nothing runs for the
user, yet `check` says "Flight Control switched off <name> …" as if it were done. So all 28
account add-ons load in every Flight Control session, which the toolkit-layers design meant to
prevent, and every welcome reports them as problems.

## Goal

Add-ons that aren't on Flight Control's allowed list are really switched off in its sessions,
without the user running anything. The health check, the welcome and the update summary speak up
only about what needs the user, in a line or two.

## You'll know it works when

- Starting a session in a copy with enabled add-ons that aren't allowed writes them to
  `enabledPlugins: false` and `afcBlockedAddons` in `.claude/settings.local.json`, and the welcome
  says once, in one line, that N add-ons will be off from the next start. A second start says
  nothing about add-ons.
- After that, `sh bin/afc check` reports no add-on problems, and `ok` is true when nothing else is
  wrong. Add-ons the user turned off themselves, and allowed ones, are never touched.
- Before anything is switched off, `check` describes it in future tense ("isn't on the allowed
  list; Flight Control switches it off at the next start"), never as done.
- The after-update summary is at most three sentences: what was updated, then "Everything checks
  out." or how many things need a look with the first one in plain words. Add-ons are one counted
  phrase, never listed by name.
- The first reply to "hi" in a fresh session on the real `A-FC` folder uses noticeably fewer
  tokens than the 75,950 seen today, measured with `docs/measurements/token_usage.py` before and
  after, and the number is written in Decisions.

## Out of scope

Changing what is on the allowed list (`afc-addons.json`). Uninstalling or changing add-ons at the
account level; they keep working outside Flight Control. Maintenance-mode sessions get the same
switch-off, nothing more. Other problem kinds keep their meaning.

## Design notes

- **When.** The SessionStart hook already runs `find_problems` for its health line. When that
  finds `addon_not_allowed` or `addon_unblock` problems, it applies the same add-on part of
  `repair` (`block_addons`, with the settings undo on failure) and drops them from the count. It
  must never block or break the welcome: any error leaves settings as they were and adds nothing.
- **Takes effect next start.** Claude Code reads `enabledPlugins` at launch, so the welcome line
  says "from the next start". That is why it shows once: the next start finds nothing to do.
- **Quiet after.** Once switched off, `claude plugin list --json` reports them `enabled: false` in
  that folder (checked in the toolkit-layers design), so `addons.blocked` no longer lists them; no
  extra filtering is needed. A test pins this with a fake plugin list.
- **Summary shape.** `afc/update_apply.py` groups add-on kinds into one counted phrase, shows the
  first other problem by its detail plus "and N more", and keeps the full list in the JSON `check`
  field.

## Slices

- [x] 1. Honest check wording — you'll check it by `tests/test_cli_health.py`: a not-yet-switched
      add-on's detail says it will be switched off at the next start; one already in
      `afcBlockedAddons` and reported disabled gives no problem
- [x] 2. Switch off at session start — you'll check it by `tests/test_session_start.py` cases: not
      allowed and enabled → written to settings, one welcome line, count excludes them; second start
      → no line; user's own `false` entries and allowed add-ons untouched; a settings write error →
      settings unchanged and the welcome still shown
- [ ] 3. Short update summary — you'll check it by `tests/test_update_apply.py` cases for a clean
      check, add-ons only (one counted phrase, no names) and one other problem plus add-ons ("and N
      more"), each three sentences or fewer
- [ ] 4. Live check — you'll check it by starting two sessions on the real `A-FC` folder: the first
      switches the 28 add-ons off, the second's welcome mentions no add-ons, and the first-reply
      token count before and after is written in Decisions

## Decisions

- 2026-10-25: Add-ons not on the allowed list are switched off automatically at session start,
  not only on `repair` (user's choice).

## Shipped
