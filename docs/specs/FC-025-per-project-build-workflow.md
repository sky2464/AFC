# FC-025 — Per-project build workflow

Size: M · Status: next · Started: - · Done: -

Asked for on 2026-10-25, to mirror `afc-build-spec.js` for user projects building `S-…` slices with
helpers instead of only the main `afc-slice` session.

## Goal

Flight Control ships a template workflow `afc-build-slice.js` that projects copy into
`.claude/workflows/` at init or sync, running one builder and one checker per project slice with
models from project routing (`FC-021` / `FC-022`).

## You'll know it works when

- A template file lives in the Flight Control repo at
  `.claude/workflows/afc-build-slice.js` (or `templates/workflows/` copied by sync — path in
  Decisions when built).
- `sh bin/afc agents sync` (or a dedicated `workflows sync`) installs it into the active project's
  `code_path/.claude/workflows/afc-build-slice.js` when missing or outdated.
- The workflow accepts `slice` (S-spec id and slice number or text), uses `afc-build` and
  `afc-check` agent types, resolves models from workspace `routing.json`, runs the project's test
  command via `sh bin/afc test` from the project root, and allows at most two fix rounds like
  `afc-build-spec.js`.
- Meta `whenToUse` states it is for project `S-…` slices, not FC maintenance specs.
- Structural tests assert required args, max fix rounds, and that checks quote the slice line from
  the project spec under `plan/specs/`.
- Documentation in `afc-slice` skill mentions the workflow as optional for multi-slice project
  builds; default path remains main-session `afc-slice`.

## Out of scope

Changing `afc-build-spec.js` for FC specs. Mandatory use of helpers for every user slice. Cloud
Agent or CI execution. Per-slice risky-path logic copied verbatim from FC repo (project risky list
may be shorter, defined in Decisions).

## Design notes

- **Parity.** Reuse patterns from `afc-build-spec.js`: `sh()` helper, safety list adapted for
  project code_path only, checker runs suite itself, builder returns last suite lines.
- **Specs.** Project specs live in workspace `plan/specs/S-NNN-….md`; workflow reads via path passed
  in args.
- **Tests.** `bin/afc test` with `--changed` when the template supports it; full suite once at end
  optional flag `finalSuite: true`.
- **Guards.** Workflow does not bypass Flight Control pretool; writes stay under `code_path` and
  workspace.

## Slices

- [ ] 1. Template workflow — you'll check it by the template file existing and a structural test for
      args, two fix rounds max, and builder/checker agent types (tests)
- [ ] 2. Install on sync — you'll check it by `tests/test_workflows_sync.py` copying into a temp
      project `.claude/workflows/` (tests)
- [ ] 3. Routing-aware models — you'll check it by a structural test that the workflow source reads
      routing or delegates to host resolution when models omitted (tests)
- [ ] 4. Skill mention — you'll check it by a content test on `afc-slice` naming `afc-build-slice`
      and stating main-session build remains the default

## Decisions

- 2026-10-25: Template ships from the Flight Control install; projects receive a copy, not a symlink.

## Shipped
