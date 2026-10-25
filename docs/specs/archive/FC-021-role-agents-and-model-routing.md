# FC-021 — Role agents and model routing

Size: M · Status: done · Started: 2026-10-25 · Done: 2026-10-25

Research on Haiku, plan on Opus, build on Sonnet, check on Haiku (Sonnet optional). Explicit `model:` per agent file; per-project overrides in workspace `agents/routing.json`. Main session stays off Haiku. Bedrock/Vertex need full model IDs; Haiku 5.5 needs Claude Code >= v2.1.293.

## Goal

Dedicated role agents (research, plan, build, check) with predictable model routing so spec and slice work can use cheaper or stronger models where it helps, without changing safety guards.

## You'll know it works when

- Maintenance repo agents `afc-research`, `afc-plan`, `afc-builder`, `afc-checker` each declare `model:` in frontmatter with the defaults above.
- `afc/role_agents.py` resolves models from defaults plus workspace `agents/routing.json`.
- `sh bin/afc agents` on an active project prints resolved models and the routing file path.
- Enterprise profile forces Jev off in routing summary even if enabled in JSON.
- Tests cover overrides, frontmatter, and enterprise Jev.

## Out of scope

The per-project install path (FC-022). Token cost estimates (FC-025). Jev calls (FC-024).

## Slices

- [x] 1. Role resolution and defaults — you'll check it by `tests/test_role_agents.py`
- [x] 2. Maintenance agents name models — you'll check it by `tests/test_build_helpers.py` (`test_agents_name_a_model`)
- [x] 3. `sh bin/afc agents` show — you'll check it by `tests/test_project_agents.py` and CLI wiring in `afc/cli_agents.py`

## Decisions

- 2026-10-25: Research FC-019..FC-024 IDs collide with shipped FC-019/FC-020; this work uses FC-021+.

## Shipped

Shipped 2026-10-25. Slices: 3.
