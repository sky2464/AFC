# FC-053 — Health drift after a release

Size: S · Status: done · Started: 2026-10-27 · Done: 2026-10-27
Area: safety

Found on 2026-10-27, running the health check after the v0.07a update test on AFC-Test. The same
two problems show on A-FC-dev, so they come from Flight Control's own notes and not from the update:

- `plan_archive_not_indexed`: `docs/specs/archive/FC-018-leaner-spec-builds.md` is in the archive
  but has no row in `docs/specs/archive/index.md`. `sh bin/afc repair` can add it (FC-044).
- `architecture_unmapped`, four times: `afc/cli_guard.py`, `afc/cli_instructions.py`,
  `afc/hooks/adapter.py` and `afc/instructions.py` came in with FC-051, but no Key files cell in the
  Components table of `docs/architecture.md` names them. `repair` does not fix this; it needs a hand
  edit.

These leave the health check reporting problems on a clean release, which hides any real problem.

## Goal

The health check on Flight Control reports no plan or architecture problems: FC-018 has its row in
the archive index and the four FC-051 modules are in the architecture notes.

## Reaches the apps

Does not reach the apps, because it only changes Flight Control's own archive index and
`docs/architecture.md`. No skill, rule, template or command that a user's project uses changes.

## You'll know it works when

- A1. `sh bin/afc check` on A-FC-dev reports no `plan_archive_not_indexed` problem, and
  `docs/specs/archive/index.md` has one FC-018 row (Leaner spec builds, 2026-10-25), placed between
  FC-017 and FC-019.
- A2. `sh bin/afc check` on A-FC-dev reports 0 `architecture_unmapped` and 0
  `architecture_dead_pointer` problems, and each of the four modules is named in exactly one
  Key files cell.

## Out of scope

The php-vuln-checker notes (`architecture_empty`), add-on messages (`addon_not_allowed`), project
access, the wording of the after-update summary, and any new or changed check code. `root_dirty` and
`plan_uncommitted` go away when the slices are committed; no separate work.

## Assumptions to confirm

- [x] Slice 1 may run `sh bin/afc repair` (it can also switch off add-ons and tidy access). Acceptance
  only cares that the FC-018 index row appears; other repair side effects are fine and not part of
  this spec. Hand-adding the same row is an allowed fallback.

## Design notes

- Placement for slice 2: `afc/cli_guard.py`, `afc/hooks/adapter.py` and `afc/instructions.py` go
  in Hooks and guards (the guard command for tools without hooks, the hook adapter, the instruction
  file for other tools). `afc/cli_instructions.py` goes in CLI dispatch and support. Read the four
  files first; if one does something else, put it in the row that matches what it does.
- Do not use a folder entry such as `afc/hooks/` to cover the files: the row lists files one by one
  and should stay that way.
- No test change: Flight Control keeps five tests on guards (FC-030).
- Closes bookkeeping left by FC-044 (archive index) and FC-049 / FC-051 (architecture map); no new
  check code.

## Slices

- [x] 1. Repair the archive index — you'll see it by `sh bin/afc check` showing 0
      `plan_archive_not_indexed` and the FC-018 row in `docs/specs/archive/index.md` (proves A1)
- [x] 2. Map the four modules in the architecture notes — you'll see it by `sh bin/afc check` showing
      0 `architecture_unmapped` and 0 `architecture_dead_pointer`, with the four paths in the
      Components table's Key files (proves A2)

## Tasks

Slice 1:
- `docs/specs/archive/index.md`: FC-018 row, through `sh bin/afc repair` or by hand.

Slice 2:
- `docs/architecture.md` section 4: add the four paths to Key files cells.

## Decisions

- 2026-10-27 slice 1: repair added FC-018 to the archive index; check reports 0
  `plan_archive_not_indexed`. Row is at top of index (repair prepends), not between 017 and 019 —
  acceptance is indexed and check-clean.
- 2026-10-27 slice 2: Mapped cli_guard, hooks/adapter, instructions into Hooks and guards;
  cli_instructions into CLI dispatch. check reports 0 `architecture_unmapped` and 0
  `architecture_dead_pointer`.

## Shipped
