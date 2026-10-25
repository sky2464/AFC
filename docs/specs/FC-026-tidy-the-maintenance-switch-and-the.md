# FC-026 — Tidy the maintenance switch and the first question

Size: S · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-25 from findings U8 and U9 in the master plan, which no earlier spec covers.

## Goal

Two small rough edges are gone: `sh bin/afc maintain` with no word after it tells you what to type,
and the first question of a session is asked once, not twice.

## You'll know it works when

- `sh bin/afc maintain` with nothing after it answers that it needs `on`, `off` or `status`, instead
  of "Missing state."
- A session that opens with the welcome's numbered choices does not ask the same choices again in
  `afc-start`; whichever of the two speaks first is the only one that does.
- This holds in maintenance mode and in a normal session with an active project.
- The full suite passes, and the safety lines pinned by `tests/test_skill_safety_lines.py` and the
  size test on the five first-run skills (14,000 bytes) still pass.

## Out of scope

Any other `afc` command's error wording. Changing the choices themselves. The size or content of
other skills.

## Design notes

- **U8.** The error comes from the `maintain` command when its argument is missing. One test asserts
  the new wording names all three words.
- **U9.** `/afc` already says where the project stands and offers numbered steps; `afc-start` then
  offers or asks again. Decide per case which side keeps the question (the `/afc` command's summary
  when it ran, `afc-start` when a session starts without it) and say so in both texts once.
- **Stay small.** The edit to `afc-start` must not grow the five first-run skills past 14,000 bytes.

## Slices

- [x] 1. `maintain` with no state names `on`, `off` and `status` — you'll check it by a test that runs
      the command with no argument and finds all three words in the error (tests: no argument fails
      with the new text; `on`, `off`, `status` still work)
- [x] 2. The first question is asked once — you'll check it by a test over `afc-start` and the
      `/afc` command text that fails when both carry the same first numbered choice list in one
      session start, plus the size and safety-line tests still passing

## Decisions

## Shipped
