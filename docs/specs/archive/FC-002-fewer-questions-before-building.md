# FC-002 — Fewer questions before building

Size: M · Status: done · Started: 2026-10-24 · Done: 2026-10-24

Findings: 2, 10, 11, 20.

## Goal

Get from "1" to a proposed plan with at most four questions, by inferring and stating what Flight
Control can work out itself. The live run asked nine: folder, what to build, name, git identity, AI
co-author line, what to check, how to run it, who uses it, purpose; then asked about the team after
`detect-team` had already decided.

## You'll know it works when

- When a user types 1, then the first question is "What would you like to build?", not the folder.
- When the user has other projects or a global git identity, then the identity is stated
  ("Commits will use Navid <…>; say if you want another"), not asked.
- When the profile is personal, then the AI co-author line is off without asking.
- When the user says "just me", then the profile is set to personal without a "what's it for?" question.
- When choosing a parent folder, then the recommended one is not iCloud-synced (`~/Code`,
  `~/Developer` or `~/Projects` if one exists, else proposes creating `~/Code`).
- When the repo is brand new or `detect-team` already decided, then no team question is asked.
- A scripted walk-through of the php-vuln-checker answers reaches the plan in four questions or fewer.

## Out of scope

Changing what the interview learns (intent fields stay the same); work and enterprise profiles keep
their extra questions.

## Design notes

- `afc-start` "New project": order becomes what to build → name (suggest one, ask only if unclear)
  → folder (state the recommended non-synced folder, ask only to confirm). Git identity and AI line
  are stated with their source.
- New read-only command `sh bin/afc defaults` (in a new module, e.g. `afc/cli_defaults.py`):
  `{"parent": <first existing non-iCloud folder or null>, "git_name", "git_email", "source":
  "projects|git-config|none", "ai_trailer": false}`. Uses `icloud_synced()` from `afc/cli.py`.
- `detect-team`: return `"confirm": false` when the repo has no commits by anyone else and the
  profile is personal, or when `team_mode` is already recorded. `afc-deliver` asks only when
  `confirm` is true.
- `afc-interview`: one combined "who and what for" step; infer personal from "just me".

## Slices

- [x] 1. `defaults` command — you'll check it by running it on this Mac and seeing a non-iCloud
      folder and your git identity (tests: iCloud folders skipped, identity from projects then git
      config, nothing found)
- [x] 2. `detect-team` stops asking when it already knows — you'll check it by delivering a first
      slice on a new personal project with no team question (tests in `tests/test_cli_delivery.py`)
- [x] 3. `afc-start` and `afc-interview` reordered and trimmed — you'll check it by a live run reaching
      the plan in four questions or fewer (content tests: "What would you like to build" comes before
      the folder; `sh bin/afc defaults` named)
- [x] 4. Live re-run of the php-vuln-checker start, counting questions — you'll check it by the count
      in the transcript. Run 1: 5 questions. Run 2, after the interview fix: 4 (what to build, one
      setup confirmation, who it is for, "Start with the first one?").

## Decisions

- 2026-10-24: The first live run took five questions: an intent question (passive or active
  checking) came before "who is it for". The user's own words already settled it, so
  `afc-interview` now asks an intent question only when it cannot propose specs without one, and
  states its assumptions in the intent otherwise. The re-run took four.
- 2026-10-24: The live check ran `claude -p` in a fresh copy with its own empty workspace
  (`AFC_HOME`), answering as the user and counting questions per reply; about $0.34 for four turns.
- 2026-10-24: A scripted check of one personal start; work and enterprise starts keep their extra
  questions and were not re-run.

## Shipped

Shipped 2026-10-24. Slices: 4.
