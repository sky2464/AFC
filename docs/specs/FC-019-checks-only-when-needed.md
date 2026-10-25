# FC-019 — Checks only when needed

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-25, while FC-015 was being built. Each slice took longer than the one before,
and most of that time went on checks that found nothing.

What the FC-015 build showed (workflow log, slices 1 to 3):

- **Every slice pays for a checker helper.** Builds took 2m42s to 5m09s; each check took about 2
  minutes more and passed. That is about 40% of a slice's time on a check that changed nothing.
- **The full suite runs at least twice per slice.** Once in the builder before its commit, and again
  in the checker. Every fix round adds two more. Measured on `dev` on 2026-10-25: 947 tests in 60
  files take 104.6 seconds one file after another.
- **The suite keeps growing.** Every slice adds tests, so each full run is slower than the last.
  That is why every slice takes longer than the one before.
- **Most of the suite is unrelated to most slices.** Five update and session-start test files take
  50 of the 105 seconds, and a slice to `afc/ship.py` touches none of them.
- **The same tests, run eight files at a time, take 37.8 seconds** with the same results (measured
  the same day on this Mac, 10 cores).
- **No CI.** The repo has no `.github/workflows`, so nothing runs the suite after a push.

## Goal

A spec builds in about half the time, and the full suite and the checker helper run when they can
find something: risky code, a failing test, a failed CI run, or when the user asks. Safety checks on
risky code stay exactly as strict as today.

## You'll know it works when

- When the full suite runs, then it runs test files in parallel through one command, and takes at
  most 40 seconds on this Mac where it took 105 seconds before, with the same tests passing and
  failing as a serial run.
- When a builder finishes a slice, then it runs only the tests for what the slice changed, not the
  whole suite. A change to a shared test helper, `bin/afc`, `afc/hooks/` or the workflow runs everything.
- When a slice touches nothing risky and its quick gate passes, then it uses one helper, the builder,
  and no checker. The quick gate is code, not a helper: commit tagged with the slice, checkbox
  ticked, the slice's tests pass, no secret patterns in the diff, no file changed outside this repo.
- When a slice touches risky code (the guards and hooks, maintenance mode, git and delivery, update
  apply, the remote and anything that reads secrets), then the checker runs as it does today. No
  setting turns this off.
- When the user asks for a full check, then every slice gets the checker, as it does today.
- When every slice is built, then the full suite runs once. If it fails, only the slice whose commits
  touched the failing test's code gets one fixer and one checker, at most two rounds.
- When code is pushed to `dev` or a pull request is opened to `main`, then CI runs the full suite,
  and a failed run shows in `/afc` with fixing it as the recommended next step.
- Measured on the next spec of at least three slices built this way, against FC-015 slices 1 to 3:
  the time per slice that touches nothing risky is at most half, and full-suite runs per spec are
  at most 2 where they were at least 2 per slice.

## Out of scope

How a user's own project slice is tested: that runs through `afc-slice`, not helpers. Which models
build and check. Removing or loosening any safety rule. Making the slow update tests faster one by
one: parallel runs come first, and a later spec can cut individual tests if 40 seconds is not
enough.

## Design notes

- **One test command.** `sh bin/afc test` runs the suite in parallel, one process per test file,
  using the standard library only (no new packages). `--changed <ref>` runs only the tests that
  cover files changed since `<ref>`. Both print one JSON line like every other command: tests run,
  failed, seconds, and the failing test names.
- **Picking tests for a change.** A test file is picked when it was changed itself, when it imports
  a changed module, or when it names a changed file's path (tests that read the workflow or a skill
  file do this). If `tests/helpers.py`, `tests/__init__.py`, `bin/afc`, `afc/hooks/` or `.claude/` itself
  changed, or nothing is picked, it runs everything. It errs towards running more.
- **Risky paths are a list in code.** One list, kept next to the quick gate, so a test can check that
  every guard and hook file is on it. The checker runs when any changed file matches.
- **The workflow takes `check`.** `'risky'` is the default; `'all'` checks every slice as today.
  There is no `'off'`: risky slices are always checked.
- **The quick gate is code.** It runs inside the workflow script after the builder, with no helper,
  so it costs seconds and no tokens. It fails the slice the same way a checker problem does: the
  builder gets one fix round with the gate's exact message.
- **One full suite at the end.** It runs after the last slice. A failing test is matched to a slice
  by which slice's commits changed the files it covers; if none matches, the last slice gets it.
- **CI.** A GitHub Actions workflow runs `sh bin/afc test` on Python 3.12 for pushes to `dev` and
  pull requests to `main`. `/afc` reads the last run with `gh`, if it is installed and signed in; if
  not, it says nothing rather than guessing. Running CI is the user's push; Flight Control never
  pushes to start it.
- **The builder and checker helpers** say to use `sh bin/afc test --changed` and
  `sh bin/afc test`, not `python3 -m unittest discover`. CONTRIBUTING's Tests section says the same.

## Slices

- [ ] 1. Parallel suite — `sh bin/afc test` runs every test file in parallel and prints one JSON line;
      you'll check it by `tests/test_afc_test.py` (a passing and a failing fixture file are both
      reported), and by the full suite taking at most 40 seconds on this Mac with the same pass and
      fail count as `python3 -m unittest discover -s tests`.
- [x] 2. Tests for what changed — `sh bin/afc test --changed <ref>` picks tests by changed files,
      imports and named paths, and runs everything for shared files; you'll check it by
      `tests/test_afc_test.py`: a change to `afc/ship.py` picks `test_ship_gate` and not
      `test_update_check`, a change to `tests/helpers.py` runs all 60 files, and a change to the
      workflow picks `test_spec_checks`.
- [x] 3. Quick gate and risky list — the workflow runs the code gate after each builder and the
      checker only for risky slices or `check: 'all'`; you'll check it by
      `tests/test_build_workflow.py`: a slice changing only `afc/plan.py` runs 1 helper,
      a slice changing `afc/hooks/rules_git.py` runs 2, `check: 'all'` runs 2 for both, a gate
      failure starts 1 fix round, and every file in `afc/hooks/` matches the risky list.
- [ ] 4. One full suite at the end — after the last slice the workflow runs `sh bin/afc test` once
      and sends a failure to the slice that changed the failing test's code; the builder and checker
      helpers and CONTRIBUTING use the new command; you'll check it by `tests/test_build_workflow.py`
      (a failing final suite starts exactly 1 fixer and 1 checker, for the right slice) and by no
      helper or CONTRIBUTING line still saying `unittest discover`.
- [ ] 5. CI — `.github/workflows/tests.yml` runs `sh bin/afc test` on pushes to `dev` and pull
      requests to `main`, and `/afc` shows a failed last run with fixing it first; you'll check it
      by `tests/test_ci_status.py` (a failed run, a passed run, and no `gh` each give the right
      line) and by the workflow file naming both triggers.
- [ ] 6. Measure the next build — build the next spec of at least three slices this way and compare
      with FC-015 slices 1 to 3 from its workflow log; time per non-risky slice at most half, and
      at most 2 full-suite runs for the whole spec; the result goes into `docs/measurements/`.

## Decisions

- 2026-10-25: Risky slices are always checked, and the workflow has no setting that skips them. The
  time saved comes from safe slices and from running fewer tests, not from checking risky code
  less.
- 2026-10-25: Parallel runs come before trimming slow tests. They cut 105 seconds to 38 seconds
  without changing a test, and the risk of losing a check is lower.
