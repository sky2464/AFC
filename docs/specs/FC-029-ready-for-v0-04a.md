# FC-029 — Ready for v0.04a

Size: S · Status: next · Started: - · Done: -

Asked for on 2026-10-25. Two specs reached `dev` after v0.03a: FC-027 (add-ons really switched off at
session start, a quiet health check, a short update summary) and FC-028 (the first reply no longer
introduces Flight Control a second time). A 28-add-on session now starts with about a fifth fewer
tokens, so this is worth a release. Same shape as FC-026 slice 4.

## Goal

`main` can be released as v0.04a: `VERSION` says `v0.04a`, the release notes are in plain words, and
`sh bin/afc release check` on `main` says `ready: true`. The user merges, tags and publishes.

## You'll know it works when

- `sh bin/afc version` prints `v0.04a` on `dev`.
- `docs/changelog.md` has a `## v0.04a` section of 10 lines or fewer, in plain words, covering only
  what changed since v0.03a.
- `tests/test_release_ready.py` (renamed from `test_v003a_ready.py`) no longer pins one version: it checks that `VERSION` is v0.03a or newer
  (compared by number), that the current version has a short changelog section, and that the README
  line for older copies is still there.
- `sh bin/afc release check` on `dev` reports only "not on main".

## Out of scope

Merging `dev` into `main`, tagging, pushing the tag and publishing the release (the user's steps).

## Design notes

- Version comparison uses `afc/version.py` (by number, not text).
- The README line about copies on v0.02a or older stays as it is.

## Slices

- [x] 1. Ready for v0.04a — you'll check it by `sh bin/afc version` printing `v0.04a`, a `## v0.04a`
      changelog section of 10 lines or fewer, the reworked `tests/test_release_ready.py` (renamed) passing for any
      version at least v0.03a, and `sh bin/afc release check` on `dev` reporting only "not on main"

## Decisions

## Shipped
