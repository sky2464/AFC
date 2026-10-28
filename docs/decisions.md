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

### 2026-10-27 — FC-052 slice 1
sh bin/afc model names the running tool and the model from its plain local settings: Cursor composer-2.5 from cli-config.json, Codex gpt-6.1-sol from config.toml, Copilot and Antigravity not shown. First four assumptions settled.

### 2026-10-27 — FC-052 slice 2
Three options (premium, best cost, hybrid) from local settings plus a timed public look-up, with machine cache fallback; never invent or ship model IDs.

### 2026-10-27 — FC-053 slice 1
repair added FC-018 to the archive index; check reports 0 plan_archive_not_indexed. Row is at top of index (repair prepends), not between 017 and 019 — acceptance is indexed and check-clean.

### 2026-10-27 — FC-053 slice 2
Mapped cli_guard, hooks/adapter, instructions into Hooks and guards; cli_instructions into CLI dispatch. check reports 0 architecture_unmapped and 0 architecture_dead_pointer.

### 2026-10-27 — FC-054 slice 1
Cursor conversation IDs fall back to the branch switch; /afc mm with CURSOR_CONVERSATION_ID sets branch, not a per-chat flag. guard --write allows A-FC.

### 2026-10-27 — FC-054 slice 2
maintain status returns applies and note in plain words; /afc mm command text uses applies.

### 2026-10-27 — FC-054 slice 3
deliver in MM commits afc_root; set last_slice and index refresh skip the active project.
