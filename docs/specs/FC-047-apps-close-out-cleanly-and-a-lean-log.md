# FC-047 — Apps close out cleanly, and a lean log

Size: M · Status: in progress · Started: 2026-10-26 · Done: -

Found on 2026-10-26, comparing this plan with AgToosa's and running `sh bin/afc check`.

- The health check reports that php-vuln-checker has finished slices but `architecture.md` is still the
  empty template. That is finding #6 again, which FC-006 was meant to close: the check warns later, but
  nothing stops a spec from finishing without it.
- php-vuln-checker's plan has an empty Goal although FC-004 added `plan goal` and the plan was reshaped
  on 2026-10-23 after its intent changed. `plan start` does not ask for one.
- A project's plan does not say, in one line, where the project stands (profile, remote, last slice).
- The Update log is about 105 of the plan's 225 lines, mostly "started" and "done" pairs that repeat
  the Done table and the spec header. `LOG_KEEP` in `afc/plan.py` is 100, so the plan is always long.
- A few rows do carry what exists nowhere else: "FC-009 closed, target not met (46,010 against
  24,490)", "FC-018 done: helpers 7.0→2.0". They sit among the noise, so they are hard to find, and
  FC-045's Outcome column will hold that kind of fact from now on.
- Nothing limits how long a plan can grow, so the fix would slowly wear off.

## Goal

A spec in a user's app cannot be started with no goal or finished with the architecture notes still
empty; the plan answers "where are we" in one computed line; and the plan's log keeps only what cannot
be worked out elsewhere, while the full event trail is kept in the workspace.

## Reaches the apps

Yes, this one is for the apps. It changes what `plan start` and `plan done` ask of a user's project,
what `afc plan` shows, and how long a project's master plan grows (`afc/cli_plan.py`, `afc/plan.py`,
`afc/cli_health.py`, `afc/registry.py`).

## You'll know it works when

- A1. On a scratch project with a ticked slice and the bare `architecture.md` template, `plan done
  S-001` stops with one plain sentence; after `architecture.md` has real content it goes through.
- A2. On a scratch project with an empty Goal, `plan start S-001` stops with one plain sentence that
  says to set the goal (`plan goal "<one line>"`); with a goal it starts.
- A3. `sh bin/afc plan` on an active project shows a `where` line made from the registry: profile,
  remote, last slice and the code folder's name. Flight Control's own plan has none.
- A4. `plan add`, `start` and `done` no longer write Update log rows; goal, rename, move, drop, park,
  release and decisions still do. The log keeps the newest 20 rows, older ones archived as today.
- A5. Every plan event, including the ones no longer in the log, is appended to `events.jsonl` in the
  project's workspace (for Flight Control's own plan, in the Flight Control home folder, outside the
  repository). Each line is one JSON object: date, event, spec.
- A7. A one-time cleanup of Flight Control's own log: every "started"/"done"/"added" row is written to
  `events.jsonl` first, then removed from the plan; rows that carry a number or a reason are kept
  (and, once FC-045 is done, copied into that spec's Outcome). The log ends under 30 rows and the
  plan under 140 lines, with nothing lost: the count of events in the file equals the rows removed.
- A8. `sh bin/afc check` says when a plan is over 150 lines or its Update log over 30 rows, names the
  longest section in one plain sentence, and offers `plan tidy`, which does what A7 did to that plan
  and nothing else.
- A6. On a scratch copy of php-vuln-checker, `check` stops reporting `architecture_empty` once the file
  is filled, and its `plan` shows the `where` line.

## Out of scope

Writing the architecture notes for the user (Claude fills them from the code, as before). Editing the
real php-vuln-checker. Showing the events file in the welcome. Reading the events file back anywhere.

## Design notes

- `cmd_done` and `cmd_start` call the same comparison `_architecture_problems` uses (the file against
  the template, whitespace aside). Flight Control's own plan skips both checks: it has no
  `architecture.md`, and its Goal is set.
- Before dropping the started/done rows, search for readers of them (`grep "started"` over `afc/` and
  the skills); the only known consumer is the history in the plan itself.
- `log()` in `afc/plan.py` splits into `event(...)` (writes `events.jsonl`) and `log(...)` (the plan row);
  `cmd_add`, `cmd_start`, `cmd_done` call `event` only.
- The older rows already in the log stay; compaction moves them to the yearly archive as today.
- What counts as "carries a fact": a row with a digit run of 3 or more, an arrow, "target", "closed",
  "renamed" or "dropped". Everything else is routine. The list is shown with `plan tidy --show` before
  anything is removed.
- Order of writes in `plan tidy`: append to `events.jsonl`, then rewrite the plan, with the plan's
  undo record from `compact` so a failure leaves both as they were.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Done needs real architecture notes — you'll see it by a scratch project's `plan done` stopped with
      the bare template and passing once the file has content (proves A1)
- [x] 2. Start needs a goal — you'll see it by a scratch project's `plan start` stopped with an empty Goal
      and passing with one (proves A2)
- [x] 3. Where we are — you'll see it by `sh bin/afc plan` on a scratch active project showing the line
      (proves A3)
- [ ] 4. A short log and an event file — you'll see it by a scratch plan after add, start and done showing no
      new log rows and three lines in `events.jsonl`, and a goal change showing a row (proves A4, A5)
- [ ] 5. Clean up the log, and keep it clean — you'll see it by `plan tidy --show` and `plan tidy` on a
      scratch copy of Flight Control's plan (rows to `events.jsonl`, fact rows kept, plan shorter,
      counts matching) and `check` flagging a scratch plan padded past 150 lines (proves A7, A8)
- [ ] 6. Live on a copy of the app that was flagged — you'll see it by a scratch copy of php-vuln-checker
      (own registry and workspace) with its health problem gone after the file is filled (proves A6)

## Tasks

Slice 1:
- `afc/cli_health.py`: make `_architecture_problems`' comparison a shared helper.
- `afc/cli_plan.py` `cmd_done`: refuse on a project plan when the helper says "bare template".

Slice 2:
- `afc/cli_plan.py` `cmd_start`: refuse on a project plan when the Goal is empty.

Slice 3:
- `afc/cli_plan.py` `cmd_plan`: add `where` from `registry`.

Slice 4:
- `afc/plan.py`: `event(...)`, `LOG_KEEP = 20`; `afc/cli_plan.py`: use `event` in add/start/done.

Slice 5:
- `afc/cli_plan.py`: `tidy` (with `--show`); `afc/cli_health.py`: `plan_too_long`.
- Run it on `docs/master-plan.md` last, in a commit of its own.

Slice 6:
- Copy php-vuln-checker's plan into a scratch workspace, fill the file, run `check`, write the result in
  Decisions. Never use the real project.

## Decisions

## Shipped
