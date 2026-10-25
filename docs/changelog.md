# Changelog

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
