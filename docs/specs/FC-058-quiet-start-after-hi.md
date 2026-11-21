# FC-058 — Quiet start after hi

Size: M · Status: next · Started: - · Done: -
Area: flow

FC-056 shipped the pick-first welcome (names only, no last slice in the banner). Live tests on
2026-10-28 still showed a noisy or blocked first reply: superpowers' start text competed with
`afc-start`, the user's Explanatory output style produced "★ Insight" boxes, health notes misnamed
missing folder access as "leftover … from an old project", updates told terminal users to type
`/exit`, and `sh bin/afc check` on a copy on `main` still listed Flight Control's own plan
bookkeeping. The scoreboard still has first-start tokens above the 50k flow target (56,247).

## Goal

After "hi", the session hears Flight Control only: no rival start skill, no insight boxes, health
notes that name the right project and come before the welcome question, update restart steps that
fit where the update ran, and no Flight Control plan noise on user copies on `main`.

## Reaches the apps

Yes. Session start, health check, update apply, and project settings are shared for every user.

## You'll know it works when

- A1. A new Claude Code session's hook context has 0 lines containing "EXTREMELY_IMPORTANT" from
  superpowers when superpowers is not on `afc-addons.json`'s allowed list.
- A2. Flight Control's `.claude/settings.json` sets `"outputStyle": "default"` so sessions in this
  folder do not inherit the user's Explanatory style; 3 first replies after "hi" contain 0 "★
  Insight".
- A3. With `php-vuln-checker` active and both project folders missing from Claude access, the welcome
  context health line names that project and says folders are not open yet; it contains 0 "old
  project" and tells Claude to say it before the welcome question.
- A4. On a scratch clone on `main`, `sh bin/afc check` reports 0 problems whose kind is
  `plan_archive_not_indexed`, `architecture_unmapped` or `architecture_dead_pointer` for Flight
  Control's plan; on `dev` they still appear when the map is behind.
- A5. `sh bin/afc update` applied from a plain shell (no Claude Code session env) returns
  `restart_how` that does not mention `/exit`; the same update from Claude Code keeps today's
  restart words.
- A6. Three fresh "hi" sessions on a copy at this version get the welcome question with no safeguard
  stop before the reply; outcomes are logged in Decisions.

## Out of scope

Changing Anthropic safeguard thresholds. Renaming `php-vuln-checker`. Editing the user's global
`~/.claude/settings.json`. Making `AFC-Test` a real isolated test home (user set-up). Re-measuring
the full 50k token target in this spec (note result in Decisions only).

## Assumptions to confirm

- [ ] superpowers comes off `afc-addons.json`; `afc-capabilities` documents writing skills without
  invoking the superpowers plugin (user's add-on elsewhere stays allowed).
- [ ] `outputStyle: default` in the project settings is enough; no per-hook change.

## Design notes

- Slice 1: `afc-addons.json` empty allowed list or drop superpowers; confirm SessionStart has no
  superpowers injection in a live start (A1).
- Slice 2: `.claude/settings.json` add `outputStyle`; live three "hi" replies (A2).
- Slice 3: `_health_line` splits `missing_access` (name the active project, "not open yet") from gone,
  foreign and stale ("leftover"); timing instruction stays "before the welcome question" (A3).
- Slice 4: `find_problems` — Flight Control `plan_problems` and `_findings_problems` only when
  `on_main()` is false (A4).
- Slice 5: `update_apply.RESTART_HOW` chosen by whether `detect_tool() == "claude"` (A5).
- Slice 6: live sessions (A6). No new core guard test file unless a slice adds a small unit test
  (welcome/health wording may use `tests/test_welcome_pick.py` pattern).

## Slices

- [ ] 1. No rival start skill — you'll see it by a live session start with superpowers off the
      allowed list and 0 "EXTREMELY_IMPORTANT" in the hook context (proves A1)
- [ ] 2. Default output style — you'll see it by 3 "hi" replies with 0 "★ Insight" (proves A2)
- [ ] 3. Plain health note — you'll see it by scratch `missing_access` context wording (proves A3)
- [ ] 4. Plan noise only on dev — you'll see it by `check` on scratch `main` vs `dev` (proves A4)
- [ ] 5. Restart words that fit — you'll see it by `restart_how` from shell vs Claude update (proves A5)
- [ ] 6. Live hi check — you'll see it by 3 sessions logged in Decisions (proves A6)

## Tasks

Slice 1: `afc-addons.json`, `.claude/skills/afc-capabilities/SKILL.md`.
Slice 2: `.claude/settings.json`.
Slice 3: `afc/hooks/session_start.py` (`_health_line`).
Slice 4: `afc/cli_health.py` (`find_problems`).
Slice 5: `afc/update_apply.py`.
Slice 6: live runs; `docs/decisions.md`.

## Decisions

## Shipped