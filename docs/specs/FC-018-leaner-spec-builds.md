# FC-018 — Leaner spec builds

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-25, after the FC-011 build with Sonnet builders and Sonnet/Haiku checkers
used 21 helpers and 2.6M tokens for five slices and showed one 3h36m step.

## Goal

Building a Flight Control spec of several slices takes about half the helpers, tokens and test runs
it takes today, without checking any less. It also no longer stalls when the Mac goes to sleep.

What the FC-011 build showed:

- **A stall from sleep, not from work.** "suite 2" and "review 2" each took 3h36m. The power log
  shows the Mac went to sleep on battery at 04:59 and did not fully wake for hours.
- **Most tokens go on starting helpers.** Every helper starts by loading about 90k tokens of
  context (rules, memory notes, every tool and add-on listed) before it does anything. "review 4"
  used 99.5k tokens in 37 seconds. That is about 1.9M of the 2.6M.
- **Two checkers doing one job.** Each slice got a "suite" helper (run the tests and check the slice
  is met) and a "review" helper (read the commits and check the slice is met). The full suite takes
  about 100 seconds. It ran once in the builder, again in "suite", and often again in "review",
  and every fix round repeated all three.
- **Loose slice checks cause fix rounds.** Slices 2 and 3 failed review and needed fix rounds; "fix
  2.1" alone took 21 minutes. The reviewer read "must never delay the welcome" as "a 3-second
  timeout is a delay", and the builder had read it the other way. Neither was wrong: the spec gave
  no number.
- **The build is written by hand each time.** The workflow lives only in the session that wrote it
  (`build-fc-011-sonnet-2`), so none of these lessons carries over to the next spec.

## You'll know it works when

- When a spec of several slices is built, then it runs from one build workflow kept in this repo.
  The session passes the spec and the slices to build, and does not write a new script.
- When a slice passes on the first try, then it uses exactly two helpers, one builder and one
  checker, and the full suite runs twice: once in the builder before its commit, once in the
  checker.
- When a check fails, then a fix round is one fixer plus one checker. There are at most two rounds,
  then the build stops and says why.
- When a helper starts, then it loads only what building or checking needs: the tools for files,
  search and the shell, and not the add-on servers or other tools. A helper that does nothing starts
  at no more than half the tokens of today's, measured before and after in the same way.
- When the checker fails a slice, then every problem quotes the spec line or safety rule it breaks.
  A problem that quotes neither is reported as a note and does not start a fix round.
- When a spec is written, then each slice's "you'll check it by" names a test or command and a
  number wherever the outcome is a time, size or count, such as "the welcome prints within 0.5
  seconds with the remote unreachable" instead of "never delays the welcome". CONTRIBUTING says so.
- When a build starts, then the Mac is kept awake until it ends. On battery, Claude says in one
  line that plugging in keeps it awake. When the build ends or stops, the keep-awake ends too.
- Measured on the next spec built this way, against FC-011 slices 3 to 5: helpers per slice, tokens
  per slice, and full-suite runs per slice are each at most half.

## Out of scope

How a user's own project slice is built: that runs in the main session through `afc-slice`, without
helpers. Test sizing and running one test file while building, which FC-013 covers. Project review
and its verdict, which FC-014 covers. Which models build and check: the workflow takes them as
settings.

## Design notes

- **Where the workflow lives.** `.claude/workflows/afc-build-spec.js` in this repo, so it ships with
  Flight Control and can be run by name. It takes `spec`, `slices` (number and text), `start` and
  `alreadyBuilt`, which are the inputs `build-fc-011-sonnet-2` already has, and the models. The
  session reads the spec and passes the slices in; the script stays the same for every spec.
- **One checker.** It runs the full suite once, reads every commit for the slice
  (`git log --grep "FC-0NN slice N"`), and judges the result against the slice's line, the spec's
  "You'll know it works when" lines, and the safety list the review prompt has today: writes only
  inside the repo and the Flight Control home, no secrets, no push, branch change, force or history
  rewrite, maintenance guard not bypassed. It returns `pass`, `problems` (each with what it quotes)
  and `notes`.
- **Builder and fixer report the suite.** They return the suite's last lines with their result. The
  checker still runs the suite itself, because a builder's own word that tests pass is not the
  check.
- **Lean helpers.** Two helper definitions in `.claude/agents/`, `afc-builder` and `afc-checker`,
  with a `tools` list (read, edit, write, search, shell; the checker without edit and write) and a
  short body. The helpers don't load MCP servers or the full skill listing. Slice 2 measures a
  do-nothing helper first, so the target is set from a number and not a guess (FC-009 missed its
  target because its baseline was estimated).
- **Keeping awake.** `sh bin/afc awake on|off|status` wraps macOS `caffeinate -i` with a stored
  process id and a four-hour limit, so a forgotten build does not keep the Mac up forever. `status`
  reports whether it is on and whether the Mac is on battery (`pmset -g batt`). On other systems it
  prints `{"awake": false, "reason": "not macOS"}` and the build carries on. The build turns it on
  before the first helper and off when it returns, whichever way it ends.
- **Sharper checks are a writing rule.** The rule goes in CONTRIBUTING beside the release steps and
  in the spec template used for new FC specs. Existing specs are not rewritten. A spec whose next
  slice has no number where one is needed gets one before it is built.

## Slices

- [x] 1. One build workflow with one checker — you'll check it by the workflow file existing in
      `.claude/workflows/` and taking spec, slices and models as inputs, and by a structural test that
      it starts one checker per round and at most two fix rounds (tests; no live build yet)
- [x] 2. Lean helpers — you'll check it by a do-nothing helper's starting tokens measured before and
      after, the after at most half the before, both numbers written in Decisions (one structural
      test that both helper files name their tools; the measure is live)
- [ ] 3. Checks that quote the spec — you'll check it by the checker's result keeping `problems` and
      `notes` apart, with a problem that quotes no spec line or rule landing in `notes`, and by
      CONTRIBUTING's rule asking for a number where an outcome is a time, size or count (one
      structural test each)
- [ ] 4. Stay awake while building — you'll check it by `sh bin/afc awake on`, `status` and `off`
      with a fake `caffeinate` and `pmset` on the path: on starts it once, a second on does not
      start another, off stops it, the four-hour limit is passed, and other systems get
      `not macOS` (tests)
- [ ] 5. Measure it on a real spec — you'll check it by building the next queued spec with the new
      workflow and comparing helpers, tokens and full-suite runs per slice with FC-011 slices 3 to
      5; each at most half, written in Decisions (no test code; numbers from the workflow panel)

## Decisions

- 2026-10-25: The multi-slice build is Flight Control's own, kept in the repo, not rewritten in each
  session.
- 2026-10-25: One checker per slice. It runs the suite itself; the builder's report is not the
  check.
- 2026-10-25: A failed check must quote the spec line or safety rule it breaks; anything else is a
  note.
- 2026-10-25: Slice 2 measured a do-nothing helper (prompt "Reply ok", `claude -p --output-format json`,
  start tokens = input + cache read + cache write): default 75,031 tokens (527 tools), `afc-checker`
  17,657 (24%). An in-session general-purpose helper started at 79,640. Target was at most half: met.
  New helper files load only when a session starts, so the next build session picks them up.

## Shipped
