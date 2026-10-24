# Developing Flight Control

Flight Control is "just AI prompting": markdown, skills, hooks and small Python scripts (standard
library only). No app, no runtime, no SDK.

## Set up

Work on Flight Control in a full clone of its own, not in the `A-FC` folder you use day to day:

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

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests always use a temporary `AFC_HOME`, so they never touch your real `~/.A-FC`.

## Editing Flight Control itself

The safety checks block edits to Flight Control by default. Turn on maintenance mode with
`sh bin/afc maintain on` (or `/afc` → More…), and turn it off with `sh bin/afc maintain off` when
done.

## Design

See `docs/superpowers/specs/2026-10-21-flight-control-design.md` for the full design and
`docs/superpowers/acceptance/` for acceptance results.
