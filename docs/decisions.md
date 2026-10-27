# Decisions

## Standing Corrections

Always/never rules the user has stated. Follow these in every slice. Only rules go here.

<!-- Example: 2026-01-01 — Never change files in the billing folder. -->

## Log

Dated entries, newest last. Each says what was decided and why. Add new entries here, at the end.

<!-- Example:
### 2026-01-01 — Use SQLite for local storage
Why: single user, no server needed. Revisit if more than one person needs it.
-->

### 2026-10-27 — FC-050 slice 5
Claude Code warns when an environment variable or a drifted agent file overrides the model for a job, and a call must not pass its own model or effort. Asking and suggesting a model in other tools is FC-052.

### 2026-10-27 — FC-050 slice 6
On a scratch project, live claude -p runs showed afc-architect on Opus, afc-build on Sonnet, and afc-docs on Haiku, matching the routing.
