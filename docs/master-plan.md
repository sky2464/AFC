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
| S-001 | Test copies use their own home | S | [spec](specs/S-001-test-copies-use-their-own-home.md) |
| S-002 | Fewer questions before building | M | [spec](specs/S-002-fewer-questions-before-building.md) |
| S-003 | A real, tested first slice | M | [spec](specs/S-003-real-tested-first-slice.md) |
| S-004 | Plan goal and plan editing | M | [spec](specs/S-004-plan-goal-and-plan-editing.md) |
| S-005 | Tidy, safe tool use | M | [spec](specs/S-005-tidy-safe-tool-use.md) |
| S-006 | Workspace notes in the right place | S | [spec](specs/S-006-workspace-notes-in-the-right-place.md) |
| S-007 | Package checks fit the stack | S | [spec](specs/S-007-package-checks-fit-the-stack.md) |
| S-008 | Agent instruction files in apps | S | [spec](specs/S-008-agent-instruction-files-in-apps.md) |
| S-009 | Leaner context per slice | M | [spec](specs/S-009-leaner-context-per-slice.md) |

## Done

| ID | Title | Done | Spec |
|---|---|---|---|
| TL | Toolkit layers (allowed add-ons, project tools, recipes) | 2026-10-24 | [stories](superpowers/plans/2026-10-23-toolkit-layers.md) |
| MP | Master plan, specs and archive | 2026-10-23 | [stories](superpowers/plans/2026-10-23-master-plan.md) |
| PC | Project controls: remove, pause/resume, health check | 2026-10-23 | — |
| v0.01a | First alpha: Python launcher, 1/2 welcome, first-run fix | 2026-10-23 | [release](https://github.com/sky2464/AFC/releases/tag/v0.01a) |

## Findings from the first live run (2026-10-23)

The php-vuln-checker test session surfaced 21 findings. Each maps to a spec:

| # | Finding | Spec |
|---|---|---|
| 1 | Test copy wrote into the real `~/.A-FC` because `AFC_HOME` was left off | S-001 |
| 2 | Nine questions before any building; folder asked before what to build | S-002 |
| 3 | First slice was a skeleton with no tests; tests saved for a last slice | S-003 |
| 4 | The master plan's Goal stays empty | S-004 |
| 5 | Decisions appended under Standing Corrections | S-006 |
| 6 | `architecture.md` never filled after the first slice | S-006 |
| 7 | Reshaping the plan was done by hand (`mv`, Python on tables) | S-004 |
| 8 | `npm audit` can't read a Bun project | S-007 |
| 9 | `pkill -f "next dev"` could stop other people's servers | S-005 |
| 10 | Recommended parent folder syncs to iCloud | S-002 |
| 11 | Team question asked on a brand-new personal repo | S-002 |
| 12 | Spec file names cut mid-word | S-004 |
| 13 | Next.js wrote an `AGENTS.md` with agent instructions; committed silently | S-008 |
| 14 | About 101k tokens of context for one slice | S-009 |
| 15 | An abandoned first session and blank launches (settings and add-ons, already fixed) | none; no change needed |
| 16 | Rule files dumped on screen; Claude guessed where rules live | S-005 |
| 17 | Files written through shell heredocs instead of file tools | S-005 |
| 18 | Claude kept changing folders and losing its place | S-005 |
| 19 | Slices written without checkboxes, so `plan` saw none | S-003 |
| 20 | Team question asked although `detect-team` had already decided | S-002 |
| 21 | Dev server log left in `/tmp`; broad process kill | S-005 |

## Update log

| Date | Event |
|---|---|
| 2026-10-24 | Master plan started; S-001 to S-009 added from the first live run |
