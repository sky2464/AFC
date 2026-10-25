# Changelog

## 2026-10-25 — FC-024 Optional TypeSafe Jev (stub)

A place to plug TypeSafe Jev later without committing to product behavior now. Off by default; always off for enterprise; shadow-only when enabled; `TYPESAFE_API_KEY` from the environment; stdlib `urllib`; mockable tests; never overrides Flight Control hard blocks.

- Isolated adapter

## 2026-10-25 — FC-023 Smoother flow and welcome fixes

Fewer wasted turns at session start and clearer maintenance commands, without changing what maintenance mode means.

- Default maintain to status
- No duplicate welcome

## 2026-10-25 — FC-022 Project role agents, workflow and init

Every new or adopted project gets role agents under `.claude/agents/`, a slice build workflow, workspace routing JSON, and a first compact brief — without manual copying.

- Install on new/adopt
- Brief on init and after deliver
- Workflow template

## 2026-10-25 — FC-021 Role agents and model routing

Dedicated role agents (research, plan, build, check) with predictable model routing so spec and slice work can use cheaper or stronger models where it helps, without changing safety guards.

- Role resolution and defaults
- Maintenance agents name models
- `sh bin/afc agents` show

## 2026-10-25 — FC-020 Trim skill text and plan bookkeeping

A whole start plus first slice adds less context in the two parts FC-017 left short: skill text and plan and spec edits. The code and tests a slice writes, and the review that runs before approval, are left as they are.

- Pin the safety lines
- Trim the five skills to at most 14,000 bytes in total
- `sh bin/afc slice record`
- `afc-slice` and `afc-deliver` use it
- Measured live re-run — same method as FC-017 slice 4 (a whole start plus first slice on a

## 2026-10-25 — FC-017 Leaner replies, plan edits and skill text

A slice adds less context in the parts Flight Control can change: replies during a build, plan and spec edits, and skill text. The code and tests a slice writes are left as they are.

- Measure the parts — the token script prints growth by part from the transcript, with a
- Plan and spec edits — the rules and skills say to edit changed lines only; you'll check it
- Shorter replies and skill text — the short rule modules and `afc-slice` say each step once
- Measured live re-run — same method as FC-009 slice 4 (a whole start plus first slice on a

## 2026-10-25 — FC-019 Checks only when needed

A spec builds in about half the time, and the full suite and the checker helper run when they can find something: risky code, a failing test, a failed CI run, or when the user asks. Safety checks on risky code stay exactly as strict as today.

- Parallel suite — `sh bin/afc test` runs every test file in parallel and prints one JSON line;
- Tests for what changed — `sh bin/afc test --changed <ref>` picks tests by changed files,
- Quick gate and risky list — the workflow runs the code gate after each builder and the
- One full suite at the end — after the last slice the workflow runs `sh bin/afc test` once
- CI — `.github/workflows/tests.yml` runs `sh bin/afc test` on pushes to `dev` and pull
- Measure the next build — build the next spec of at least three slices this way and compare

## 2026-10-25 — FC-015 Ship a finished spec

When the last slice of a spec is approved, finishing it is one safe step: Flight Control checks the spec is really finished, writes down what shipped in words the user can read, prunes the plan, and says what is next.

- The readiness gate
- `plan done` runs the gate first
- The changelog entry
- `WIP` commits and an unpushed branch
- What shipped and what is next
