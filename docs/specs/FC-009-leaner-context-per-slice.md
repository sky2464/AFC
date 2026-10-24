# FC-009 — Leaner context per slice

Size: M · Status: in progress · Started: 2026-10-24 · Done: -

Finding: 14.

## Goal

A slice costs much less context. The live run used about 101k tokens to set up the project and build
one small slice: full skill texts loaded several times, five full rule modules, two web searches and
long shell outputs.

## You'll know it works when

- A measured repeat of the php-vuln-checker start plus first slice uses at least a third fewer tokens
  than the first run (measured from the session transcript's token counts).
- Rule modules have a short form (Do and Never, at most about 25 lines each) that Claude reads by
  default; the long form stays for review.
- No skill is loaded twice in a row for the same step.
- Command outputs Claude doesn't need stay small (for example `plan` and `status` without echoing
  paths it already has).

## Out of scope

Changing models or effort settings; removing safety rules.

## Design notes

- Measure first: a small script in `docs/` notes (not shipped) that sums token usage from a
  transcript JSONL, run on the first live session as the baseline.
- `rules/*.md`: add a `## Short` section at the top; `sh bin/afc modules` returns the short form path
  by default and the full one with `--full`.
- Skills: move rarely used parts (enterprise, remotes, Azure) out of the always-loaded skills into
  ones loaded only when needed.
- FC-005's "no `cat` of rules" already removes the biggest single block.

## Slices

- [x] 1. Baseline measurement — you'll check it by a written number for the first live run
- [ ] 2. Short rule modules — you'll check it by `modules` returning short paths (tests in
      `tests/test_content.py` for the size limit, `tests/test_cli.py` for `--full`)
- [ ] 3. Trim always-loaded skills — you'll check it by skill line counts going down with the content
      tests still passing
- [ ] 4. Measured live re-run — you'll check it by the new number against the baseline

## Decisions

## Shipped
