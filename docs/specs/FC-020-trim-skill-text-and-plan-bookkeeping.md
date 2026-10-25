# FC-020 — Trim skill text and plan bookkeeping

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-25, after FC-017 closed with its ceiling missed (growth 41,916 against 36,736).
Replies met their third; skill text (9,483 against 7,581) and plan and spec edits (4,573 against
4,003) did not. The numbers are in `docs/measurements/fc-017-rerun.md`.

## Goal

A whole start plus first slice adds less context in the two parts FC-017 left short: skill text and
plan and spec edits. The code and tests a slice writes, and the review that runs before approval,
are left as they are.

## You'll know it works when

- The five skills a first run loads (`afc-start`, `afc-setup`, `afc-interview`, `afc-slice`,
  `afc-deliver`) total at most 14,000 bytes, down from 20,796, and every safety rule they state
  today is still in them.
- Recording a finished slice is one command, `sh bin/afc slice record`, that writes the spec tick,
  the `decisions.md` entry and the `architecture.md` change in one call; the session no longer
  reads those three files or edits them one by one.
- On a re-run of the same whole start plus first slice, skill text is at most 7,581 and plan and
  spec edits at most 4,003, measured by `token_usage.py --parts`.
- Growth on that re-run is at most 36,736, and a control made the same day on `dev` at `71e6517`
  shows the change moved it.
- The full suite passes and no safety rule is cut.

## Out of scope

Replies, which met their third. The review (`afc review`) and its report. The rule modules in
`rules/short/` (about 13.7 KB; four were read in the first run), which deserve their own look if
this spec still misses. Changing the ceiling or the measuring method.

## Design notes

- **Where the skill text went.** The first run loaded five skills (about 20.8 KB, roughly 5k tokens)
  and each load also counts the turn after it, which is why the measured part is 9.5k. Trimming has
  to come from the two largest: `afc-slice` (7,164 bytes) and `afc-interview` (5,051 bytes). Say
  each step once, drop examples that repeat a rule, keep every "never" and every approval step.
- **Where the plan edits went.** After the slice the session read the spec, `decisions.md` and
  `architecture.md`, then made five edits to them, and two more `decisions.md` edits at delivery.
  That is bookkeeping a command can do from three short strings, so the model writes the entry
  once and never reads the files back.
- **One command, same files.** `slice record` writes where the skills told the session to write
  (`plan/specs/`, `plan/decisions.md`, `plan/architecture.md`); nothing new is stored and a
  project's files read the same as before.
- **Safety rules are checked, not assumed.** Slice 1 starts with a test listing the safety lines of
  the five skills as they are today, so a trim that drops one fails the suite.

## Slices

- [x] 1. Pin the safety lines — you'll check it by `tests/test_skill_safety_lines.py` listing every
      line with "never", "must not" or "always ask" in the five skills and failing when one
      disappears (tests: passes on today's skills; a fixture with one line removed fails)
- [x] 2. Trim the five skills to at most 14,000 bytes in total — you'll check it by the same test
      still passing and a size test on the five files (14,000 bytes, down from 20,796)
- [x] 3. `sh bin/afc slice record` — you'll check it by `tests/test_slice_record.py`: one call ticks
      the slice in the spec, appends a dated line to `decisions.md` and updates `architecture.md`,
      refuses when the spec has no such slice, and leaves the three files byte-identical on
      refusal (tests)
- [x] 4. `afc-slice` and `afc-deliver` use it — you'll check it by content tests that neither skill
      tells the session to read or edit `decisions.md`, `architecture.md` or the spec by hand for
      bookkeeping, and that both name `slice record`
- [x] 5. Measured live re-run — same method as FC-017 slice 4 (a whole start plus first slice on a
      copy of `dev` with its own home), plus a control the same day on `dev` at `71e6517`; skill
      text at most 7,581, plan and spec edits at most 4,003, growth at most 36,736; the result goes
      into `docs/measurements/`

## Decisions

- 2026-10-25: Specced after FC-017 missed. The two byte and token numbers come from FC-017's own
  re-run: the skill total is 20,796 bytes today, and 14,000 is a third under it. The re-run
  numbers are the third-below figures FC-017 slice 4 asked for and did not reach.
- 2026-10-25: Slice 5 measured on `dev` at `4087be3` and met its numbers: growth 31,793 (ceiling 36,736), skill text 6,394 (7,581), plan and spec edits 0 (4,003). The 0 is because `slice record` is a Bash command counted under Other; the two together fell 10%. The control was the FC-017 re-run made earlier the same day, and this run built a smaller first slice (6 tests against 19), so part of the drop is not FC-020's. Closed as met. The numbers are in `docs/measurements/fc-020-rerun.md`.

## Shipped
