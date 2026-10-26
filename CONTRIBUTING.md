# Developing Flight Control

Flight Control is "just AI prompting": markdown, skills, hooks and small Python scripts (standard
library only). No app, no runtime, no SDK.

## Set up

Make a developer copy: a full clone of its own, next to the folder you run real projects from:

```bash
git clone https://github.com/sky2464/AFC.git A-FC-dev
```

To try a change the way a user would, make a test copy as well and give it a workspace of its own.
A fresh clone uses your real `~/.A-FC` until you do, so do this before you start it:

```bash
git clone https://github.com/sky2464/AFC.git A-FC-test
```

```bash
cd A-FC-test
```

```bash
AFC_HOME=~/A-FC-test-home sh bin/afc maintain on
```

```bash
AFC_HOME=~/A-FC-test-home sh bin/afc home set ~/A-FC-test-home
```

```bash
sh bin/afc maintain off
```

The two prefixes keep the setup itself out of your real `~/.A-FC`; after them you never need one
again. `sh bin/afc home` should answer `"source": "file"` with that path, and `claude` started in
the folder uses it plainly. `sh bin/afc home clear` goes back to the default, and `AFC_HOME=…` on
the command line still wins over the file for a one-off run.

Setting the home writes `.afc-home` in the Flight Control folder, which is why it needs maintenance
mode for that one command. The file is git-ignored, so `git status` stays clean and `git pull`
keeps it.

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
| `tests/` | The five core tests |
| `docs/superpowers/` | Design, plans and acceptance results |

Project data never goes in this repo: it lives in `~/.A-FC/` (or `$AFC_HOME`).

## Three places to work

Flight Control work and real use stay apart by living in different places.

| Place | What it is for | Branch | Maintenance mode | Project data |
|---|---|---|---|---|
| Daily folder (`A-FC`) | Running Flight Control for real projects | released versions on `main` | off | your real `~/.A-FC` |
| Developer copy (`A-FC-dev`) | Changing Flight Control itself | `dev`, or a branch off it | on (`/afc mm`) | none: no project is touched |
| Test copy (`A-FC-test`) | Trying a change the way a user would | a snapshot of `dev` | off | its own home, set once with `sh bin/afc home set` |

- Flight Control work (specs `FC-001`…) happens in the developer copy with maintenance mode on. It
  is never in the daily folder, and project work (specs `S-001`…) is never in the developer copy.
- A session in maintenance mode says so in its welcome (🔧 …) and sets every project aside.
- The test copy must use its own home: set it once with `sh bin/afc home set` (see Set up), so test
  projects are never in your real `~/.A-FC`. After that `claude` needs no prefix; `sh bin/afc home`
  says which folder is in use and whether it came from the file, `AFC_HOME` or the default. A copy
  with no home set uses your real `~/.A-FC`, which is what sent the first test project there.
- Rollout order: the safety checks that run are the ones in the folder Claude Code was started in.
  When a change touches the guard or maintenance mode, update the daily folder first (`git pull`
  there) and only then use the new behavior. An older folder can't see a newer session flag, so it
  treats maintenance mode as off.

## Releasing

Users only ever see published releases: `v*` tags on `main`. Publishing stays your own step.

1. Merge `dev` into `main` (your own action).
2. Bump the `VERSION` file to the new version (e.g. `v0.03a`) in the release commit.
3. If the release changes the layout of the workspace (`~/.A-FC/`), ship a numbered upgrade step:
   `afc/upgrade_NNN.py` with `run(home)`, where step N takes the workspace from layout N-1 to N.
   The update backs up `~/.A-FC/`, runs missing steps in order and restores
   the backup if one fails.
4. Tag the release on `main` with the same version as `VERSION`
   and push the tag.

## Writing specs

Each slice of an FC spec ends with "you'll see it by" and names the live run or command output that
shows it. Where the outcome is a time, size or count, give the number: "the welcome prints within 0.5
seconds with the remote unreachable", not "never delays the welcome". A builder and a checker must
read the same line the same way. Existing specs are not rewritten, but a spec whose next slice has
no number where one is needed gets one before it is built.

When a spec is built with the `afc-build-spec` workflow, a check fails only on a problem that quotes
the spec line or safety rule it breaks; anything else is reported as a note.

## Tests

Flight Control keeps five tests, on the guards that protect user data.
Run them with `sh bin/afc test`, only when asked.
Tests use a temporary `AFC_HOME`, so they never touch your real `~/.A-FC`.

## Editing Flight Control itself

The safety checks block edits to Flight Control by default. Turn on maintenance mode with
`/afc mm` (or `sh bin/afc maintain on`), and turn it off with `/afc mm off` (or
`sh bin/afc maintain off`) when done. It is on for this session only, and while it is on the guard
blocks writes and git in every project's folders.

`sh bin/afc home set` and `sh bin/afc home clear` change a file in the Flight Control folder, so
they need maintenance mode too.

## Design

See `docs/superpowers/specs/2026-10-21-flight-control-design.md` for the full design and
`docs/superpowers/acceptance/` for acceptance results.
