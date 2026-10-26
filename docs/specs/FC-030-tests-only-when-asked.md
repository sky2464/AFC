# FC-030 — Tests only when asked

Size: M · Status: next

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

- [ ] 1. Five core tests — you'll see it by `sh bin/afc test` running five tests and passing in a
      few seconds, with the rest of `tests/` gone
- [ ] 2. Building runs no tests — you'll see it by a build of a one-line FC slice finishing with no
      test run in its log, and no test count in its summary
- [ ] 3. Quiet replies and CI — you'll see it by `/afc` in maintenance mode showing no GitHub test
      line, and GitHub running only the five on a pull request to `main`
- [ ] 4. Projects test only when asked — you'll see it by a live slice in a test project that
      shows a working change with no test written, and delivers it without a test command
- [ ] 5. Specs say "you'll see it by" — you'll see it by the spec template, `CONTRIBUTING.md` and
      the open specs in Next all using it

## Decisions

## Shipped
