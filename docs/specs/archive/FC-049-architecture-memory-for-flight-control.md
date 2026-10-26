# FC-049 — Architecture memory for Flight Control

Size: M · Status: done · Started: 2026-10-26 · Done: 2026-10-26
Area: flow

Found on 2026-10-26, comparing this repository with AgToosa's `docs/Master-Architecture.md`, a single
file that says what the solution is made of, which files own what, and how each claim is checked.

- Every user's app gets `plan/architecture.md` in its workspace (ten sections, from
  `templates/workspace/plan/architecture.md`). Flight Control itself has none: its structure is only
  in a folder table in `CONTRIBUTING.md` and in 49 specs, so each new spec re-discovers it.
- The template is prose only. Nothing ties a component to the files that hold it, so notes go stale
  without anyone noticing: `afc-architecture` says to update them "when structure changes", but the
  only check (`architecture_empty`) catches an untouched template and nothing after that.
- AgToosa's table names the key files and the evidence for each part. That is the piece to copy.

## Goal

Flight Control has its own architecture memory, in the same shape it gives every app. Each part is
tied to the files that hold it, and `sh bin/afc check` says when a pointer is dead or a module has
no home in the notes.

## Reaches the apps

Yes. The template every app gets (`templates/workspace/plan/architecture.md`) gains a Key files
column, the `afc-architecture` skill says to keep it current, and the same dead-pointer check runs on
each project's own notes (`afc/cli_health.py`). The unmapped-module check is Flight Control's own
(it knows its module folders); an app's notes get the dead-pointer check only.

## You'll know it works when

- A1. `docs/architecture.md` exists and has the ten sections, with a Components table whose rows name
  the key files, covering at least: hooks and guards, plan and specs, workspace and registry, update
  and release, add-ons and connectors, skills, agents and workflow, templates and rules, and
  measurements.
- A2. Its Security section lists each guard in plain words with where it is checked (the five core
  tests, or "live run"), and its Data flow section says what lives in the repository, in
  `~/.A-FC/` and in a user's code folder.
- A3. `sh bin/afc check` reports `architecture_dead_pointer` when a Key files entry names a path that
  does not exist, with the row and path; on Flight Control it reports `architecture_unmapped` for a
  new `afc/*.py` module, skill, agent or workflow that no row names.
- A4. The same dead-pointer check runs on a scratch project whose `plan/architecture.md` points at a
  file that is not in its code folder, and says nothing when every pointer exists.
- A5. `plan done` on a Flight Control spec prints one plain line when `check` finds either problem
  and never blocks; `afc-builder` and `afc-plan` are told to read `docs/architecture.md` before
  touching structure.
- A6. `docs/architecture.md` is under 500 lines and holds no secret values.

## Out of scope

Rewriting any spec. An unmapped-module check on apps (their layout is not known). Diagrams beyond the
context and containers pictures the template already asks for. Making the notes block a spec from
finishing (FC-047 does that for apps when the file is still the bare template).

## Design notes

- The Key files cell is a comma-separated list of repository-relative paths in backticks, so the
  check reads it with one pattern and needs no new syntax. Globs are not allowed; a folder path ends
  in `/`.
- "Unmapped" means a path under `afc/` (not `__pycache__`), `.claude/skills/`, `.claude/agents/` or
  `.claude/workflows/` that no Key files cell names, directly or through its folder. One folder entry
  such as `afc/hooks/` covers everything in it.
- Pointers are checked against the filesystem only; no git call, so `check` stays fast.
- For an app the check reads `plan/architecture.md` in the workspace and tests paths against the
  project's code folder. Cells with no backticked path (a fresh template) are skipped.
- Evidence column: name a live run, a command, or "one of the five core tests". Never "unit tests".
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Write the file — you'll see it by `docs/architecture.md` with the ten sections and a
      Components table naming real files for the nine areas, under 500 lines (proves A1, A2, A6)
- [x] 2. Template and skill — you'll see it by the template's Components table with a Key files
      column, and `afc-architecture` saying to keep it current after a slice that adds or removes a
      module (proves part of A4)
- [x] 3. The check — you'll see it by `check` on a scratch copy of the repo with one dead pointer and
      one new `afc/` module giving both problems, and on the real repo giving neither (proves A3, A4)
- [x] 4. Wired into the flow — you'll see it by `plan done` on a scratch Flight Control spec printing
      the line when a problem exists, and `afc-builder` and `afc-plan` naming the file (proves A5)

## Tasks

Slice 1:
- `docs/architecture.md` (new): fill from the code, not from specs; start from the template.

Slice 2:
- `templates/workspace/plan/architecture.md`: Components table gets a Key files column.
- `.claude/skills/afc-architecture/SKILL.md`: one line under "After a slice".

Slice 3:
- `afc/cli_health.py`: `_architecture_pointer_problems(path, base)` shared by Flight Control and
  projects; `_architecture_unmapped_problems(root)` for Flight Control; both added to the existing
  `_architecture_problems` flow.

Slice 4:
- `afc/cli_plan.py` `cmd_done`: one line after a Flight Control spec closes.
- `.claude/agents/afc-builder.md`, `.claude/agents/afc-plan.md`: read `docs/architecture.md` first.

## Decisions

- 2026-10-26: an app's dead-pointer check runs whether or not a slice is done; only the
  `architecture_empty` report still waits for a done slice. The check also runs on test copies of
  Flight Control, since a scratch copy is how slice 3 is proven.
- Checked 2026-10-26 on scratch copies (real plan and workspace untouched):
  - Slice 1 (A1, A2, A6): `docs/architecture.md` has ten sections and 133 lines; the Security table
    was corrected against the code (only `check_paths`, `check_secrets` and `check_git` are in the
    five core tests; the rest are live runs) and the registry is `projects.json`.
  - Slice 3 (A3, A4): a repo copy with `afc/gone.py` in a Key files cell and a new `afc/newmod.py`
    gave one `architecture_dead_pointer` (row and path) and one `architecture_unmapped`; the real
    repo gave neither. A scratch app pointing at a missing `server/routes.py` gave one dead pointer,
    and none once the file existed.
  - Slice 4 (A5): `plan done` on a scratch copy closed the spec with no note when clean, and with
    "docs/architecture.md has 1 problem(s)" when a module was unmapped; it never blocked.

## Shipped

Shipped 2026-10-26. Slices: 4. Criteria: 0 of 6 proven.
