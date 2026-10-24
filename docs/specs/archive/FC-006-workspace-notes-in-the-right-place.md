# FC-006 — Workspace notes in the right place

Size: S · Status: done · Started: 2026-10-24 · Done: 2026-10-24

Findings: 5, 6.

## Goal

Decisions and architecture notes land where the next session will find them. In the live run the
day's decisions were appended under "Standing Corrections" (the always/never rules), because that is
the last section of `decisions.md`, and `architecture.md` stayed the empty template although the
first slice set up the whole stack.

## You'll know it works when

- When a decision is recorded, then it goes under `## Log` as a dated entry, and Standing Corrections
  only ever hold the user's always/never rules.
- When the first slice of a project is approved, then `architecture.md` has its goal, the stack with
  versions, the main parts and how it runs.
- When the health check sees a project with done slices but a template-only `architecture.md`, then
  it reports `architecture_empty` (not auto-fixable; Claude fills it).

## Out of scope

Rewriting existing projects' `decisions.md`; diagrams.

## Design notes

- `templates/workspace/plan/decisions.md`: Standing Corrections first, then `## Log` (dated entries,
  newest last). The health repair can add a missing `## Log` heading to older workspaces.
- `afc-slice` "On yes": decisions go under `## Log`; on the first approved slice, fill
  `architecture.md` sections 1, 4 and 6 in a few lines each.
- Template-only detection: the file still matches the template text apart from whitespace.

## Slices

- [x] 1. Decisions template with `## Log` and repair for old workspaces — you'll check it by a new
      project's `decisions.md` (tests in `tests/test_content.py`, `tests/test_cli_health.py`)
- [x] 2. First slice fills the architecture notes — you'll check it by a live first slice (content
      tests on `afc-slice`). Live, from a fresh project: decisions under `## Log`; architecture
      sections 1, 4 and 6 filled; 0 heredoc writes. A first run skipped section 6 and used a script,
      so the wording was tightened and the run repeated.
- [x] 3. Health check reports an empty architecture — you'll check it by `check` on a project with a
      done slice and the template file (tests in `tests/test_cli_health.py`). The real check now
      reports `architecture_empty` for the php-vuln-checker project.

## Decisions

- 2026-10-24: "Done slice" means the project has a recorded last slice, which every approved slice
  sets. A brand-new project is never flagged.
- 2026-10-24: `architecture_empty` is reported, not fixable: Claude fills the notes from the code,
  so `repair` leaves it and `check` keeps reporting it until it is filled.
- 2026-10-24: Slice 2 was checked by live runs, not content tests (see FC-013).

## Shipped

Shipped 2026-10-24. Slices: 3.
