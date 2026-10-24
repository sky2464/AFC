# FC-010 — Maintenance mode keeps Flight Control work apart

Size: L · Status: done · Started: 2026-10-24 · Done: 2026-10-24

Findings: the 2026-10-24 mix-up (M1–M10 in the master plan). Priority: before FC-001.

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

Running two Flight Control versions side by side (FC-001 covers the test copy's home); production
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
  its own home (FC-001).

## Slices

- [x] 1. Per-session maintenance mode — you'll check it by turning it on in one session and seeing
      another session still blocked from editing Flight Control (tests: per-session file, fallback,
      `status` names the scope)
- [x] 2. Guard blocks project writes and project git in maintenance mode — you'll check it by asking
      for a change in php-vuln-checker while in maintenance mode and seeing a plain block (tests in
      `tests/test_guard_paths.py` and a new git-target guard test)
- [x] 3. Welcome and context show the mode, and `/afc mm` switches it — you'll check it by starting a
      session and typing `/afc mm` (tests in `tests/test_session_start.py`, content test on `afc.md`)
- [x] 4. `plan` works on Flight Control's own master plan — you'll check it by `sh bin/afc plan` in
      maintenance mode showing this spec (tests in `tests/test_cli_plan.py`)
- [x] 5. `FC-` IDs for Flight Control's specs — you'll check it by `docs/master-plan.md` and
      `docs/specs/` using `FC-001`… with working links (tests: `next_id` with a prefix)
- [x] 6. "Two kinds of work" in `CLAUDE.md`, the stricter ask-first rule, no branches in apps, and
      verified undo — you'll check it by repeating "build S-002 on dev" with a project active and
      getting one clear question instead of a build (content tests)
- [x] 7. Bring the two stranded fixes onto `dev` (`435bf22`, `77eda62`) and write the three places in
      CONTRIBUTING — you'll check it by `git log dev` showing both and a fresh developer copy set up
      from the instructions

## Decisions

- 2026-10-24: The command learns its session from `AFC_SESSION` (saved by the startup hook through
  `CLAUDE_ENV_FILE`, which is documented), then `CLAUDE_CODE_SESSION_ID` (present and matching in
  Claude Code, but not documented), then falls back to the old global switch and says so. Hooks
  always get `session_id` in their input (documented).
- 2026-10-24: Rollout order matters. The guard that runs is the one in the folder Claude Code was
  started from (the daily `A-FC` folder), not the copy being edited. Until that folder has the new
  code, it can't see session flags and treats maintenance mode as off. Update the folder first, then
  use the new switch. Slice 7's instructions must say so.
- 2026-10-24: Turning maintenance off also clears the global switch, so "off" always means off for
  the person who asked.

- 2026-10-24: The maintenance rule sits second in the guard, after the path rule (a test requires
  the path rule first). Any git command in a project folder is blocked, including read-only ones such
  as `git status`; plain reads of project files stay allowed. If the project list can't be read, the
  rule can't tell project folders and lets the request through; the other rules still apply.

- 2026-10-24: The welcome is built when a session starts, so it can't redraw after `/afc mm` turns
  the mode on mid-session; Claude restates the mode in its reply instead. The 🔧 welcome shows when a
  session starts, resumes or clears while maintenance is on (the flag lives as long as the session).
  The typed `/afc mm` flow is written as instructions and was not run in a live session when this
  slice was approved.

- 2026-10-24: Each plan numbers only its own prefix (`S` for projects, `FC` for Flight Control), and
  asking a plan command for the other kind of ID gets a plain hint. Mentions of what was typed in
  the mix-up keep their `S-` on purpose, as do the old design notes in `docs/superpowers/`, which
  describe project specs.

- 2026-10-24: The stranded "ask before building another spec" rule (`435bf22`) was brought onto
  `dev` in slice 6 (as `e05b16a`) and widened, so slice 7 only has the Bun audit fix (`77eda62`) and
  the "three places" notes left.
- 2026-10-24: The new rules are instructions, so tests only prove the wording exists. A dry run
  (a fresh agent reading only `CLAUDE.md` and `afc-slice`) answered correctly for "build S-002 on
  dev" (one question, no branch), "build FC-002" with maintenance off (offers `/afc mm`),
  "build S-001" in maintenance mode (offers `/afc mm off`) and an undo (shows `git status --short`).
  It found two gaps, now closed: ask about the first problem only, and ask before removing leftovers.
  Still to prove live: repeat "build S-002 on dev" with a project active in the daily folder.

- 2026-10-24: The Bun audit fix (`77eda62`) came onto `dev` as `647a474` and is recorded under
  FC-007, where it belongs; it was checked against real `bun audit` and `npm audit` output. The
  three places to work (daily folder, developer copy, test copy) and the rollout order are in
  CONTRIBUTING.md.
- 2026-10-24: Left for later, not part of this spec: the test copy still needs `AFC_HOME` typed by
  hand (FC-001 makes it automatic), and the new rules for Claude are proved only by a dry run until
  "build S-002 on dev" is repeated in a live session.

## Shipped

Shipped 2026-10-24. Slices: 7.
