# FC-048 — MM: prefix turns maintenance mode on

Size: S · Status: done · Started: 2026-10-26 · Done: 2026-10-26

Found on 2026-10-26. The user typed `/afc MM: Master plan for each project…` meaning "maintenance mode on,
then this". `/afc` only switched maintenance mode on for `mm` or `mm on` as the whole argument, so the
session ran as an ordinary `/afc`, said maintenance mode was off, and stayed read-only.

## Goal

Typing `/afc MM: <request>` turns maintenance mode on for the session and then handles `<request>` as
Flight Control work, so the user never has to send `/afc mm` first as a separate message.

## Reaches the apps

Not directly. This changes only how `/afc` reads its arguments (`.claude/commands/afc.md`). It does not
touch a user's app, plan or code. It reaches the apps' sessions only in that the same `/afc` command runs
there, so a user who types "MM:" gets what they meant instead of a read-only reply.

## You'll know it works when

- A1. In a session with maintenance mode off, `/afc MM: check the master plan layout` turns it on
  (`sh bin/afc maintain status` says on) and the reply starts with the one-line "Maintenance mode is on"
  message, then handles the request.
- A2. `mm`, `mm on`, `mm off` and `mm status` behave exactly as before.
- A3. "MM" inside a sentence (`/afc what does MM mean`) does not switch anything on. Only a leading
  "MM:" counts, in any letter case.
- A4. With maintenance mode already on, `/afc MM: …` does not repeat the one-line message and goes
  straight to the request.

## Out of scope

Turning maintenance mode on from other commands or from plain chat messages. Changing how the mode is
stored, how long it lasts, or what the guards block. Any change to a user's project.

## Assumptions to confirm

- [x] The command file is the only place `/afc` arguments are read (no code parses them).

## Design notes

- Add one bullet to the "Maintenance mode first" list in `.claude/commands/afc.md`: an argument that
  starts with `MM:` (any case) runs `sh bin/afc maintain on` when the mode is off, says the usual
  one-line message, then continues with the rest of the text as the request. It does not run the
  normal summary.
- Keep the existing rule for a bare `mm`, `mm on`, `mm off` and `mm status`.
- No change to `afc/` code, so no new test (Flight Control keeps five tests on guards, FC-030).

## Slices

- [x] 1. `/afc MM: …` turns the mode on and carries on with the request — you'll see it by typing
  `/afc MM: show the master plan` with the mode off (proves A1, A2, A3, A4)

## Tasks

Slice 1:
- `.claude/commands/afc.md`: add the leading-"MM:" bullet under "Maintenance mode first"; leave the
  `mm` bullets as they are.

## Decisions

- Slice 1, 2026-10-26: added the leading-"MM:" bullet to `.claude/commands/afc.md`. Only that file reads
  `/afc` arguments (`afc/` code just prints "/afc mm" in messages), so the assumption holds. A1 and A4 can
  only be seen in a fresh session, because command files load at session start; they are not yet seen.

## Shipped

Shipped 2026-10-26. Slices: 1. Criteria: 0 of 4 proven.
