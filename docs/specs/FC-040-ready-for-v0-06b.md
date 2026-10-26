# FC-040 — Ready for v0.06b

Size: S · Status: next, ready for build

Asked for on 2026-10-26. Four specs reached `dev` after v0.05b (FC-036 to FC-039), all from the
fresh-clone review: a stuck maintenance switch and heavy starts for new users. Same shape as FC-035,
and still a beta like v0.05b.

## Goal

`main` can be released as v0.06b: `VERSION` says `v0.06b`, the release notes are in plain words, and
`sh bin/afc release check` on `main` says `ready: true`. The user merges, tags and publishes.

## Reaches the apps

This is the release. Users on v0.05b or older get it through the update, and it gives them back
their projects (no stuck maintenance mode) and a lighter start before and after their first app.

## You'll know it works when

- `sh bin/afc version` prints `v0.06b` on `dev`.
- `docs/changelog.md` has a `## v0.06b` section of 10 lines or fewer, in plain words, covering only
  what changed since v0.05b:
  - maintenance mode can't get stuck on any more: it is per session only, never on a copy on
    `main`, and the update clears an old leftover switch;
  - starts without a project are light too (about 42k tokens from the second start, down from 73k);
  - a new copy's very first "hi" is lighter (about 56k, down from 73k), with no extra step;
  - the first welcome says once that connectors are held back, and how to ask for one.
- This release carries workspace layout 1 (`afc/upgrade_001.py`, from FC-036). The notes say in
  plain words that the update backs up the workspace first. `workspace_upgrade.upgrade` takes a
  scratch layout-0 workspace with a `maintain` file to layout 1, with the file gone and a backup
  made.
- `sh bin/afc release check` on `dev` reports only "not on main".

## Out of scope

Merging `dev` into `main`, tagging, pushing the tag and publishing the release (the user's steps).
Any new feature.

## Design notes

- Edit `VERSION` and `docs/changelog.md` only. The `## v0.05b` section stays as it is.
- Numbers come from the Decisions of FC-037 (42,241 on the second start) and FC-038 (56,247 on the
  first, down from 73,310).

## Slices

- [ ] 1. Ready for v0.06b — you'll see it by `sh bin/afc version` printing `v0.06b`, a `## v0.06b`
      changelog section of 10 lines or fewer, the layout-1 upgrade run on a scratch workspace
      leaving no `maintain` file, and `sh bin/afc release check` on `dev` reporting only "not on
      main"

## Tasks

Slice 1:
- `VERSION`: `v0.06b`.
- `docs/changelog.md`: add `## v0.06b` above `## v0.05b`, with the four bullets above and one line
  on the workspace backup.
- Run the layout-1 upgrade on a scratch workspace and the release check, and write what they printed
  in Decisions.

## Decisions

## Shipped
