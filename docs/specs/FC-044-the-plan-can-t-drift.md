# FC-044 — The plan can't drift

Size: L · Status: in progress · Started: 2026-10-26 · Done: -

Found on 2026-10-26, comparing this plan with AgToosa's and looking at our own history.

- The plan is changed by hand. The Update log has no "added" row for FC-035 to FC-042, although
  `plan add` writes one. The tool has seven edits (add, goal, rename, drop, move, start, done), so a
  new size, a dependency or reopening a spec has no command.
- Plan moves are committed apart from the work: 122 of 367 commits are `docs:` commits ("FC-042
  started"), and between them the tree is dirty. Right now `docs/master-plan.md` and FC-041's header
  are uncommitted.
- `plan_problems` in `afc/cli_health.py` catches three things (a Now row with every slice ticked, a
  built spec still in Next, a worktree copy that differs) and only on Flight Control's own plan. It does
  not catch two rows in Now, a row whose spec file is gone, a spec header that disagrees with its
  section, an archive file missing from the index, a broken table, or a dirty plan.
- AgToosa shows where this ends: its DEV-154 and DEV-155 rows kept their pre-merge status until a
  whole story (#166) fixed them, and some of its Backlog rows landed under the wrong heading.
- `docs/superpowers/` holds the plans and designs from before FC-001, and the Done archive still has
  rows PC, MP, TL and v0.01a pointing at it, so "one truth" (FC-033) is not obvious to a newcomer.

## Goal

Anything wrong in the plan is found by `sh bin/afc check` in a plain sentence, on Flight Control's plan
and on every project's plan; what needs no decision is fixed by `repair`; every plan change has a
command, so hand editing is never needed; and a build never leaves the plan uncommitted.

## Reaches the apps

Yes. The check and the commands run on each user's project plan the same way (today `plan_problems`
reads only Flight Control's), so a user's plan is caught when a spec header and the plan disagree, and
the user gets `set` and `reopen` instead of editing tables by hand (`afc/plan.py`, `afc/cli_plan.py`,
`afc/cli_health.py`). The clean-tree part is Flight Control's own build workflow; a project's plan lives
in its workspace, not in the app's repository, so there is nothing to commit there.

## You'll know it works when

- A1. In a scratch copy of the plan, `sh bin/afc check` names each of these in one plain sentence: two
  rows in Now; a row whose spec file is missing; a spec header saying "done" while its row is in Next;
  an archive file not in `index.md`; a table row with the wrong number of cells. Run on a scratch
  project's plan it names the same.
- A2. `repair` fixes the archive index and leaves the rest, saying why.
- A3. `plan set <id> --size M` and `plan set <id> --depends FC-045` change the spec header, the row and
  the log; `plan start` of a spec whose dependency is not done says so and starts nothing;
  `plan reopen <id>` moves a finished spec back to Next with status "next" and logs it.
- A4. After the build workflow runs a one-slice scratch spec, `git status --short` is empty and the log
  shows `docs: <ID> started` and `docs: <ID> done, archived` commits.
- A5. `check` also says when Flight Control's own plan has uncommitted edits (not while a build is
  running).
- A6. `docs/superpowers/README.md` says in two lines that it is history from before FC-001 and not a
  place for new specs; `check` ignores that folder; the old Done rows stay.

## Out of scope

Splitting a spec (none has needed it yet). Moving the old history into `docs/specs/`. Changing the
plan's table columns. Merging, pushing or rewriting history.

## Design notes

- `plan_problems(home)` becomes `plan_problems(space)` and runs for Flight Control's plan and once for
  each registered project. New kinds join `PLAN_KINDS`; only `plan_archive_not_indexed` is fixable.
- Dependencies live in the spec header line (`Size: M · Status: next · Depends: FC-045`), not a table
  column, because plan code reads columns by position. `set_header` learns `depends`.
- `plan reopen` reverses `cmd_done`: it moves the archive file back, takes the row out of Done and
  logs; it refuses when the spec is not in Done.
- The dirty-plan check runs `git status --short -- docs/master-plan.md docs/specs` and is skipped
  while a spec is in Now with an open slice.
- The workflow `.claude/workflows/afc-build-spec.js` already calls `plan start` and `plan done`; it
  adds a commit after each that stages only `docs/master-plan.md` and `docs/specs`.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Find more, on both plans — you'll see it by a scratch Flight Control plan broken five ways and a
      scratch project plan broken the same ways, `check` naming each in one sentence (proves A1, A5)
- [ ] 2. Fix what needs no decision — you'll see it by `repair` adding the missing archive file to the
      index and saying why it left the other problems (proves A2)
- [ ] 3. Commands for what was done by hand — you'll see it by `plan set` changing size and dependency,
      `plan start` refusing while the dependency is open, and `plan reopen` bringing a finished
      scratch spec back (proves A3)
- [ ] 4. A build leaves a clean tree — you'll see it by the workflow building a one-slice scratch spec
      on a scratch clone and ending with an empty `git status --short` and the two `docs:` commits
      (proves A4)
- [ ] 5. Old history labelled — you'll see it by `docs/superpowers/README.md` and `check` on the real
      repo showing no problem from that folder (proves A6)

## Tasks

Slice 1:
- `afc/cli_health.py`: `plan_problems(space)`; kinds `plan_two_in_now`, `plan_no_spec_file`,
  `plan_status_mismatch`, `plan_archive_not_indexed`, `plan_table_broken`, `plan_uncommitted`;
  `find_problems` calls it for Flight Control's plan and for each project.

Slice 2:
- `afc/cli_health.py` `_repair_plan`: rebuild the index row with `cli_plan._archive_index`.

Slice 3:
- `afc/plan.py`: `set_header(..., depends=…)`.
- `afc/cli_plan.py`: `set`, `reopen`; `cmd_start` refuses an open dependency.

Slice 4:
- `.claude/workflows/afc-build-spec.js`: commit after `plan start` and after `plan done`.

Slice 5:
- `docs/superpowers/README.md`; the folder is skipped in the check.

## Decisions

## Shipped
