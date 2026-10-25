# FC-015 — Ship a finished spec

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-24. Reference design: the user's earlier AgToosa ship workflow (a readiness
gate, a changelog, plan pruning and a suggested next story), cut down to the steps Flight Control is
allowed to take on its own.

## Goal

When the last slice of a spec is approved, finishing it is one safe step: Flight Control checks the
spec is really finished, writes down what shipped in words the user can read, prunes the plan, and
says what is next.

Today `sh bin/afc plan done <id>` already refuses while slices are open, archives the spec, moves
the row to Done, logs it and suggests the next spec. What is missing is everything that makes
finishing trustworthy — nobody checks that the tests are green, that the code folder is committed,
that no `WIP` commit is left on the branch — and nothing tells the user, in their own language, what
they just got.

## You'll know it works when

- When the last slice is approved, then `sh bin/afc plan done <id>` runs a readiness gate first and,
  if anything is missing, refuses with a plain list: a slice not ticked, the test suite failing,
  uncommitted changes in the code folder, a `WIP` commit still on the branch, an unpushed branch on
  a project with a remote, or a blocked verdict from the last review (FC-014).
- When the gate fails, then nothing is archived, nothing is written, the plan is untouched, and the
  one thing to do next is named.
- When the gate passes, then the spec is archived as it is today and a changelog entry is written in
  the project workspace: the date, what the spec set out to do, and the slices that shipped.
- When a spec is finished, then the user is told in one or two plain lines what shipped and what is
  next, with the next spec offered as step 1.
- When the test suite can't be run because the project has no test command recorded, then the gate
  says so and counts it as missing, never as passing.
- When `sh bin/afc ship --check <id>` is run, then it reports the same gate and changes nothing at
  all.
- When Flight Control's own plan finishes a spec in maintenance mode, then it gets a changelog entry
  the same way a project does.

## Out of scope

Deploying to any environment, and rewriting history to tidy `WIP` commits: both stay the user's own
actions, and the gate names the exact step instead of taking it. Issue-tracker status and comments.
The sprint retrospective, which belongs with the plan and deserves its own spec. Release tagging and
publishing, which FC-011 covers from the update side.

## Design notes

- **Where it lives.** A new `afc/ship.py` holds the gate, called by `cli_plan.cmd_done` before it
  moves anything. `plan done`'s current refusal for open slices becomes the gate's first check, so
  there is exactly one place that explains why a spec can't be finished.
- **Tests green.** Run the project's own test command from its recorded stack, never a guess. A
  project with no test command fails the gate with that as the reason — a spec whose tests were
  never run is not a finished spec.
- **`WIP` commits.** A plain `git log <base>..HEAD` scan for the prefix. Flight Control names them
  and stops; squashing them is an interactive rebase, which is a history rewrite and so the user's
  own action.
- **The changelog.** `changelog.md` in the project workspace, newest entry first, one entry per
  spec. It is written from the spec's goal and its slice labels, never from commit subjects, because
  it exists for the user to read rather than for a developer to scan.
- **Deploying.** The gate's last line is what the user runs next. Flight Control never runs it, and
  never offers to.
- **Pruning.** The Done list is compacted the way `plan done` already compacts it; the detail stays
  in the archive, so nothing is lost by pruning.

## Slices

- [ ] 1. The readiness gate — you'll check it by `sh bin/afc ship --check <id>` listing exactly what
      is missing on a project with an open slice, a failing suite and a dirty tree, then saying
      ready on a clean one (tests, one per check)
- [ ] 2. `plan done` runs the gate first — you'll check it by `plan done` refusing with the gate's
      list while the spec, the plan and the archive stay exactly as they were (tests)
- [ ] 3. The changelog entry — you'll check it by finishing a spec and reading `changelog.md` in the
      workspace: date, goal, slices, newest first (tests: one entry per spec, order, Flight
      Control's own plan included)
- [ ] 4. `WIP` commits and an unpushed branch — you'll check it by a `WIP:` commit and an unpushed
      branch each failing the gate, each naming the user's own next step (tests)
- [ ] 5. What shipped and what is next — you'll check it by finishing a spec in a live session and
      being told in two plain lines, with the next spec as step 1 (content tests and one live run)

## Decisions

- 2026-10-24: Ship deepens `plan done`. The only new command surface is `ship --check`, which
  changes nothing.
- 2026-10-24: Deploying and squashing `WIP` commits stay the user's own actions; the gate names
  them.
- 2026-10-24: The changelog is written from the spec's goal and slice labels, not commit subjects.
- 2026-10-24: A project with no test command fails the gate rather than passing it.

## Shipped
