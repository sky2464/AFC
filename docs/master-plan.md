# Master plan

Flight Control's own master plan, kept in the same shape it gives every project. Specs live in
`docs/specs/`; finished ones move to `docs/specs/archive/`. Build each spec on `dev`, one commit
per slice, with maintenance mode on while editing.

## Goal

A calm co-pilot inside Claude Code that turns what someone wants to build into small, working,
safe slices, with as few questions and as little noise as possible.

Every change must reach the apps Flight Control builds for users.

## Now

| ID | Title | Size | Spec | Started |
|---|---|---|---|---|
| FC-035 | Ready for v0.05b | S | [FC-035](specs/FC-035-ready-for-v0-05b.md) | 2026-10-25 |

## Next

| ID | Title | Size | Spec |
|---|---|---|---|

## Done

| ID | Title | Done | Spec |
|---|---|---|---|
| FC-034 | Connectors load only when needed | 2026-10-25 | [FC-034](specs/archive/FC-034-connectors-load-only-when-needed.md) |
| FC-033 | Master plan, one truth | 2026-10-25 | [FC-033](specs/archive/FC-033-master-plan-one-truth.md) |
| FC-032 | Every spec reaches the apps | 2026-10-25 | [FC-032](specs/archive/FC-032-every-spec-reaches-the-apps.md) |
| FC-031 | Test copy stays current and separate | 2026-10-25 | [FC-031](specs/archive/FC-031-test-copy-stays-current-and-separate.md) |
| FC-030 | Tests only when asked | 2026-10-25 | [FC-030](specs/archive/FC-030-tests-only-when-asked.md) |
| FC-029 | Ready for v0.04a | 2026-10-25 | [FC-029](specs/archive/FC-029-ready-for-v0-04a.md) |
| FC-028 | Welcome says it once | 2026-10-25 | [FC-028](specs/archive/FC-028-welcome-says-it-once.md) |
| FC-027 | Add-ons off at start, quiet health check | 2026-10-25 | [FC-027](specs/archive/FC-027-add-ons-off-at-start-quiet-health-check.md) |
| FC-026 | Release check and v0.03a | 2026-10-25 | [FC-026](specs/archive/FC-026-release-check-and-v0-03a.md) |
| FC-025 | Token usage cost by model | 2026-10-25 | [FC-025](specs/archive/FC-025-token-usage-by-model.md) |

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
| U8 | `sh bin/afc maintain` with no argument says `Missing state.` without naming on, off or status | FC-023 |
| U9 | The first question was asked twice: the welcome offered 1/2, then `afc-start` asked again | FC-023 |

## Findings from the v0.03a update test (2026-10-25)

A scratch copy of the previous `main` updated itself from v0.01a to v0.03a in one step, ended clean
on `main` and passed all 1034 tests. Its summary still read as a failure. An `A-FC-test` session the
same day showed the rest.

| # | Finding | Spec |
|---|---|---|
| R1 | The after-update summary listed 28 account add-ons as "problems to look at"; nothing was wrong | FC-027 |
| R2 | Add-ons are switched off only on `repair`, which nothing runs, so all 28 load in every Flight Control session; `check` says they were "switched off" | FC-027 |
| R3 | The welcome said "a health check found 30 problems"; 28 were those add-ons | FC-027 |
| R4 | The first reply to "hi" used 75,950 tokens, mostly the 28 add-ons loading | FC-027 |
| R5 | After the welcome, the reply to "hi" introduced Flight Control again and re-asked the same 1/2 question | FC-028 |
| R6 | `A-FC-test` sits on older code (973da0c, detached), so live tests there don't test the current release | none; the user moves it forward |
| R7 | With add-ons off, a "hi" still loads 350 tools and about 60k tokens, mostly claude.ai connectors that `enabledPlugins` doesn't reach | FC-034 |

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
| 2026-10-25 | FC-011 started |
| 2026-10-25 | FC-011 done |
| 2026-10-25 | FC-018 Leaner spec builds added and specced (5 slices) after the FC-011 build: one checker per slice, lean helpers, sharper checks, keep awake; queued last in Next |
| 2026-10-25 | FC-018 started |
| 2026-10-25 | FC-013 started, built with the FC-018 workflow to measure it (FC-018 slice 5) |
| 2026-10-25 | FC-018 done: helpers 7.0→2.0 and tokens 7.5M→0.25M per slice, full-suite runs 8.7→5.0 (target 4.35 missed; FC-013 run-one-file rule covers it) |
| 2026-10-25 | FC-013 done |
| 2026-10-25 | FC-014 started |
| 2026-10-25 | FC-014 done |
| 2026-10-25 | FC-015 started |
| 2026-10-25 | FC-019 Checks only when needed added and specced (6 slices) during the FC-015 build: parallel suite, tests for what changed, checker only for risky slices, one suite at the end, CI; queued first in Next |
| 2026-10-25 | FC-015 done |
| 2026-10-25 | FC-019 started |
| 2026-10-25 | FC-019 done |
| 2026-10-25 | FC-017 started |
| 2026-10-25 | FC-017 done |
| 2026-10-25 | FC-020 added |
| 2026-10-25 | FC-020 started |
| 2026-10-25 | FC-020 done |
| 2026-10-25 | FC-021–FC-025 added (role agents, project workflow, flow fixes, Jev stub, token cost) |
| 2026-10-25 | FC-021 done |
| 2026-10-25 | FC-022 started |
| 2026-10-25 | FC-022 done |
| 2026-10-25 | FC-023 started |
| 2026-10-25 | FC-023 done |
| 2026-10-25 | FC-024 started |
| 2026-10-25 | FC-024 done |
| 2026-10-25 | FC-025 started |
| 2026-10-25 | FC-025 done |
| 2026-10-25 | FC-026 added |
| 2026-10-25 | FC-026 started |
| 2026-10-25 | FC-026 done |
| 2026-10-25 | FC-027 added |
| 2026-10-25 | FC-027 renamed to Add-ons off at start, quiet health check |
| 2026-10-25 | FC-028 added |
| 2026-10-25 | FC-027 started |
| 2026-10-25 | FC-027 done |
| 2026-10-25 | FC-028 started |
| 2026-10-25 | FC-028 done |
| 2026-10-25 | FC-029 added |
| 2026-10-25 | FC-029 started |
| 2026-10-25 | FC-029 done |
| 2026-10-25 | FC-030 started |
| 2026-10-25 | FC-030 done |
| 2026-10-25 | FC-031 started |
| 2026-10-25 | FC-031 done |
| 2026-10-25 | FC-032 started |
| 2026-10-25 | FC-032 done |
| 2026-10-25 | FC-033 started |
| 2026-10-25 | FC-033 done |
| 2026-10-25 | FC-034 added and specced (5 slices): connectors load only when needed, per project |
| 2026-10-25 | FC-034 started |
| 2026-10-25 | FC-034 done |
| 2026-10-25 | FC-035 started |
