# FC-014 — Review before delivery

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-24. Reference design: the user's earlier AgToosa review workflow (four
reviewer personas, a root-cause protocol and a verdict that blocks shipping), adapted to Flight
Control's size and rules.

## Goal

Before the user is asked to approve a slice, Flight Control looks at what it just built the way
four different reviewers would — security, structure, product, tests — in the slice's own size, and
holds the slice back while anything critical is open.

Today `sh bin/afc scan` runs outside tools over the whole code folder: secrets, vulnerable
dependencies, gitleaks and semgrep when installed. Nothing checks whether the slice does what the
spec said, whether a file grew past the 500-line limit, whether every "You'll know it works when"
line has a test behind it, or whether a bug fix left a regression test. Those are the findings that
matter most, and they are the ones nobody is making.

## You'll know it works when

- When a slice is built, then the review runs as part of showing it:
  `sh bin/afc review --slice "<n> <label>"` prints one JSON object with `verdict`, `critical`,
  `warning` and `report`, and the tool checks `scan` already runs are part of it.
- When anything critical is open, then `verdict` is `blocked`, the user is not asked to approve the
  slice, and Claude says in one line what is wrong and what it is doing about it.
- When nothing critical is open, then `verdict` is `ok` and the slice is shown for approval as it is
  today; warnings are mentioned in one line only when they change what the user will see.
- When a file the slice touched is over 500 lines, then that is critical and the file is named.
- When the active spec has a "You'll know it works when" line with no test behind it, then that is
  critical and the line is quoted in full, so the user can see exactly what is untested.
- When the slice is a bug fix, then a regression test named after the bug must exist, fail on the
  unfixed code and pass after the fix; without it the verdict is `blocked`.
- When a test fails or a bug turns up, then Flight Control states a hypothesis, writes a
  reproduction test that isolates it, and only then a fix; after three wrong hypotheses it stops and
  asks the user, showing what it tried.
- When names in the code disagree with the project's own words (the spec and `decisions.md`), then
  that is a warning naming both words.
- When the review finds nothing to say, then the report is still written, so every slice leaves a
  trail.
- Reports go to the project workspace beside today's scan reports, one per slice. Nothing is written
  into the code folder.

## Out of scope

A command the user has to invoke — review happens inside building a slice. A second AI platform's
opinion. Issue-tracker status or comments. A coverage percentage gate, which the acceptance-line
check replaces. Accessibility, performance and browser-matrix checks, which deserve a spec of their
own. Reviewing anything other than the current slice's changes.

## Design notes

- **Where it lives.** `afc/scan.py` already runs outside tools, collects `Check` objects, writes a
  report and prints a summary line. The review adds checks of its own and a verdict on top:
  `sh bin/afc review` becomes what a slice runs, and `sh bin/afc scan` stays the tools-only part it
  already is. The new checks go in a new `afc/review.py`, because the 500-line rule the review
  enforces applies to the review.
- **Two severities, not three.** Critical holds the slice; warning is written down. A third level
  would only invite arguing about it.
- **What "the slice's changes" means.** Tracked and untracked changes against the last commit in the
  code folder — the same set `deliver` would commit — so the review never grades code the slice
  didn't touch.
- **Acceptance-line coverage.** The active spec's "You'll know it works when" lines are matched
  against test names and test bodies by their own words. An unmatched line is quoted, not counted:
  "3 of 5 covered" tells the user nothing they can act on.
- **The root-cause protocol.** The hypothesis → reproduction test → named regression test rule, and
  stopping after three wrong hypotheses, belong in `afc-slice` checkpoint 2 as behaviour, with the
  hypothesis log kept in the slice's report. Code can't enforce it; content tests can check the rule
  is written down, and the report shows whether it was followed.
- **The reviewers stay internal.** The user sees one line and a verdict, never four sections with
  persona names. The four passes are how Claude thinks, not what the user reads.

## Slices

- [x] 1. `review` runs the checks and gives a verdict — you'll check it by
      `sh bin/afc review --slice "1 label"` on a project with a known problem printing `verdict`,
      `critical`, `warning` and `report` (tests: ok and blocked, report written, the existing scan
      checks included)
- [x] 2. File size and untested acceptance lines are critical — you'll check it by a 501-line file
      and an uncovered "You'll know it works when" line each making the verdict `blocked`, each
      named in the report (tests for both, and for a clean project staying `ok`)
- [ ] 3. A bug fix needs a regression test — you'll check it by a bug-fix slice with no named
      regression test being blocked, and the same slice passing once the test exists (tests)
- [ ] 4. Names that disagree with the project's words are a warning — you'll check it by a spec that
      says one word and code that uses another showing both words in the report (tests)
- [ ] 5. The slice flow reviews before asking for approval — you'll check it by a live slice where
      the review runs inside checkpoint 3 and a blocked verdict stops the approval question, with
      the root-cause rule in checkpoint 2 (content tests and one live run)

## Decisions

- 2026-10-24: Review is part of building a slice, not a command the user asks for. `/afc` stays the
  only command anyone needs to remember.
- 2026-10-24: Two severities. Critical holds the slice; warnings are written down and mentioned only
  when they change what the user sees.
- 2026-10-24: An untested acceptance line is quoted in full instead of a coverage percentage.
- 2026-10-24: Left out of the port on purpose: a second AI platform's opinion, issue-tracker
  updates, and showing the four reviewers as sections.
- 2026-10-25: Slice 1 approved as built. A scan check that fails is critical, a warning is a warning, and a missing tool counts as neither; the verdict is blocked while anything is critical. A blocked verdict exits 0, as scan does. The review runs over the whole code folder for now; scoping to the slice's own changes comes with slice 2. Slices 2 to 5 are not built.

## Shipped
