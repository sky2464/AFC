# FC-022 — Project role agents at init

Size: M · Status: next · Started: - · Done: -

Asked for on 2026-10-25, after FC-021 defines repo role agents and workspace routing; projects need
the same helpers locally when code lives outside the Flight Control repo.

## Goal

Every project gets its own `.claude/agents/` copies of the four role agents and a workspace
`routing.json` when it is created or adopted. A sync command refreshes them when the repo templates
change, without touching project-specific routing overrides the user already set.

## You'll know it works when

- After `sh bin/afc new` or `sh bin/afc adopt`, the project's `code_path` contains
  `.claude/agents/` with the four role agent files and a starter `routing.json` (empty overrides or
  commented keys only) in the project workspace, not inside the app repo unless `code_path` is the
  app folder — agents ship under `code_path/.claude/agents/` per project layout in `afc-setup`.
- Agent bodies match the repo templates from FC-021 at sync time; frontmatter `model` in the project
  copy reflects repo defaults until the user overrides via `routing.json`.
- `sh bin/afc agents sync` copies or updates agent files from the Flight Control install into the
  active project's `.claude/agents/`, leaves `routing.json` override values intact, and reports what
  changed in plain text.
- Sync refuses when there is no active project or when `code_path` is missing; it does not create
  agents outside the active project's tree.
- Tests cover `new`, `adopt` and `sync` on a temp project without a live Claude session.

## Out of scope

Defining the four roles and default models (`FC-021`). Token measurement (`FC-023`). Generating
compact context (`FC-024`). Project build workflows (`FC-025`). Copying Flight Control's own
`.claude/workflows/` into user projects (maintenance workflows stay in the A-FC repo).

## Design notes

- **Templates.** Source of truth is `.claude/agents/afc-{research,plan,build,check}.md` in the
  Flight Control install; `agents sync` reads from `sh bin/afc home` or equivalent path helper.
- **Init.** `new` and `adopt` call the same internal helper so adopt of an existing folder does not
  skip agents when `.claude/` was never there.
- **routing.json.** Written under workspace (`~/.A-FC/<id>/routing.json`) on init; FC-021's
  `routing set` continues to edit that file. If a project keeps agents only under `code_path`, document
  one canonical place in Decisions when built.
- **Merge policy.** Sync overwrites agent file content when the template hash differs; it never deletes
  extra agent files the user added unless a future spec says so.
- **Guards.** Pretool rules already treat `.claude/agents/` as sensitive in the FC repo; project
  copies follow the project's code_path guard, not maintenance mode.

## Slices

- [ ] 1. Sync helper — you'll check it by `tests/test_agents_sync.py`: copies four templates into a
      temp `code_path`, updates changed content on second sync, does not wipe `routing.json`
      overrides (tests)
- [ ] 2. `afc new` installs agents — you'll check it by an integration test that runs `new` with a
      fixture home and finds four agents under the new project's `code_path` (tests)
- [ ] 3. `afc adopt` installs agents — you'll check it by the same for adopt on an existing empty
      directory (tests)
- [ ] 4. CLI `agents sync` — you'll check it by command tests wired to the helper, including refuse
      when no active project (tests)

## Decisions

- 2026-10-25: Agents live under each project's `code_path/.claude/agents/`; routing stays in the
  workspace unless implementation finds one folder works better for both.

## Shipped
