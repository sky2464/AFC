# FC-016 — Nothing drops out of the plan

Size: S · Status: next · Started: - · Done: -

Found on 2026-10-24 while closing FC-007.

## Goal

When the master plan is compacted, rows that leave the Done table are archived, not deleted.

`plan.compact` already does this correctly for the update log: rows past the newest 100 are appended
to `archive/updatelog-<year>.md` with a header, and the file is appended to when it already exists.
The Done table gets no such treatment — `write_rows(text, "Done", done[:DONE_KEEP])` keeps the ten
newest rows and the rest are simply gone.

Closing FC-007 pushed out `PC — Project controls: remove, pause/resume, health check`, whose Spec
column was `—` because it never went through `plan done`. Nothing in the repository records it any
more; the `v0.01a` release row went the same way earlier. Only specs closed with `plan done` reach
`archive/index.md`, so every hand-added Done row is lost the moment it overflows.

## You'll know it works when

- When compaction takes rows out of the Done table, then they are appended to
  `archive/done-<year>.md` (Flight Control's `docs/specs/archive/`, a project's `plan/archive/`)
  with the same four columns, before the plan is rewritten.
- When that file already exists, then the rows are appended to it; an existing file is never
  replaced.
- When it does not exist, then it is created with a heading and a table header, the way
  `updatelog-<year>.md` is.
- When a row's Done date carries no year, then it goes to `done-unknown.md` rather than being
  dropped.
- When the archive can't be written, then the plan keeps every row and the failure is reported —
  compaction never half-finishes.
- When nothing overflows, then no archive file is created or touched.
- When the plan is compacted twice with nothing new, then the archive gains no duplicate rows.

## Out of scope

Changing how many Done rows the plan keeps (ten stays). The update log's own archiving, which
already works. `archive/index.md`, which is the per-spec index and keeps its current job.

## Design notes

- **Where it goes.** `plan.compact` in `afc/plan.py`, beside the update-log branch it mirrors. The
  year comes from the Done column — `row[2]` for a Done row, not `row[0]` as in the log branch, so
  the existing year-matching line can't just be copied.
- **Order inside the file.** Newest first, matching the Done table itself, so the archive reads like
  a continuation of the plan rather than a log.
- **Write order.** Archive first, then rewrite the plan. `compact` currently writes the plan once at
  the end; the archive write must happen before that and raise on failure, so a failed archive
  leaves a complete plan rather than a pruned one.
- **The rows already lost.** Both are recoverable from git history: `git show
  5609014^:docs/master-plan.md` holds the `PC` row, and `git show 7ae3e69^:docs/master-plan.md`
  holds the `v0.01a` row, which dropped out when FC-006 closed. Slice 3 puts them into the new
  archive file so the record is whole again.
- **FC-015.** Its design notes assume pruning keeps the detail in the archive. That is only true
  once this is built, so FC-015 depends on it.

## Slices

- [ ] 1. Done overflow is archived — you'll check it by compacting a plan with twelve Done rows and
      finding the two oldest in `archive/done-2026.md` with the plan down to ten (tests: a file
      created with its header, an existing file appended to, a row with no year, no overflow
      touching nothing, compacting twice adding no duplicates)
- [ ] 2. A failed archive leaves the plan whole — you'll check it by making the archive folder
      unwritable, compacting, and finding all twelve rows still in the plan with the reason reported
      (tests)
- [ ] 3. The lost rows are put back — you'll check it by reading `docs/specs/archive/done-2026.md`
      and finding the `PC` and `v0.01a` rows as they were in the plan (content test)

## Decisions

- 2026-10-24: Done overflow is archived to `done-<year>.md` beside `updatelog-<year>.md`; the plan
  still keeps ten rows.
- 2026-10-24: A failed archive write aborts compaction with the plan untouched, rather than pruning
  and hoping.

## Shipped
