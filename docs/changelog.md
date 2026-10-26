# Changelog

## v0.05b

- Tests run only when you ask. Flight Control keeps five on the things that protect your data, and your apps get none unless you ask.
- Every spec now says how it reaches the apps Flight Control builds for you.
- There is one master plan, and it updates itself wherever the work runs.
- The test copy stays current and in its own workspace, and an empty start is quiet: no red errors, no repeated lines.
- A session starts with only the connectors a project uses, so a "hi" costs about 43k tokens instead of 60k. Ask for another in plain words.

## 2026-10-25 — FC-034 Connectors load only when needed

A Flight Control session starts with only the connectors that matter for the active project, and anything else is one plain request away. The start costs far fewer tokens, and nobody loses a connector they need.

- Where the tokens go
- A connector list per project
- Hold back the rest at start
- Ask for one in plain words
- Live check

## 2026-10-25 — FC-033 Master plan, one truth

There is one master plan: the one on `dev` (for Flight Control) or in the project's workspace (for an app). Starting, finishing and checking work updates it automatically, wherever the work runs, and no copy can disagree with it.

- Close what's built
- The build moves the plan
- One plan wherever you stand
- A stale plan is found and fixed
- Apps stay current

## 2026-10-25 — FC-032 Every spec reaches the apps

Every FC spec says how its change reaches the apps Flight Control builds, or says plainly that it can't. The rule is written into Flight Control itself, not left in notes.

- The rule and the section
- Plan flags missing sections

## 2026-10-25 — FC-031 Test copy stays current and separate

A test copy runs today's Flight Control and stays inside its own test workspace. An empty start is quiet: no red errors, no repeated lines, and any health problem is named in plain words with its fix.

- A test copy knows it is behind
- A test copy stays in its own workspace
- A quiet empty start

## 2026-10-25 — FC-030 Tests only when asked

No tests run, and none are mentioned, unless the user asks. Flight Control keeps at most five tests for itself, all on the things that can hurt a user if they break silently. Building is faster and replies are cleaner.

- Five core tests
- Building runs no tests
- Quiet replies and CI
- Projects test only when asked
- Specs say "you'll see it by"

## 2026-10-25 — FC-029 Ready for v0.04a

`main` can be released as v0.04a: `VERSION` says `v0.04a`, the release notes are in plain words, and `sh bin/afc release check` on `main` says `ready: true`. The user merges, tags and publishes.

- Ready for v0.04a

## v0.04a

- Add-ons that aren't on Flight Control's list are now really switched off in its sessions, so a start costs about a fifth fewer tokens (measured with 28 add-ons).
- The welcome says once, in one line, when it switches add-ons off.
- The health check no longer lists add-ons Flight Control already switched off.
- After an update the summary is one sentence: everything checks out, or what needs a look.
- The first reply no longer introduces Flight Control a second time.

## 2026-10-25 — FC-028 Welcome says it once

After the welcome, the first reply never repeats it. A greeting gets a short hello and the welcome's own question, without a second introduction.

- No second introduction

## 2026-10-25 — FC-027 Add-ons off at start, quiet health check

Add-ons that aren't on Flight Control's allowed list are really switched off in its sessions, without the user running anything. The health check, the welcome and the update summary speak up only about what needs the user, in a line or two.

- Honest check wording
- Switch off at session start
- Short update summary
- Live check

## 2026-10-25 — FC-026 Release check and v0.03a

Releasing is a checked, repeatable step: Flight Control says whether `main` is ready to tag, the version it reports is never older than the newest release, and the one-click update is proven on a real copy before v0.03a goes out. Publishing stays the user's own step.

- Version is never behind the newest release
- Release check
- Real update between two copies
- Ready for v0.03a

## v0.03a

- One-click updates: Flight Control tells you when a newer release is out and updates itself.
- `sh bin/afc release check` says whether `main` is ready to tag.
- The version it reports is never older than the newest release.
- Role agents, a slice build workflow and model routing for every project.
- Quicker checks: only the tests for what changed, and one full run at the end.
- `sh bin/afc slice record` ticks the spec and logs the decision in one call.
- Shorter skill text and replies; a smoother welcome.
- Optional token cost estimate by model.

## 2026-10-25 — FC-025 Token usage cost by model

The measurement script can estimate run cost from transcript models, so role and model experiments can be compared in dollars as well as tokens.

- Cost fields

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
