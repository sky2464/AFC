# Master plan

Flight Control's own master plan, kept in the same shape it gives every project. Specs live in
`docs/specs/`; finished ones move to `docs/specs/archive/`. Build each spec on `dev`, one commit
per slice, with maintenance mode on while editing and the full suite passing.

## Goal

A calm co-pilot inside Claude Code that turns what someone wants to build into small, working,
safe slices, with as few questions and as little noise as possible.

## Now

| ID | Title | Size | Spec | Started |
|---|---|---|---|---|

## Next

| ID | Title | Size | Spec |
|---|---|---|---|
| FC-001 | Test copies use their own home | S | [spec](specs/FC-001-test-copies-use-their-own-home.md) |
| FC-002 | Fewer questions before building | M | [spec](specs/FC-002-fewer-questions-before-building.md) |
| FC-003 | A real, tested first slice | M | [spec](specs/FC-003-real-tested-first-slice.md) |
| FC-004 | Plan goal and plan editing | M | [spec](specs/FC-004-plan-goal-and-plan-editing.md) |
| FC-005 | Tidy, safe tool use | M | [spec](specs/FC-005-tidy-safe-tool-use.md) |
| FC-006 | Workspace notes in the right place | S | [spec](specs/FC-006-workspace-notes-in-the-right-place.md) |
| FC-007 | Package checks fit the stack | S | [spec](specs/FC-007-package-checks-fit-the-stack.md) |
| FC-008 | Agent instruction files in apps | S | [spec](specs/FC-008-agent-instruction-files-in-apps.md) |
| FC-009 | Leaner context per slice | M | [spec](specs/FC-009-leaner-context-per-slice.md) |
| FC-011 | One-click updates | L | [spec](specs/FC-011-one-click-updates.md) |

## Done

| ID | Title | Done | Spec |
|---|---|---|---|
| FC-010 | Maintenance mode keeps Flight Control work apart | 2026-10-24 | [FC-010](specs/archive/FC-010-maintenance-mode-keeps-flight-control-work-apart.md) |
| TL | Toolkit layers (allowed add-ons, project tools, recipes) | 2026-10-24 | [stories](superpowers/plans/2026-10-23-toolkit-layers.md) |
| MP | Master plan, specs and archive | 2026-10-23 | [stories](superpowers/plans/2026-10-23-master-plan.md) |
| PC | Project controls: remove, pause/resume, health check | 2026-10-23 | — |
| v0.01a | First alpha: Python launcher, 1/2 welcome, first-run fix | 2026-10-23 | [release](https://github.com/sky2464/AFC/releases/tag/v0.01a) |

## Findings from the first live run (2026-10-23)

The php-vuln-checker test session surfaced 21 findings. Each maps to a spec:

| # | Finding | Spec |
|---|---|---|
| 1 | Test copy wrote into the real `~/.A-FC` because `AFC_HOME` was left off | FC-001 |
| 2 | Nine questions before any building; folder asked before what to build | FC-002 |
| 3 | First slice was a skeleton with no tests; tests saved for a last slice | FC-003 |
| 4 | The master plan's Goal stays empty | FC-004 |
| 5 | Decisions appended under Standing Corrections | FC-006 |
| 6 | `architecture.md` never filled after the first slice | FC-006 |
| 7 | Reshaping the plan was done by hand (`mv`, Python on tables) | FC-004 |
| 8 | `npm audit` can't read a Bun project | FC-007 |
| 9 | `pkill -f "next dev"` could stop other people's servers | FC-005 |
| 10 | Recommended parent folder syncs to iCloud | FC-002 |
| 11 | Team question asked on a brand-new personal repo | FC-002 |
| 12 | Spec file names cut mid-word | FC-004 |
| 13 | Next.js wrote an `AGENTS.md` with agent instructions; committed silently | FC-008 |
| 14 | About 101k tokens of context for one slice | FC-009 |
| 15 | An abandoned first session and blank launches (settings and add-ons, already fixed) | none; no change needed |
| 16 | Rule files dumped on screen; Claude guessed where rules live | FC-005 |
| 17 | Files written through shell heredocs instead of file tools | FC-005 |
| 18 | Claude kept changing folders and losing its place | FC-005 |
| 19 | Slices written without checkboxes, so `plan` saw none | FC-003 |
| 20 | Team question asked although `detect-team` had already decided | FC-002 |
| 21 | Dev server log left in `/tmp`; broad process kill | FC-005 |

## Findings from the maintenance mix-up (2026-10-24)

Asked to build Flight Control's own specs ("build S-001", "build S-002 on dev"), a session built the
php-vuln-checker app three times instead. All of these map to FC-010:

| # | Must change |
|---|---|
| M1 | Maintenance mode changes who the work is for, not just what may be edited |
| M2 | A real `/afc mm` switch instead of a convention Claude must remember |
| M3 | The guard blocks project writes and project git while in maintenance mode |
| M4 | Different IDs: `FC-…` for Flight Control's specs, `S-…` for projects |
| M5 | An unknown spec ID or branch means ask, never guess |
| M6 | Never create a branch in an app without asking |
| M7 | Separate places: daily folder on `main`, developer copy on `dev`, test copy with its own home |
| M8 | The welcome always shows which world you're in |
| M9 | Maintenance work ends up on `dev`, or says where it is |
| M10 | Undo is verified with `git status`, not assumed |

## Update log

| Date | Event |
|---|---|
| 2026-10-24 | Master plan started; FC-001 to FC-009 added from the first live run |
| 2026-10-24 | FC-010 added at the top after the maintenance mix-up; the Bun audit fix for FC-007 already exists on `claude/toolkit-layers-build-0d5bc1` (`77eda62`) |
| 2026-10-24 | FC-010 started |
| 2026-10-24 | Flight Control's specs renamed FC-001 to FC-010; S- stays for project specs |
| 2026-10-24 | FC-007's code and tests brought onto `dev` with FC-010 slice 7 and checked against real Bun and npm output; waiting to be closed |
| 2026-10-24 | FC-010 done |
| 2026-10-24 | FC-011 One-click updates specced and sliced (7 slices); queued in Next |
