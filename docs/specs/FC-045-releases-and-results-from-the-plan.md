# FC-045 — Releases and results from the plan

Size: M · Status: in progress · Started: 2026-10-26 · Done: -

Found on 2026-10-26, comparing this plan with AgToosa's, whose Done rows carry the version and links
to the review and the evidence.

- Three of 43 specs (FC-029, FC-035, FC-040) are hand-written "Ready for vX" prep, and there were five
  releases in four days. FC-040 is already stale: it names FC-036 to FC-039 but not FC-042 (it changed
  what users see) or FC-041.
- Each finished spec already gets a plain changelog entry (`ship.changelog_entry`), but the `## vX`
  section that `release check` wants is written by hand.
- Done rows say nothing about the result. FC-009 was closed "target not met" and that is in one log
  line; a dropped spec is filed in Done as "(dropped)".
- The goal ("as few questions and as little noise as possible") is measured nowhere. The numbers exist
  but are scattered: three files in `docs/measurements`, FC-038's 73,310 down to 56,247 tokens inside
  its Decisions, FC-040's 42k and 56k.

## Goal

A release is made from the plan, not from a spec. `sh bin/afc release prepare <version>` lists what is
done since the last release, drafts the `## <version>` section (10 lines or fewer, plain words) from
each spec's goal, and sets VERSION. Each Done row says which release it went out in and what it
reached (met, partly, not met), and a small Scoreboard shows the few numbers the goal depends on.

## Reaches the apps

Yes. Users get Flight Control through its releases, so each release now says in plain words what
changed for them, and a missed target can no longer be shipped as "done". A project's Done rows get the
same Outcome column, so a user sees which finished specs met their criteria
(`afc/release.py`, `afc/cli_plan.py`, `afc/plan.py`, `templates/workspace/plan/master-plan.md`).

## You'll know it works when

- A1. `sh bin/afc release prepare v0.07a --show` on a scratch clone with three finished specs since the
  last tag prints them and changes nothing; without `--show` it writes a `## v0.07a` section of 10
  lines or fewer from the goals and sets VERSION, and `release check` on main then reports only "not on
  main" or nothing.
- A2. On the real `dev`, `--show` lists FC-036 to FC-039 and FC-042 (and FC-041 once done): the
  specs FC-040 misses.
- A3. The plan has a `## Releases` table, computed from tags and the Done rows' Release column, and
  `release prepare` stamps the version into the Done rows it covers.
- A4. `plan done <id> --outcome met|partly|not-met "<number or reason>"` puts the result in the Done
  row; `plan drop` writes "dropped"; FC-009 shows "not met" with its numbers.
- A5. The plan has a `## Scoreboard` with at least three measures, each with now, before and where it
  comes from: first-start tokens (73,310 to 56,247), tokens per slice (7.5M to 0.25M, FC-018), and
  full-suite runs per slice (8.7 to 5.0, FC-018). `plan score "<name>" <value>` updates one and logs it.

## Out of scope

Merging, tagging, pushing and publishing (the user's steps). Choosing the next version number: the user
gives it. Deciding FC-040's fate (see Design notes). Measuring anything new beyond the three seeds.

## Design notes

- "Done since the last release" comes from git, not dates: the specs whose archive file was added
  since the newest tag (`git log <tag>..HEAD --diff-filter=A --name-only -- docs/specs/archive`). Dates
  are one-day only, so two releases on one day would blur.
- Done gains two columns at the end, `Release` and `Outcome`, so the position-based reads (`row[2]` is
  the date, `row[3]` the spec) keep working. `_DONE_HEADER`, `cmd_drop` and `cmd_done` append them; the
  yearly archive files keep their four columns for old rows and the new six for new ones.
- The draft section uses `ship.changelog_entry`'s goal paragraph, cut to one line per spec.
- Scoreboard is a table of text; `plan score` replaces the "now" cell and moves the old one to
  "before" only when the user says so (`--keep-before`), never silently.
- FC-040 ("Ready for v0.06a") is the hand-written version of slice 1. Once slice 1 is done it should be
  replaced by `release prepare v0.06a`; the user decides whether FC-040 waits for this spec or ships
  first, so nothing here changes it.
- No test change: Flight Control keeps five tests on guards (FC-030).

## Slices

- [x] 1. Draft the release — you'll see it by `release prepare v0.07a --show` and then without `--show`
      on a scratch clone, and `--show` on the real `dev` listing the specs FC-040 misses (proves A1, A2)
- [x] 2. Releases table and Release column — you'll see it by a scratch plan showing the table and the
      stamped Done rows after `prepare` (proves A3)
- [x] 3. Outcome on Done rows — you'll see it by `plan done --outcome` and `plan drop` on scratch specs
      and FC-009's row backfilled (proves A4)
- [ ] 4. Scoreboard — you'll see it by the three seeded rows in the plan and `plan score` changing one
      with a log row (proves A5)

## Tasks

Slice 1:
- `afc/release.py`: `since_tag(root)` from git; `prepare(root, version, show)` writes the section,
  sets VERSION.
- `afc/cli_version.py` or `afc/cli.py`: the `release prepare` subcommand next to `release check`.

Slice 2:
- `afc/plan.py`: Releases rendering from tags; Done columns.
- `templates/workspace/plan/master-plan.md`: the new columns.

Slice 3:
- `afc/cli_plan.py`: `--outcome` on `done`; "dropped" on `drop`; backfill FC-009 in
  `docs/specs/archive/done-2026.md`.

Slice 4:
- `docs/master-plan.md`: Scoreboard section; `afc/cli_plan.py`: `score`.

## Decisions

## Shipped
