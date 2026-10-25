# FC-017 — Leaner replies, plan edits and skill text

Size: M · Status: done · Started: 2026-10-25 · Done: 2026-10-25

Asked for on 2026-10-25, after FC-009 was closed with its target missed. The re-run that missed
(dev `973da0c`) grew 46,010 against a target of 24,490. Its growth is in `fc-009-baseline.md`: code
and tests written (about 9.5k, intended work), the model's replies (about 9.5k), skill text (about
5.7k), plan and spec edits (about 5.2k), and files and rules read (about 5.5k). Those parts were
estimated by hand from the transcript. Slice 1 measures them properly.

## Goal

A slice adds less context in the parts Flight Control can change: replies during a build, plan and
spec edits, and skill text. The code and tests a slice writes are left as they are.

## You'll know it works when

- The measuring script reports growth by part (code and tests, replies, skill text, plan and spec
  edits, files read, other) from the transcript, not by hand.
- On a re-run of the same whole start plus first slice, replies, plan and spec edits, and skill
  text each grow at least a third less than in the FC-009 re-run, measured by the same script.
- Growth on that re-run is at most 36,736, the baseline's own growth. This is a ceiling, not the
  FC-009 target.
- No skill is loaded twice in a row for the same step.
- The full suite passes, and no safety rule is cut.

## Out of scope

Code and tests a slice writes; changing models or effort settings; removing safety rules; the
first real tested slice that FC-003 added.

## Design notes

- Replies: during a build, the reply is a status line and at most one question. No restating the
  plan, which the pinned task list already shows. Enforced through the short rule modules from
  FC-009 slice 2 and the `afc-slice` skill.
- Plan and spec edits: change the lines that change with the file edit tool, not a rewrite of the
  whole file. `afc plan` already prints only the parts a step needs.
- Skill text: each step is stated once in the skill. A skill is loaded again only when the step
  changes.

## Slices

- [x] 1. Measure the parts — the token script prints growth by part from the transcript, with a
      fixture transcript covering each part (tests in `tests/test_token_usage.py`); run on the
      FC-009 transcript pair, the breakdown is printed.
- [x] 2. Plan and spec edits — the rules and skills say to edit changed lines only; you'll check it
      by content tests and by the plan-and-spec share falling on a re-run of the breakdown.
- [x] 3. Shorter replies and skill text — the short rule modules and `afc-slice` say each step once
      and keep build replies to a status line and one question; you'll check it by content tests
      and by the reply and skill-text shares falling on a re-run.
- [x] 4. Measured live re-run — same method as FC-009 slice 4 (a whole start plus first slice on a
      copy of `dev` with its own home); growth at most 36,736 and each part a third below the
      FC-009 re-run; the result goes into `docs/measurements/`.

## Decisions

- 2026-10-25: The ceiling is the baseline's growth, 36,736. The same-kind FC-009 runs spread between
  44,274 and 46,689, so a tighter number would be judged on noise. Change it if a different number
  is wanted.

## Shipped

Shipped 2026-10-25. Slices: 4.
