# FC-030 — Tests only when asked

Size: M · Status: next, ready for build

Asked for on 2026-10-25. FC-013 (right-sized tests) and FC-019 (checks only when needed) made the
suite cheaper to run, but it kept growing, and test talk still fills every reply. Where it stands
today on `dev`:

- **1,049 tests in 78 files, 10,440 lines**: about as much test code as Flight Control itself.
  The full run takes about 60 seconds. FC-013 started at 610, FC-019 at 947, so each spec that
  trimmed the cost was outgrown within a day.
- **Tests run without being asked, everywhere:**
  - the build workflow's gate runs the slice's tests;
  - each builder runs the changed tests before committing;
  - the checker runs the full suite;
  - the workflow runs the full suite again at the end;
  - the release check runs it;
  - two GitHub workflows run it, one on three systems and two Python versions;
  - `/afc` in maintenance mode checks the last GitHub run.
- **Every reply reports it.** "All 1,049 tests pass" shows up at the end of jobs that only changed
  a spec, where it tells the user nothing.
- **Projects pay the same cost.** `afc-slice` won't show a slice until a test for it has run and
  passed, so tests get written first. The delivery gate in `afc/ship.py` refuses to deliver when no
  test command is recorded. Each spec's slice line names a test as "you'll check it by".

## Goal

No tests run, and none are mentioned, unless the user asks. Flight Control keeps at most five tests
for itself, all on the things that can hurt a user if they break silently. Building is faster and
replies are cleaner.

## You'll know it works when

- `tests/` holds at most five tests, and `sh bin/afc test` runs them in a few seconds. The others
  are removed; git history keeps them if one is ever wanted back.
- Building an FC spec runs no tests: not the gate, the builders, the checker, the end of the
  workflow or the release check. A slice is shown when it works in a live run.
- Tests run only when the user asks ("run the tests", "test it", `sh bin/afc test`), and then only
  the five.
- Replies never mention tests or test counts unless the user asked for a run, or a run they asked
  for failed.
- `/afc` in maintenance mode no longer checks or reports GitHub test runs.
- GitHub runs the same five tests once, on one system, only for pull requests to `main`.
- In a user's project, `afc-slice` shows a slice once it works in a live run. It writes tests only
  when the user asks for them, and delivery no longer needs a test command.
- New spec slices say "you'll see it by" (a live run or a command's output), not "you'll check it
  by" a test. The open specs in Next are rewritten to match.

## Out of scope

Removing the safety guards themselves. Guards stay exactly as they are; only their test files go.
Changing what the guards, secret check or path rules do. Adding a new test tool.

## Design notes

- The five tests, one each, each guarding a silent failure that would hurt a user:
  1. the path guard keeps code writes inside the active project's code folder;
  2. the secret check blocks a line that looks like a key;
  3. the risky-git guard blocks force-push and branch deletion;
  4. remove moves a project into `~/.A-FC/removed/` and deletes nothing;
  5. the start hook always prints a welcome, even with a broken registry.

  Put them in one file, `tests/test_core.py`, with the helpers they need. Remove the rest of
  `tests/` and `tests/fixtures/` once nothing uses them.
- Places that run or require tests today:
  - `.claude/workflows/afc-build-spec.js` (gate, final suite, checker suite);
  - `afc/gate.py` (`pick_tests` / `run_files`);
  - `.claude/agents/afc-builder.md` and `afc-checker.md`;
  - `afc/ship.py` (`tests_green`, `NO_TEST_COMMAND`);
  - the release check;
  - `.github/workflows/ci.yml` and `tests.yml`;
  - `sh bin/afc ci` and its step in `.claude/commands/afc.md`;
  - `.claude/skills/afc-slice/SKILL.md`;
  - the test lines in `rules/` (for example `rules/architecture.md`, `rules/api.md`,
    `rules/data.md`);
  - `CONTRIBUTING.md` (Tests, release steps);
  - the master plan's intro ("the full suite passing");
  - `.github/pull_request_template.md`.
- `afc/testrun.py` and the `--changed` picking go away with the gate's test run, unless
  `sh bin/afc test` still needs them for five tests (it shouldn't).
- Each slice is checked by trying it, not by a new test.

## Slices

- [x] 1. Five core tests — you'll see it by `sh bin/afc test` running five tests and passing in a
      few seconds, with the rest of `tests/` gone
- [x] 2. Building runs no tests — you'll see it by a build of a one-line FC slice finishing with no
      test run in its log, and no test count in its summary
- [x] 3. Quiet replies and CI — you'll see it by `/afc` in maintenance mode showing no GitHub test
      line, and GitHub running only the five on a pull request to `main`
- [x] 4. Projects test only when asked — you'll see it by a live slice in a test project that
      shows a working change with no test written, and delivers it without a test command
- [x] 5. Specs say "you'll see it by" — you'll see it by the spec template, `CONTRIBUTING.md` and
      the open specs in Next all using it

## Tasks

Slice 1, five core tests:
- Write `tests/test_core.py` with the five tests from the design notes. Each builds its own
  temporary `AFC_HOME` and code folder, with no shared fixtures.
- Delete every other `tests/test_*.py`, plus `tests/helpers.py` and `tests/fixtures/` if
  `test_core.py` doesn't use them.
- `afc/cli_test.py`: `sh bin/afc test` runs `tests/` in one process, prints `{"passed": n,
  "failed": n}` plus any failure's last lines, and drops `--changed`.
- Delete `afc/testrun.py` and its uses (`afc/cli_test.py`, `afc/gate.py`).

Slice 2, building runs no tests:
- `afc/gate.py`: remove the test pick and run. The gate checks the tagged commit, the ticked box,
  that no line looks like a secret, and that files stay in the repo.
- `.claude/workflows/afc-build-spec.js`: drop the "Final suite" phase and the `suite` fields from
  both schemas. Builder and fix prompts no longer run tests; the checker prompt no longer runs the
  suite, and `pass` depends only on its problems.
- `.claude/agents/afc-builder.md`: replace "write the test first" and the test-run lines with "try
  the change for real (run the command, start the hook) before committing".
  `.claude/agents/afc-checker.md`: drop "run the full suite".
- `afc/cli_ship.py` and `afc/ship.py`: the release path no longer runs `FC_TEST_COMMAND`. Remove
  that constant.

Slice 3, quiet replies and CI:
- `.claude/commands/afc.md`: remove the `sh bin/afc ci` step from maintenance mode. Delete
  `afc/ci_status.py` and the `ci` command in `afc/cli.py` and `afc/cli_parser.py`.
- `.github/workflows/`: delete `ci.yml`. In `tests.yml`, run `sh bin/afc test` on `ubuntu-latest`
  only, on `pull_request` to `main`.
- `.github/pull_request_template.md`: drop the "Tests pass locally" box.
- `CLAUDE.md`: under Simple by default, add one line: "Never mention tests or test counts unless the
  user asked for a run, or a run they asked for failed."
- `docs/master-plan.md`: drop "and the full suite passing" from the intro.

Slice 4, projects test only when asked:
- `.claude/skills/afc-slice/SKILL.md`: replace the test lines (49–55, 70–76) with this: show a slice
  once it works in a live run; write or run tests only when the user asks; a bug gets a hypothesis
  and a live reproduction. Keep the skill at its size limit or under.
- `afc/ship.py`: delivery no longer calls `tests_green` and no longer needs `NO_TEST_COMMAND` or
  `recorded_test_command`. Remove them and the `Test command:` lookup.
- `rules/architecture.md`, `rules/api.md`, `rules/data.md` and any other `rules/*.md` "Tests:"
  line: change each to a "Check:" line saying what to try live. Keep the safety rule itself.
- `.claude/skills/afc-interview/SKILL.md`: the slice line format drops "(tests: <what>)".

Slice 5, "you'll see it by":
- `templates/workspace/spec.md`, `.claude/skills/afc-interview/SKILL.md`,
  `.claude/agents/afc-plan.md` and `CONTRIBUTING.md` (slice line, Tests section, release steps):
  "you'll check it by <test>" becomes "you'll see it by <live run or command output>". The Tests
  section in `CONTRIBUTING.md` becomes three lines: the five tests, `sh bin/afc test`, run when
  asked.
- Rewrite the slice lines of the open specs in Next (FC-031) to match.

## Decisions

- 2026-10-25: applies to the user's projects too. No tests in an app unless the user asks, and
  delivery doesn't need a test command (slice 4).
- 2026-10-25: five tests, not zero, so the guards that protect user data still have a check when
  someone asks for one.

## Shipped
