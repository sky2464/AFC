# FC-026 — Release check and v0.03a

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-25. Fifteen specs (FC-011 to FC-025) reached `main` after the
v0.02a release, and the one-click update (FC-011) has never updated a real older copy.

Found while speccing: `VERSION` on `main` and `dev` says `v0.01a`, so `sh bin/afc version` prints
`v0.01a` although v0.02a is published. FC-011's decision says slice 1 reports `v0.02a`; that change
was lost. Every copy built from `main` would be offered v0.02a, an older release than the code it
runs. The v0.01a and v0.02a tags have no `VERSION` file and no update code at all.

## Goal

Releasing is a checked, repeatable step: Flight Control says whether `main` is ready to tag, the
version it reports is never older than the newest release, and the one-click update is proven on a
real copy before v0.03a goes out. Publishing stays the user's own step.

## You'll know it works when

- `sh bin/afc version` on `dev` and `main` prints a version no older than the newest `v*` tag on
  `main` (today `v0.02a`), and a test fails if `VERSION` is ever behind that tag.
- `sh bin/afc release check` prints one JSON object with `ready` true or false and one plain line
  per problem: not on `main`, uncommitted changes, `VERSION` not newer than the newest tag, no
  changelog entry since the newest tag, a tag for `VERSION` already existing. It changes nothing.
- An update from a copy at an older tag to a newer tag, both carrying FC-011's update code, lands on
  the newer tag with `sh bin/afc check` passing, in a scratch copy with its own `AFC_HOME`.
- `main` is ready for v0.03a: `VERSION` says `v0.03a`, release notes are drafted in plain words, and
  `sh bin/afc release check` on `main` says `ready: true`. The user tags and publishes.

## Out of scope

Tagging, pushing tags or publishing the GitHub release (the user's own steps). Making the repo or
release public in any new way. Updating copies older than v0.03a automatically: v0.01a and v0.02a
have no update code, so they move once by hand.

## Design notes

- **Newest tag.** Read from local tags reachable from `main` (`git tag --merged main 'v*'`), sorted
  with the existing version order in `afc/version.py`. No network in `release check`.
- **Changelog entry.** `docs/changelog.md` has a `## <date> — ...` heading dated after the newest
  tag's commit date, or a `## v0.03a` heading. Either counts.
- **Real update test.** Build two scratch copies from the current code: tag the older one `v0.03a`
  and the newer `v0.03b` in a local bare repo used as `origin`, then run `sh bin/afc update` in the
  older copy. Nothing touches the real `~/.A-FC` or GitHub. A slow test, marked so the quick run
  skips it; CI runs it.
- **Older copies.** README gets one line: copies on v0.02a or older update once with
  `git pull` in the `A-FC` folder; from v0.03a on, Flight Control offers updates itself.

## Slices

- [ ] 1. Version is never behind the newest release — you'll check it by `sh bin/afc version`
      printing `v0.02a` on `dev`, and `tests/test_version.py` failing when `VERSION` is older than
      the newest `v*` tag merged into `main` (tests: equal passes, newer passes, older fails, no tags
      passes)
- [ ] 2. Release check — you'll check it by `sh bin/afc release check` printing `ready: false` with
      exactly one line per problem on `dev`, and `ready: true` on a scratch repo on `main` with a
      bumped `VERSION`, a new changelog heading and a clean tree (tests: each of the 5 problems alone,
      all clear, and `git status --short` unchanged after the run)
- [ ] 3. Real update between two copies — you'll check it by `tests/test_update_live.py` updating a
      scratch copy from local tag `v0.03a` to `v0.03b` and finding `sh bin/afc version` printing
      `v0.03b` and `sh bin/afc check` with no problems, with the real `~/.A-FC` unchanged (file
      count and newest modified time compared before and after)
- [ ] 4. Ready for v0.03a — you'll check it by `sh bin/afc release check` on `dev` reporting only
      "not on main", `VERSION` saying `v0.03a`, a `## v0.03a` changelog section listing what
      changed since v0.02a in 10 lines or fewer, and the README line for older copies

## Decisions

## Shipped
