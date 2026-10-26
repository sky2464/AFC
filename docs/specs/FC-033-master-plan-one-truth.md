# FC-033 — Master plan, one truth

Size: M · Status: in progress

Asked for on 2026-10-25: the master plan must always be synced and be the only source of truth,
whatever branch, fork or worktree the work runs on. Today it isn't. What showed:

- **Built work stays in Next.** FC-030, FC-031 and FC-032 were built, checked and pushed, and the
  plan still lists them as Next. The build workflow (`.claude/workflows/afc-build-spec.js`) never
  calls `plan start` or `plan done`, so closing depends on someone remembering.
- **Every copy has its own plan.** `afc/cli_plan.py` reads `docs/master-plan.md` from whichever
  folder Flight Control runs in (`afc_root()`). A worktree or fork reads and edits its own copy.
  There are 12 worktrees and 36 branches here, many with their own older copy of the plan.
- **Specs outlive the plan.** Spec files and ticked slices live in the same folder as the plan, so
  they drift together with it.
- **The same holds for users' apps.** A project's plan lives in its workspace (`~/.A-FC/projects/…`),
  so it is one copy, but the slice flow has to start and close specs there on its own.

## Goal

There is one master plan: the one on `dev` (for Flight Control) or in the project's workspace (for an
app). Starting, finishing and checking work updates it automatically, wherever the work runs, and
no copy can disagree with it.

## Reaches the apps

Yes. `afc-slice` and `afc-deliver` already call `plan start` and `plan done` in projects; this makes
those calls automatic and checked, so an app's plan is never stale after a slice. Flight Control's
own build uses the same plan commands.

## You'll know it works when

- Building a spec with the build workflow moves it to Now at the start and to Done (spec archived)
  at the end, with no manual step.
- Running `sh bin/afc plan` in any worktree or fork of A-FC shows the plan from `dev`, not that
  folder's own copy, and a plan change made there lands on `dev`.
- `sh bin/afc check` lists a stale plan as a fixable problem: a built spec still in Next, a Now row
  with all slices ticked, or a worktree plan that differs from `dev`'s. `repair` fixes it.
- In a project, a finished slice leaves the project's plan current without the user asking.
- `docs/master-plan.md` on `dev` shows FC-030, FC-031 and FC-032 as Done.

## Out of scope

Merging branches, or deleting worktrees and branches. Cross-machine sync. Changing how specs are
written.

## Design notes

- One resolver: the plan path is `afc_root()` of the main checkout on `dev` (found through
  `git worktree list`'s first entry), not the current folder. Edits made from a worktree write
  there, and a dirty main checkout stops the write with a plain message.
- The build workflow calls `plan start` before the first slice and `plan done` after the final
  gate, through `sh bin/afc` (the runtime has no shell, so use the existing helper like `gate`).
- The stale-plan check belongs in `afc/cli_health.py`, with the other fixable problems.
- Keep skill text to a line or two.

## Slices

- [x] 1. Close what's built — you'll see it by `plan` showing FC-030, FC-031 and FC-032 in Done and
      their specs archived
- [x] 2. The build moves the plan — you'll see it by a build of a one-line FC slice moving its spec
      to Now at the start and to Done at the end with no manual call
- [x] 3. One plan wherever you stand — you'll see it by `sh bin/afc plan` run in a worktree showing
      `dev`'s plan, and `plan start` there changing `dev`'s file
- [x] 4. A stale plan is found and fixed — you'll see it by `sh bin/afc check` listing a built spec
      still in Next as fixable, and `repair` moving it
- [x] 5. Apps stay current — you'll see it by a slice finished in a test project leaving its plan
      with the right Now/Done rows with no extra step

## Tasks

Slice 1: run `sh bin/afc plan done FC-030`, `FC-031`, `FC-032` on `dev` (this closes and archives
them); commit.

Slice 2: `.claude/workflows/afc-build-spec.js` calls `plan start <id>` before building and
`plan done <id>` after the last gate passes; add a `sh bin/afc plan` helper subcommand it can call
if the runtime can't; only mark done when every slice passed.

Slice 3: in `afc/cli_plan.py` `_load()`, in maintenance mode resolve the plan root to the main
checkout from `git worktree list`; refuse with a plain sentence if that folder has uncommitted plan
edits. Same resolver for `plan add/start/done/drop/move/rename/goal`.

Slice 4: in `afc/cli_health.py` add three problems (`plan_built_in_next`, `plan_all_ticked_in_now`,
`plan_copy_differs`), each `fixable`; `repair` runs the matching `plan` command.

Slice 5: `.claude/skills/afc-slice/SKILL.md` and `afc-deliver/SKILL.md`: after a slice is accepted,
run `plan` and close the spec when its last slice is ticked, saying nothing about it unless asked.
Check a test project's plan after a live slice.

## Decisions

- 2026-10-25: `dev` in the main checkout is the one plan for Flight Control; worktrees and forks
  read and write through it.

## Shipped
