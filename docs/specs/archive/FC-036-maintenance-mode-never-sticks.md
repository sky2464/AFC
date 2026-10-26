# FC-036 — Maintenance mode never sticks

Size: S · Status: done

Found on 2026-10-25 in a fresh clone of `main` (`~/Documents/Code/AFC-Test/A-FC`, v0.04a). Nobody
typed `/afc mm`, yet the first start said "🔧 Maintenance: working on Flight Control itself · A-FC ·
main. Projects are set aside." The first "hi" got a maintenance menu instead of the welcome question.

Why it happened:

- **A global switch from Oct 24 was still on.** `~/.A-FC/maintain` was created on 2026-10-24 at
  12:24, before maintenance mode became per session. It still turns maintenance mode on for every
  Flight Control session on this Mac. `set_maintain` creates it whenever a session's ID can't be
  read (`afc/config.py`).
- **Nothing ever clears it.** Per-session switches are dropped after 7 days (`STALE_AFTER`); the
  global one never is. `check` doesn't report it, and the welcome doesn't say where the switch came
  from or how old it is.
- **A clone without its own workspace shares the real one.** The clone has no `.afc-home`, so it
  read `~/.A-FC`, switch included. That is how a real user's second copy behaves too.
- **Maintenance mode on a daily folder.** `CONTRIBUTING.md` says the daily folder (on `main`) runs
  with maintenance mode off and Flight Control work happens on `dev`. Nothing enforces that, so a
  released copy on `main` was set to edit Flight Control itself.

## Goal

Maintenance mode is only ever on in the one session that turned it on, and never in a copy on
`main`. A new or daily copy always starts with your projects.

## Reaches the apps

Yes. While the switch is stuck, every project is set aside in every session, so no app can be built
or changed at all. Fixing it gives users back their projects on the first start
(`afc/hooks/session_start.py`, `afc/config.py`, `sh bin/afc check`).

## You'll know it works when

- `sh bin/afc maintain on` never creates `~/.A-FC/maintain`. With no readable session ID it refuses
  in one plain line ("Maintenance mode needs this session's ID; open Flight Control in Claude Code
  and try again") and changes nothing.
- A leftover `~/.A-FC/maintain` is ignored: maintenance mode reads as off. `sh bin/afc check` lists
  it as `fixable`, and `sh bin/afc repair` removes it. The next update removes it as well, through
  workspace upgrade step 1 (`afc/upgrade_001.py`), so users on v0.05b who never run repair are
  cleared too.
- On `main`, `sh bin/afc maintain on` refuses in one line ("Flight Control is changed in the
  developer copy on dev, not here") and changes nothing, and any switch reads as off. Every other
  branch, a detached worktree included, works as today, so builds in worktrees aren't cut off.
- A fresh clone of `main` started with `claude` and "hi" shows the normal welcome and its 1/2
  question, with no 🔧 line, even when `~/.A-FC/maintain` exists.
- Maintenance mode in this developer copy on `dev` works as before: `/afc mm` turns it on for this
  session only, and `/afc mm off` turns it off.

## Out of scope

Giving each copy its own workspace automatically (FC-031 covers test copies). Changing what
maintenance mode allows once it is on. The guard rules themselves.

## Design notes

- `afc/config.py`: `maintain_scope` drops the `global` result. `set_maintain` without a session
  returns an error, not a fallback. Keep the `scope` field in `maintain status` ("session" or
  "off") so `/afc` still reads it.
- The branch comes from `update._branch` (it reads `.git/HEAD` with no git call). Only `main`
  counts. The rule is about the daily folder, and build worktrees are on other branches or
  detached, so naming one branch is safer than guessing which ones are "from dev".
- This is the first workspace layout change since FC-011, so it ships `afc/upgrade_001.py` (layout
  0 → 1: remove `maintain`). The next release spec must say so.
- `.claude/commands/afc.md` line 17 explains "scope global"; remove it.

## Slices

- [x] 1. No global switch — you'll see it by `sh bin/afc maintain on` with `AFC_SESSION` and
      `CLAUDE_CODE_SESSION_ID` unset printing the refusal and creating no file, and a touched
      `~/.A-FC/maintain` (in a scratch `AFC_HOME`) reading as off, listed by `check` and removed by
      `repair`
- [x] 2. Cleared by the update — you'll see it by `workspace_upgrade.upgrade` (what an update runs)
      taking a scratch workspace at layout 0 with a `maintain` file to layout 1, with the file gone
      and a backup made
- [x] 3. Never on main — you'll see it by `sh bin/afc maintain on` on a scratch clone of `main`
      refusing in one line, while on `dev` it prints `"scope": "session"`
- [x] 4. Live check — you'll see it by a fresh `git clone --depth 1` of `dev` into a scratch folder,
      switched to a branch named `main`, starting with `claude -p hi` against a home that has a
      `maintain` file, and showing the 1/2 welcome with no 🔧 line

## Tasks

Slice 1:
- `afc/config.py`: remove the global branch from `maintain_scope` and `set_maintain`. Raise a
  `ValueError` with the refusal text when there's no session.
- `afc/cli_maintain.py`: turn that error into `{"error": "..."}`. Drop `GLOBAL_NOTE` and the
  `global` note.
- `afc/cli_health.py`: a `stale_maintain` problem (fixable) when `home/"maintain"` exists. Repair
  removes it.
- `.claude/commands/afc.md`: remove the "If the result has `scope` 'global'" line.

Slice 2:
- `afc/upgrade_001.py`: `run(home)` removes `home/"maintain"` if present. Nothing else.
- `CONTRIBUTING.md` (Releasing): note that the next release carries layout 1.

Slice 3:
- `afc/config.py`: `maintain_scope` returns "off" when the copy is on `main`, so the guard, the
  welcome and `/afc` all agree.
- `afc/cli_maintain.py`: refuse `on` on `main`.

Slice 4:
- Run the live check and write the welcome's first lines in Decisions.

## Decisions

Live check (fresh `git clone --depth 1` of `dev`, switched to branch `main`, `claude -p hi` with a home holding a `maintain` file): the welcome began "Hi! Are you starting a new project, or working on one that already exists on this computer?" with options 1. Start a new project (recommended) / 2. Bring in one that already exists, and no maintenance line. The leftover `maintain` file was ignored, not deleted; the health check flagged it as one fixable problem.

## Shipped

Shipped 2026-10-25. Slices: 4.
