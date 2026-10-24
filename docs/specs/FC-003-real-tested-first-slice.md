# FC-003 — A real, tested first slice

Size: M · Status: in progress · Started: 2026-10-24 · Done: -

Findings: 3, 19.

## Goal

Every slice, including the first, is something the user can see work, and comes with its tests.
In the live run the first slice was "Create the app…" (a page title), tests were saved for a last
"error handling and tests" slice, none were written, and slices were listed without checkboxes so
`plan` couldn't find them.

## You'll know it works when

- When a spec is written, then every slice line reads `- [ ] <n>. <label> — you'll check it by <how>`.
- When a spec's slices have no checkboxes, then `plan` says so (`"slices": "unreadable"`) instead of
  `next_slice: null`, and Claude fixes the spec before building.
- When the first slice of a new app is planned, then project setup is folded into the first real
  behavior (for php-vuln-checker: "type an address and see the PHP version it announces").
- When a slice is shown, then it comes with at least one test that ran and passed, and the test
  command and result are in the one-line summary.
- No spec contains a slice that is only "tests" or "error handling".

## Out of scope

Test coverage targets; choosing test frameworks beyond the stack's default.

## Design notes

- `templates/workspace/spec.md`: the Slices section holds a real (uncommented) example line in the
  right form, which Claude replaces.
- `afc/plan.py`: `all_slices` already exists; add a check for list items under `## Slices` that
  aren't checkboxes; `plan` reports it.
- `afc-interview`: rules for writing slices (form above; first slice is real behavior; tests belong
  in every slice). `afc-slice` checkpoint 3: refuse to show a slice with no passing test when the
  stack has tests; say why in one line if it truly can't have one.
- `afc/scan.py` could add a "tests ran" check later; not in this spec.

## Slices

- [x] 1. Spec template and `plan` unreadable-slices report — you'll check it by `plan` on a spec with
      plain `- ` lines (tests in `tests/test_plan.py`, `tests/test_cli_plan.py`)
- [x] 2. Interview rules for writing slices — you'll check it by a live run whose specs all use the
      checkbox form and whose first slice is real behavior (content tests on `afc-interview`)
- [ ] 3. Slice skill requires a passing test — you'll check it by a live slice that shows its test
      result (content tests on `afc-slice`)

## Decisions

## Shipped
