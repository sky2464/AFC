# Findings

Problems found in live runs, reviews, and maintenance. New findings use IDs `F-001`, `F-002`, …
so they never collide with the numbered series below. State transitions for `open` and `in progress`
are automated by `plan start` and `plan done` when a spec names `Fixes: <id>`.

## States

open · in progress · fixed in FC-0xx · waiting on you · parked · no change needed

## All findings

| ID | Finding | State | Found |
|---|---|---|---|
| 1 | Test copy wrote into the real `~/.A-FC` because `AFC_HOME` was left off | fixed in FC-001 | live run 2026-10-23 |
| 2 | Nine questions before any building; folder asked before what to build | fixed in FC-002 | live run 2026-10-23 |
| 3 | First slice was a skeleton with no tests; tests saved for a last slice | fixed in FC-003 | live run 2026-10-23 |
| 4 | The master plan's Goal stays empty | fixed in FC-004 | live run 2026-10-23 |
| 5 | Decisions appended under Standing Corrections | fixed in FC-006 | live run 2026-10-23 |
| 6 | `architecture.md` never filled after the first slice | fixed in FC-006 | live run 2026-10-23 |
| 7 | Reshaping the plan was done by hand (`mv`, Python on tables) | fixed in FC-004 | live run 2026-10-23 |
| 8 | `npm audit` can't read a Bun project | fixed in FC-007 | live run 2026-10-23 |
| 9 | `pkill -f "next dev"` could stop other people's servers | fixed in FC-005 | live run 2026-10-23 |
| 10 | Recommended parent folder syncs to iCloud | fixed in FC-002 | live run 2026-10-23 |
| 11 | Team question asked on a brand-new personal repo | fixed in FC-002 | live run 2026-10-23 |
| 12 | Spec file names cut mid-word | fixed in FC-004 | live run 2026-10-23 |
| 13 | Next.js wrote an `AGENTS.md` with agent instructions; committed silently | fixed in FC-008 | live run 2026-10-23 |
| 14 | About 101k tokens of context for one slice | fixed in FC-009 | live run 2026-10-23 |
| 15 | An abandoned first session and blank launches (settings and add-ons, already fixed) | no change needed | live run 2026-10-23 |
| 16 | Rule files dumped on screen; Claude guessed where rules live | fixed in FC-005 | live run 2026-10-23 |
| 17 | Files written through shell heredocs instead of file tools | fixed in FC-005 | live run 2026-10-23 |
| 18 | Claude kept changing folders and losing its place | fixed in FC-005 | live run 2026-10-23 |
| 19 | Slices written without checkboxes, so `plan` saw none | fixed in FC-003 | live run 2026-10-23 |
| 20 | Team question asked although `detect-team` had already decided | fixed in FC-002 | live run 2026-10-23 |
| 21 | Dev server log left in `/tmp`; broad process kill | fixed in FC-005 | live run 2026-10-23 |
| M1 | Maintenance mode changes who the work is for, not just what may be edited | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M2 | A real `/afc mm` switch instead of a convention Claude must remember | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M3 | The guard blocks project writes and project git while in maintenance mode | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M4 | Different IDs: `FC-…` for Flight Control's specs, `S-…` for projects | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M5 | An unknown spec ID or branch means ask, never guess | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M6 | Never create a branch in an app without asking | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M7 | Separate places: daily folder on `main`, developer copy on `dev`, test copy with its own home | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M8 | The welcome always shows which world you're in | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M9 | Maintenance work ends up on `dev`, or says where it is | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| M10 | Undo is verified with `git status`, not assumed | fixed in FC-010 | maintenance mix-up 2026-10-24 |
| U1 | Git that changes the `A-FC` folder ran with maintenance mode off; no guard saw it | fixed in FC-012 | update session 2026-10-24 |
| U2 | The copy was left on a detached HEAD, which FC-011 would then always refuse to update | fixed in FC-012 | update session 2026-10-24 |
| U3 | `sh bin/afc check` has no check for the `A-FC` folder's own git state | fixed in FC-012 | update session 2026-10-24 |
| U4 | A rule was seen to be broken and the work carried on | fixed in FC-012 | update session 2026-10-24 |
| U5 | The installed version was guessed from truncated `git tag` and `git log` output | fixed in FC-011 | update session 2026-10-24 |
| U6 | "What's new" was told in FC- IDs, branch names and commit subjects, not plain words | fixed in FC-011 | update session 2026-10-24 |
| U7 | Nothing was verified after the self-update: no tests, no `check`, no workspace backup | fixed in FC-011 | update session 2026-10-24 |
| U8 | `sh bin/afc maintain` with no argument says `Missing state.` without naming on, off or status | fixed in FC-023 | update session 2026-10-24 |
| U9 | The first question was asked twice: the welcome offered 1/2, then `afc-start` asked again | fixed in FC-023 | update session 2026-10-24 |
| R1 | The after-update summary listed 28 account add-ons as "problems to look at"; nothing was wrong | fixed in FC-027 | v0.03a update test 2026-10-25 |
| R2 | Add-ons are switched off only on `repair`, which nothing runs, so all 28 load in every Flight Control session; `check` says they were "switched off" | fixed in FC-027 | v0.03a update test 2026-10-25 |
| R3 | The welcome said "a health check found 30 problems"; 28 were those add-ons | fixed in FC-027 | v0.03a update test 2026-10-25 |
| R4 | The first reply to "hi" used 75,950 tokens, mostly the 28 add-ons loading | fixed in FC-027 | v0.03a update test 2026-10-25 |
| R5 | After the welcome, the reply to "hi" introduced Flight Control again and re-asked the same 1/2 question | fixed in FC-028 | v0.03a update test 2026-10-25 |
| R6 | `A-FC-test` sits on older code (973da0c, detached), so live tests there don't test the current release | fixed | v0.03a update test 2026-10-25 |
| R7 | With add-ons off, a "hi" still loads 350 tools and about 60k tokens, mostly claude.ai connectors that `enabledPlugins` doesn't reach | fixed in FC-034 | v0.03a update test 2026-10-25 |
