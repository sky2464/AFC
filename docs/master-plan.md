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
| FC-011 | One-click updates | L | [spec](specs/FC-011-one-click-updates.md) |
| FC-013 | Right-sized tests | M | [spec](specs/FC-013-right-sized-tests.md) |
| FC-014 | Review before delivery | M | [spec](specs/FC-014-review-before-delivery.md) |
| FC-015 | Ship a finished spec | M | [spec](specs/FC-015-ship-a-finished-spec.md) |
| FC-017 | Leaner replies, plan edits and skill text | M | [spec](specs/FC-017-leaner-replies-plan-edits-and-skill-text.md) |

## Done

| ID | Title | Done | Spec |
|---|---|---|---|
| FC-012 | Flight Control keeps its own copy safe | 2026-10-25 | [FC-012](specs/archive/FC-012-flight-control-keeps-its-own-copy-safe.md) |
| FC-009 | Leaner context per slice (closed; target not met, rest in FC-017) | 2026-10-25 | [FC-009](specs/archive/FC-009-leaner-context-per-slice.md) |
| FC-008 | Agent instruction files in apps | 2026-10-24 | [FC-008](specs/archive/FC-008-agent-instruction-files-in-apps.md) |
| FC-016 | Nothing drops out of the plan | 2026-10-24 | [FC-016](specs/archive/FC-016-nothing-drops-out-of-the-plan.md) |
| FC-007 | Package checks fit the stack | 2026-10-24 | [FC-007](specs/archive/FC-007-package-checks-fit-the-stack.md) |
| FC-006 | Workspace notes in the right place | 2026-10-24 | [FC-006](specs/archive/FC-006-workspace-notes-in-the-right-place.md) |
| FC-005 | Tidy, safe tool use | 2026-10-24 | [FC-005](specs/archive/FC-005-tidy-safe-tool-use.md) |
| FC-004 | Plan goal and plan editing | 2026-10-24 | [FC-004](specs/archive/FC-004-plan-goal-and-plan-editing.md) |
| FC-003 | A real, tested first slice | 2026-10-24 | [FC-003](specs/archive/FC-003-real-tested-first-slice.md) |
| FC-002 | Fewer questions before building | 2026-10-24 | [FC-002](specs/archive/FC-002-fewer-questions-before-building.md) |

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

## Findings from the update session (2026-10-24)

Asked "is there any afc update?", a session on an older copy answered from raw `git tag` and
`git log` output, then updated Flight Control with a hand `git merge --ff-only v0.02a` — with
maintenance mode off, leaving the copy on a detached HEAD.

| # | Finding | Spec |
|---|---|---|
| U1 | Git that changes the `A-FC` folder ran with maintenance mode off; no guard saw it | FC-012 |
| U2 | The copy was left on a detached HEAD, which FC-011 would then always refuse to update | FC-012 |
| U3 | `sh bin/afc check` has no check for the `A-FC` folder's own git state | FC-012 |
| U4 | A rule was seen to be broken ("updated without a maintenance-mode prompt") and the work carried on | FC-012 |
| U5 | The installed version was guessed from truncated `git tag` and `git log` output | FC-011 |
| U6 | "What's new" was told in FC- IDs, branch names and commit subjects, not plain words | FC-011 |
| U7 | Nothing was verified after the self-update: no tests, no `check`, no workspace backup | FC-011 |
| U8 | `sh bin/afc maintain` with no argument says `Missing state.` without naming on, off or status | none yet |
| U9 | The first question was asked twice: the welcome offered 1/2, then `afc-start` asked again | none yet |

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
| 2026-10-24 | FC-012 added |
| 2026-10-24 | FC-012 specced and sliced (5 slices) from the update session's findings; queued last in Next |
| 2026-10-24 | FC-001 started |
| 2026-10-24 | FC-001 done |
| 2026-10-24 | FC-002 started |
| 2026-10-24 | FC-013 Right-sized tests specced and sliced (3 slices); queued last in Next |
| 2026-10-24 | FC-002 done |
| 2026-10-24 | FC-014 added |
| 2026-10-24 | FC-015 added |
| 2026-10-24 | FC-014 and FC-015 specced and sliced (5 slices each): review folded into building a slice, ship folded into finishing a spec; deploys and history rewrites left as the user's own actions |
| 2026-10-24 | FC-003 started |
| 2026-10-24 | FC-003 done |
| 2026-10-24 | FC-004 started |
| 2026-10-24 | FC-004 done |
| 2026-10-24 | FC-005 started |
| 2026-10-24 | FC-005 done |
| 2026-10-24 | FC-006 started |
| 2026-10-24 | FC-006 done |
| 2026-10-24 | FC-007 started |
| 2026-10-24 | FC-007 done |
| 2026-10-24 | FC-016 added |
| 2026-10-24 | FC-016 specced and sliced (3 slices): compaction drops Done rows instead of archiving them, which lost the PC and v0.01a rows; FC-015 depends on it |
| 2026-10-24 | FC-016 started |
| 2026-10-24 | FC-016 done |
| 2026-10-24 | FC-008 started |
| 2026-10-24 | FC-008 done |
| 2026-10-24 | FC-009 started |
| 2026-10-25 | FC-009 closed: slice 4 measured at 46,010 growth against 24,490, target not met; spec archived |
| 2026-10-25 | FC-017 added and specced (4 slices); queued last in Next |
| 2026-10-25 | FC-012 slice 3 approved and ticked: the health check sees the A-FC folder; spec stays in Next while FC-009 holds Now |
| 2026-10-25 | FC-014 slice 1 approved and ticked: review gives a verdict; spec stays in Next while FC-009 holds Now |
| 2026-10-25 | FC-012 started |
| 2026-10-25 | FC-012 done |
