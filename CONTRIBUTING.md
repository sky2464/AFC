# Developing Flight Control

Flight Control is "just AI prompting": markdown, skills, hooks and small Python scripts (standard
library only). No app, no runtime, no SDK.

## Set up

Make a developer copy: a full clone of its own, next to the folder you run real projects from:

```bash
git clone https://github.com/sky2464/AFC.git A-FC-dev
```

## Branches

- `main` holds released versions, tagged (e.g. `v0.01a`).
- `dev` is where ongoing work lands. Branch from `dev` for a change and merge back into `dev`.

## What lives where

| Place | What is in it |
|---|---|
| `CLAUDE.md`, `.claude/` | Instructions, skills, the `/afc` command and the hook settings |
| `bin/afc` | Launcher: finds Python 3.10+ and runs the command line and hooks |
| `afc/` | The command line (`sh bin/afc <command>`) and the hooks (`afc/hooks/`) |
| `afc/plan.py`, `afc/cli_plan.py` | Master plan tables, and the `plan` commands |
| `afc/addons.py`, `afc/tools.py`, `afc/cli_tools.py` | Allowed add-on list, swapping a project's skills and MCP servers in and out, and the `addons` / `tools` commands |
| `afc-addons.json` | The add-ons Flight Control sessions may use |
| `rules/`, `templates/`, `library/` | Rule modules, project templates and the capability library (`library/skills/`, `library/mcp/` recipes) |
| `tests/` | Unit tests |
| `docs/superpowers/` | Design, plans and acceptance results |

Project data never goes in this repo: it lives in `~/.A-FC/` (or `$AFC_HOME`).

## Three places to work

Flight Control work and real use stay apart by living in different places.

| Place | What it is for | Branch | Maintenance mode | Project data |
|---|---|---|---|---|
| Daily folder (`A-FC`) | Running Flight Control for real projects | released versions on `main` | off | your real `~/.A-FC` |
| Developer copy (`A-FC-dev`) | Changing Flight Control itself | `dev`, or a branch off it | on (`/afc mm`) | none: no project is touched |
| Test copy (`A-FC-test`) | Trying a change the way a user would | a snapshot of `dev` | off | its own home, set with `AFC_HOME` |

- Flight Control work (specs `FC-001`…) happens in the developer copy with maintenance mode on. It
  is never in the daily folder, and project work (specs `S-001`…) is never in the developer copy.
- A session in maintenance mode says so in its welcome (🔧 …) and sets every project aside.
- The test copy must use its own home: start it with `AFC_HOME=~/A-FC-test-home claude`, so test
  projects are never in your real `~/.A-FC`.
- Rollout order: the safety checks that run are the ones in the folder Claude Code was started in.
  When a change touches the guard or maintenance mode, update the daily folder first (`git pull`
  there) and only then use the new behavior. An older folder can't see a newer session flag, so it
  treats maintenance mode as off.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests always use a temporary `AFC_HOME`, so they never touch your real `~/.A-FC`.

## Editing Flight Control itself

The safety checks block edits to Flight Control by default. Turn on maintenance mode with
`/afc mm` (or `sh bin/afc maintain on`), and turn it off with `/afc mm off` (or
`sh bin/afc maintain off`) when done. It is on for this session only, and while it is on the guard
blocks writes and git in every project's folders.

## Design

See `docs/superpowers/specs/2026-10-21-flight-control-design.md` for the full design and
`docs/superpowers/acceptance/` for acceptance results.
