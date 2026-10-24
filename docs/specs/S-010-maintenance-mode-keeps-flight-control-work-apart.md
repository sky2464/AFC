# S-010 — Maintenance mode keeps Flight Control work apart

Size: L · Status: next · Started: - · Done: -

Findings: the 2026-10-24 mix-up (M1–M10 in the master plan). Priority: before S-001.

## Goal

Work on Flight Control itself and work on a user's project can never be confused. On 2026-10-24 a
session opened in the `A-FC` folder was asked to "build S-001" and "build S-002 on dev" for
Flight Control. Three times it built the php-vuln-checker app instead: it committed an app slice,
created a `dev` branch inside the app, and left six uncommitted files there. Maintenance mode was on
for part of it, but that switch only unlocks editing Flight Control; it doesn't change who the work
is for, so the active project kept winning.

## You'll know it works when

- When maintenance mode is on, then the welcome says `🔧 Maintenance: working on Flight Control
  itself` with the folder and branch, and no project is offered.
- When maintenance mode is on, then any write to a project's code folder or workspace, and any git
  command run in a project folder, is blocked with a plain reason.
- When maintenance mode is on, then "build <id>" and `plan` act on Flight Control's own master plan
  (`docs/master-plan.md`), never on the active project's.
- When `/afc mm` is typed, then maintenance mode turns on for that session; `/afc mm off` turns it
  off. Nothing depends on Claude remembering a convention.
- When a request names a spec ID that isn't in the plan being worked on, or a branch that doesn't
  exist there, then Claude stops and asks one question; it never guesses and never creates a branch
  in an app on its own.
- Flight Control's own specs use `FC-001`, `FC-002`…; project specs keep `S-001`…; "build FC-…"
  outside maintenance mode is answered with "that's a Flight Control spec; turn on maintenance mode
  first?".
- When an interrupted change is undone, then Claude shows `git status` proving it is clean before
  saying so.
- When maintenance work is committed, then it lands on `dev`, or Claude says exactly which branch it
  is on and how to bring it to `dev`.

## Out of scope

Running two Flight Control versions side by side (S-001 covers the test copy's home); production
releases (still the user's own step).

## Design notes

- **Mode, not just a lock.** Today maintenance mode is a file in the workspace home
  (`~/.A-FC/maintain`), so it is global: turning it on in one session unlocks Flight Control edits in
  every session. Make it per session: the hook input carries `session_id`; store
  `~/.A-FC/maintain/<session_id>` and treat a missing file as off. How `sh bin/afc maintain` learns
  the session must be checked against Claude Code's current docs first (hook input carries
  `session_id`; don't assume an environment variable exists). If a command can't know its session,
  fall back to today's global switch and say so.
- **Guard.** `afc/hooks/rules_paths.py`: in maintenance mode, the allowed write area is the Flight
  Control folder only; project code and workspaces are blocked. A new small rule module blocks git
  commands whose `-C <path>` or working folder is a registered project's code folder.
- **Welcome and context.** `afc/hooks/session_start.py` shows the maintenance line and, in context,
  `Mode: maintenance. Plan: docs/master-plan.md. Do not touch projects.`
- **Command.** `/afc mm` and `/afc mm off` in `.claude/commands/afc.md` run
  `sh bin/afc maintain on|off` and restate the mode in one line.
- **Plan target.** `afc/cli_plan.py` gains `--fc` (or acts on `docs/master-plan.md` when maintenance
  mode is on) so the same `plan` commands manage Flight Control's own plan.
- **IDs.** Rename this repo's specs to `FC-001`… (files, master plan rows, links); `next_id` takes a
  prefix (`S` for projects, `FC` for Flight Control).
- **Skills.** `CLAUDE.md` gains a "Two kinds of work" section: building a user's project vs
  maintaining Flight Control, with how to tell and what to ask. The "ask before another spec" rule
  committed as `435bf22` on `claude/toolkit-layers-build-0d5bc1` is merged into `dev` and widened
  (unknown ID or branch → ask).
- **Where things run.** CONTRIBUTING describes three places: the daily `A-FC` folder runs released
  `main`; a developer copy on `dev` with maintenance mode and no active project; the test copy with
  its own home (S-001).

## Slices

- [ ] 1. Per-session maintenance mode — you'll check it by turning it on in one session and seeing
      another session still blocked from editing Flight Control (tests: per-session file, fallback,
      `status` names the scope)
- [ ] 2. Guard blocks project writes and project git in maintenance mode — you'll check it by asking
      for a change in php-vuln-checker while in maintenance mode and seeing a plain block (tests in
      `tests/test_guard_paths.py` and a new git-target guard test)
- [ ] 3. Welcome and context show the mode, and `/afc mm` switches it — you'll check it by starting a
      session and typing `/afc mm` (tests in `tests/test_session_start.py`, content test on `afc.md`)
- [ ] 4. `plan` works on Flight Control's own master plan — you'll check it by `sh bin/afc plan` in
      maintenance mode showing this spec (tests in `tests/test_cli_plan.py`)
- [ ] 5. `FC-` IDs for Flight Control's specs — you'll check it by `docs/master-plan.md` and
      `docs/specs/` using `FC-001`… with working links (tests: `next_id` with a prefix)
- [ ] 6. "Two kinds of work" in `CLAUDE.md`, the stricter ask-first rule, no branches in apps, and
      verified undo — you'll check it by repeating "build S-002 on dev" with a project active and
      getting one clear question instead of a build (content tests)
- [ ] 7. Bring the two stranded fixes onto `dev` (`435bf22`, `77eda62`) and write the three places in
      CONTRIBUTING — you'll check it by `git log dev` showing both and a fresh developer copy set up
      from the instructions

## Decisions

## Shipped
