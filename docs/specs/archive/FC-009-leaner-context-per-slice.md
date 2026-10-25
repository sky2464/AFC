# FC-009 — Leaner context per slice

Size: M · Status: closed, target not met · Started: 2026-10-24 · Done: 2026-10-25

Finding: 14.

## Goal

A slice costs much less context. The live run used about 101k tokens to set up the project and build
one small slice: full skill texts loaded several times, five full rule modules, two web searches and
long shell outputs.

## You'll know it works when

- A measured repeat of the php-vuln-checker start plus first slice grows its context at least a third
  less than the first run did: peak context minus the first turn's context (the floor, which Flight
  Control does not control), measured from the session transcript's token counts.
- Rule modules have a short form (Do and Never, at most about 25 lines each) that Claude reads by
  default; the long form stays for review.
- No skill is loaded twice in a row for the same step.
- Command outputs Claude doesn't need stay small (for example `plan` and `status` without echoing
  paths it already has).

## Out of scope

Changing models or effort settings; removing safety rules.

## Design notes

- Measure first: a small script in `docs/` notes (not shipped) that sums token usage from a
  transcript JSONL, run on the first live session as the baseline.
- `rules/*.md`: add a `## Short` section at the top; `sh bin/afc modules` returns the short form path
  by default and the full one with `--full`.
- Skills: move rarely used parts (enterprise, remotes, Azure) out of the always-loaded skills into
  ones loaded only when needed.
- FC-005's "no `cat` of rules" already removes the biggest single block.

## Slices

- [x] 1. Baseline measurement — you'll check it by a written number for the first live run
- [x] 2. Short rule modules — you'll check it by `modules` returning short paths (tests in
      `tests/test_content.py` for the size limit, `tests/test_cli.py` for `--full`)
- [x] 3. Trim always-loaded skills — you'll check it by skill line counts going down with the content
      tests still passing
- [ ] 4. Measured live re-run — you'll check it by `python3 docs/measurements/token_usage.py
      <baseline> <rerun>` showing growth above the floor at or below 24,490 (a third under the
      baseline's 36,736), with each run's floor beside it (tests in `tests/test_token_usage.py`).
      Measured 2026-10-24: 46,010, not met. Closed 2026-10-25; the rest goes to FC-017.

## Decisions

- 2026-10-24: The short form is a separate file per module, `rules/short/<name>.md`, not a
  `## Short` section in the long file: `modules` hands out a path, so a section inside the same file
  would still be read in full. It is derived from the long file (title, Do and Never) by
  `afc/rules.py`, so the long file stays the only place a rule is edited; regenerate with
  `python3 -m afc.rules`, and a test fails if a short file drifts.
- 2026-10-24: The short-form line limit is 30, not "about 25": nine modules fit in 25 and `identity`
  needs 29. No safety rule was cut to meet the number.
- 2026-10-24: The saving is small on its own: about 22% of the rule text, roughly 440 tokens for an
  auth slice, under half a percent of the 101k baseline. The one-third target depends on slices 3
  and 4.
- 2026-10-24: Parts of a skill that apply only in one situation moved into skills of their own, so
  they load only when needed: `afc-setup` (new or existing project, out of `afc-start`),
  `afc-remote` (creating a remote, opening a team pull request, out of `afc-deliver`) and
  `afc-profile` (the profile questions, out of `afc-interview`). The text moved verbatim; the
  tests that read it now read the new skill with every assertion unchanged. `afc-slice` is left
  alone: the FC-010 tests pin its wrong-spec rules and every other line is used on every slice.
- 2026-10-24: Measured against the committed skills, a returning session loads about 630 tokens
  less and each solo delivery about 320 less; a new personal project about 260 less. Two rare
  paths cost more: a new work project about 190 and a first delivery that needs a remote about 120.
  The three new skill descriptions and their routing rows add about 115 tokens to every session.
  The four main skills together went from 22.8k to 17.6k characters, still above the 16.3k they
  were at the first live run. `tests/test_skill_split.py` sets ceilings so they don't grow back.
- 2026-10-24: Slice 4's target needs a second look before it is run. The baseline transcript shows
  64,312 tokens of context at turn 1, before any Flight Control skill loaded, and "a third fewer"
  means a peak of 67,365 or less, so only about 3k tokens above that floor are left for everything
  the session does. The floor is mostly the system prompt, tool definitions and the plugin and skill
  listings, which this repo does not control. Decided the same day: slice 4 measures only what the
  session adds above its own first turn ("growth": peak context minus first-turn context), and the
  target is a third less growth than the baseline's 36,736, so 24,490 or less. Judging growth also
  keeps the comparison fair when the re-run's floor differs, for example because more or fewer
  plugins are loaded; the floors are shown beside the result.
- 2026-10-24: Slice 4's re-run was measured (headless, `dev` at `973da0c`, Sonnet 5.5): growth 46,010
  against a target of 24,490, so the target is not met and slice 4 stays open. The baseline's first
  slice was a skeleton and FC-003 made it a real tested slice, so the two runs don't build the same
  thing; two whole runs from before slices 2 and 3 grew 44,274 and 46,689, so those slices moved the
  number by less than the spread between runs. The numbers, where the growth went and a fix to the
  whole-run check are in `docs/measurements/fc-009-baseline.md`.

## Shipped

## Shipped

Closed 2026-10-25 without meeting its target. Slices 1 to 3 shipped; slice 4 was measured on
2026-10-24 and missed (growth 46,010 against 24,490). The result and the breakdown are in
`docs/measurements/fc-009-baseline.md`. The parts not yet done are specced in FC-017.
