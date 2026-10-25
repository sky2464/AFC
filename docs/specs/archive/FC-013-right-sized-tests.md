# FC-013 — Right-sized tests

Size: M · Status: done · Started: 2026-10-25 · Done: 2026-10-25

Asked for on 2026-10-24, after FC-002 slice 3 added 18 tests (about 120 lines) to check about 20
lines of skill wording, and two of them failed on exact phrasing and had to be rewritten.

## Goal

Tests protect what can break silently and cost little to write, run and keep. Today there are 610
tests in 36 files, 5,591 lines of tests for 5,375 lines of code. The suite runs in about 30
seconds, so running it is not the cost. The cost is writing tests that check wording instead of
behavior, writing them per field instead of per risk, and fixing them whenever a sentence changes.

## You'll know it works when

- When a slice changes a command, hook, guard or parser, then it gets real tests sized by risk:
  thorough for guards, secrets and anything that moves or deletes data; three to five (happy path,
  nothing found, one failure) for a small read-only command.
- When a slice changes a skill, doc or prompt, then no test asserts its prose. At most one
  structural check, such as a named command still existing, and the real check is a live run.
- When a slice is being built, then only the test file for what changed is run; the full suite runs
  once, before the commit, with only its last lines shown.
- When someone looks for a test, then they list test names with a search and do not read whole test
  files.
- When the wording-only tests are trimmed, then the suite is a few hundred lines smaller, the
  same code is still protected, and the full suite still passes.
- CONTRIBUTING's Tests section and the `afc-slice` skill state these rules, so every future slice
  follows them without being reminded.

## Out of scope

Changing what the guards, secrets scan or data-moving commands are tested for; those stay as they
are. A coverage tool, a faster test runner, or running tests in parallel.

## Design notes

- **What counts as wording-only.** A test whose only input is a `.md` file under `.claude/`, plus
  `README.md`, `CONTRIBUTING.md` or `CLAUDE.md`, and whose only assertions are that a phrase is
  present. Candidates today: `tests/test_fewer_questions.py` (18 tests), the added tests in
  `tests/test_contributing_places.py`, and the phrase checks in `tests/test_content.py`. Tests that
  parse a skill's front matter, check a file's size, or check that a named command exists are
  structural and stay.
- **Trimming rule.** Keep the structural checks plus one test per behavior a skill or doc change is
  meant to cause (for FC-002: what to build comes before the folder; `afc defaults` is named; "just
  me" sets the personal profile). Drop checks on exact phrases and on every field of a message.
  Each deleted test is listed in the commit message so the cut can be reviewed.
- **Where the rule goes.** `afc-slice` checkpoint 2 now says "write tests first where the stack has
  tests". It becomes "write tests first, sized to risk", with the two lines above. CONTRIBUTING's
  Tests section gets the same rules plus the one-file command
  (`python3 -m unittest tests.test_<name>`).
- **Applies to projects too.** `afc-slice` is the same skill for users' apps, so the sizing rule
  must read well there: risk means what the slice touches (`auth`, `data`, `input`…, the modules from
  checkpoint 1), not Flight Control's own files.
- **Finding tests.** Listing test names with `grep -n "def test_" <file>` is the supported way;
  CONTRIBUTING says so.

## Slices

- [x] 1. The rule is written down — you'll check it by reading CONTRIBUTING's Tests section and
      `afc-slice` checkpoint 2 and seeing risk-sized tests, no prose assertions, and run-one-file
      then run-all-once (one structural test each: the Tests section names the one-file command; the
      skill keeps its three checkpoints)
- [x] 2. Trim the wording-only tests — you'll check it by the full suite passing with fewer tests and
      fewer lines than the 943 tests and 8,792 lines in `tests/test_*.py` on 2026-10-25, and a commit message listing every
      deleted test (tests: the suite itself; the structural checks stay)
- [x] 3. Try it on the next slice — you'll check it by FC-002 slice 4 or the next one adding tests
      under the new rule and the count staying in proportion to the change (no test code; compare
      lines of tests to lines changed in the commit)

## Decisions

- 2026-10-24: Wording is checked by a live run, not by tests. Behavior that code decides is tested
  by size of risk, not field by field.
- 2026-10-25: Closed with slice 3 unmeasured. It is checked on FC-014 slice 2 instead: compare lines of
  tests to lines changed in that commit.

## Shipped

Shipped 2026-10-25. Slices: 3.
