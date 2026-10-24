# FC-004 — Plan goal and plan editing

Size: M · Status: in progress · Started: 2026-10-24 · Done: -

Findings: 4, 7, 12.

## Goal

The master plan states its goal, and changing the plan never means hand-editing tables. In the live
run the Goal stayed empty, and reshaping the plan took `mv` on spec files plus a Python edit of
`master-plan.md`. File names were cut mid-word (`…show-it-in-th.md`).

## You'll know it works when

- When the interview writes the intent, then `sh bin/afc plan goal "<one line>"` fills `## Goal`, and
  `plan` returns it.
- When a spec is renamed with `plan rename <id> "<title>"`, then its file, its row and its heading
  change together, and the update log says so.
- When a spec is dropped with `plan drop <id>`, then it moves to the archive marked `dropped` (never
  deleted) and leaves Next.
- When `plan move <id> --to <position>` runs, then the Next order changes.
- When a title is long, then the file name is cut at a word boundary (at most 40 characters).
- The spec in Now can't be dropped or moved; it can be renamed.

## Out of scope

Merging or splitting specs; editing slice lines (Claude edits the spec file for that).

## Design notes

- Commands go in `afc/cli_plan.py` and helpers in `afc/plan.py` (both have room).
- `plan drop`: Done row with Spec `[<id>](archive/<file>)` and Done date, plus `(dropped)` after the
  title; `archive/index.md` row likewise; spec header `Status: dropped`.
- Slugs: cut at the last `-` before 40 characters when there is one.
- `afc-interview` and `afc-drift` use these commands; the drift skill never edits `master-plan.md`
  tables directly.

## Slices

- [x] 1. `plan goal` — you'll check it by setting a goal and seeing it in `plan` (tests in
      `tests/test_cli_plan.py`)
- [ ] 2. `plan rename` and word-boundary slugs — you'll check it by renaming a spec and listing
      `plan/specs/` (tests in `tests/test_plan.py`, `tests/test_cli_plan.py`)
- [ ] 3. `plan drop` and `plan move` — you'll check it by dropping and reordering specs and reading
      `master-plan.md` (tests: dropped spec archived, Now spec refused, order changes)
- [ ] 4. Interview and drift skills use the commands — you'll check it by a live pivot like the
      PHP2Shell one, with no hand edits in the transcript (content tests)

## Decisions

## Shipped
