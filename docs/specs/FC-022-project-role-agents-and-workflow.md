# FC-022 — Project role agents, workflow and init

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

## Goal

Every new or adopted project gets role agents under `.claude/agents/`, a slice build workflow, workspace routing JSON, and a first compact brief — without manual copying.

## You'll know it works when

- `sh bin/afc new` and `adopt` install agents, `afc-build-slice.js`, and `agents/routing.json`, and refresh `resources/afc-brief.md`.
- `sh bin/afc agents sync` rewrites agent files from templates with current routing.
- Session start context names the brief path when it exists.
- `afc-slice` tells the session to read the brief once per slice.

## Out of scope

Full multi-slice automated builds in the main session (workflow is there to run by name). Jev.

## Slices

- [x] 1. Install on new/adopt — you'll check it by `tests/test_project_agents.py` and `afc/project_agents.py`
- [x] 2. Brief on init and after deliver — you'll check it by `tests/test_context_brief.py` and deliver returning `brief`
- [x] 3. Workflow template — you'll check it by file at `templates/project/workflows/afc-build-slice.js` copied into the code tree

## Decisions
