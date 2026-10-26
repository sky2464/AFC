# FC-042 — Review asks for tests only when asked

Size: S · Status: in progress

Found on 2026-10-26. In php-vuln-checker, `sh bin/afc review --slice "3 …"` came back `blocked`
with five critical findings, every one "no test behind: <a line of the spec>". The slice worked in
live runs and the user's rule (FC-030) is that Flight Control writes and runs no tests unless asked,
yet the review would not let the slice be shown. Three of the five lines describe the next slice's
verdicts, so no test could have covered them yet.

Two checks in `afc/review.py` still assume tests exist:

- `acceptance_checks`: every bullet under "You'll know it works when" needs a test file that holds
  60% of its words, or the slice is `blocked`.
- `regression_checks`: a slice whose label says fix, bug or hotfix needs a changed test file that
  names a regression, or it is `blocked`.

FC-030 removed the test demands from the skill, delivery and CI, but not from the review, so the
review contradicts the skill ("show a slice once it works in a live run") and stops it.

## Goal

The review judges a slice by what it can see without tests (secrets, scans, file size, naming) and
never blocks a slice for having no tests. A user who does ask for tests still gets the old checks.

## Reaches the apps

Yes. The review is the gate every slice of every user's app passes before it is shown, so a user who
asked for no tests is no longer stopped by one (`afc/review.py`, `afc/cli_review.py`,
`.claude/skills/afc-slice/SKILL.md`).

## You'll know it works when

- `sh bin/afc review --slice "<n> <label>"` on a project with a spec, working code and no tests
  gives `verdict: ok` (when nothing else is wrong) and its report has no "untested acceptance
  line" and no "regression test" lines, including for a slice labelled "fix …".
- `sh bin/afc review --slice "<n> <label>" --tests` adds both checks back exactly as they were, so a
  user who asked for tests can have them enforced.
- `afc-slice` says: run the review with `--tests` only when the user has asked for tests in this
  project; otherwise run it as is.
- The secret scan, dependency audit, scanner checks, file-size check and naming warning are
  unchanged and still block or warn as before.

## Out of scope

The scan checks themselves, the 500-line limit and naming warnings. How a user asks for tests (they
just say so in the conversation; nothing is stored). Removing the test checks' code, which stays
behind the flag.

## Design notes

- `run_review(code, workspace, label, tests=False)`; `cmd_review` passes `args.tests`, from a new
  `--tests` option on the `review` command.
- `docstring` of `afc/review.py` says two checks are the review's own; update it to say one, and
  that the test checks run only with `--tests`.
- No test change needed for this: Flight Control keeps five tests on guards (FC-030), and none
  covers the review.

## Slices

- [x] 1. No test demand by default — you'll see it by a scratch project with a spec of five
      acceptance lines and no test files giving `verdict: ok`, no "untested acceptance line" in the
      report, and the same for a slice labelled "2 fix login"
- [x] 2. Tests when asked — you'll see it by the same scratch project with `--tests` giving
      `verdict: blocked` and five "untested acceptance line" findings, and `afc-slice` carrying the
      sentence about when to use it
- [x] 3. Live on the app that was blocked — you'll see it by `sh bin/afc review --slice "3 …"` on a
      scratch copy of php-vuln-checker at commit `a8fcebf` with a changed `app/page.tsx` giving
      `verdict: ok`

## Tasks

Slice 1:
- `afc/review.py`: `run_review(..., tests=False)`; only add `regression_checks` and
  `acceptance_checks` to the check list when `tests` is true. Update the module docstring.
- `afc/cli_review.py`: `--tests` flag, passed through.

Slice 2:
- `.claude/skills/afc-slice/SKILL.md`: one sentence in checkpoint 3 step 2, replacing a line.

Slice 3:
- Copy php-vuln-checker at `a8fcebf` into a scratch folder with a registered scratch workspace, make
  a one-line change, run the review, write the result in Decisions. Never use the real project.

## Decisions

- Slice 3, 2026-10-26: on a scratch copy of php-vuln-checker at `a8fcebf` (own registry and
  workspace, plan copied in; the real project untouched) with one comment line added to
  `app/page.tsx`, `sh bin/afc review --slice "3 server-side request that reads the announced PHP
  version"` gave `verdict: ok`, 0 critical, 0 warnings, and a report with no "untested acceptance
  line" and no "regression test" lines. The same review with `--tests` gave `verdict: blocked` with
  5 critical findings, the five that stopped the user, so the flag brings the old checks back.

## Shipped
