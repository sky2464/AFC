# FC-006 — Workspace notes in the right place

Size: S · Status: in progress · Started: 2026-10-24 · Done: -

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
- [ ] 2. First slice fills the architecture notes — you'll check it by a live first slice (content
      tests on `afc-slice`)
- [ ] 3. Health check reports an empty architecture — you'll check it by `check` on a project with a
      done slice and the template file (tests in `tests/test_cli_health.py`)

## Decisions

## Shipped
