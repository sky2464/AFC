# FC-040 — Ready for v0.06a

Size: S · Status: done

Asked for on 2026-10-26. Four specs reached `dev` after v0.05b (FC-036 to FC-039), all from the
fresh-clone review: a stuck maintenance switch and heavy starts for new users. Same shape as FC-035.

## Goal

`main` can be released as v0.06a: `VERSION` says `v0.06a`, the release notes are in plain words, and
`sh bin/afc release check` on `main` says `ready: true`. The user merges, tags and publishes.

## Reaches the apps

This is the release. Users on v0.05b or older get it through the update, and it gives them back
their projects (no stuck maintenance mode) and a lighter start before and after their first app.

## You'll know it works when

- `sh bin/afc version` prints `v0.06a` on `dev`.
- `docs/changelog.md` has a `## v0.06a` section of 10 lines or fewer, in plain words, covering only
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

- FC-041 and FC-042 are queued ahead of this release. When they are done first, their changes
  (maintenance mode kept across a restart, review no longer demands tests) get a bullet each in
  the v0.06a notes; the 10-line limit then drops the smallest bullet.
- Edit `VERSION` and `docs/changelog.md` only. The `## v0.05b` section stays as it is.
- Numbers come from the Decisions of FC-037 (42,241 on the second start) and FC-038 (56,247 on the
  first, down from 73,310).

## Slices

- [x] 1. Ready for v0.06a — you'll see it by `sh bin/afc version` printing `v0.06a`, a `## v0.06a`
      changelog section of 10 lines or fewer, the layout-1 upgrade run on a scratch workspace
      leaving no `maintain` file, and `sh bin/afc release check` on `dev` reporting only "not on
      main"

## Tasks

Slice 1:
- `VERSION`: `v0.06a`.
- `docs/changelog.md`: add `## v0.06a` above `## v0.05b`, with the four bullets above and one line
  on the workspace backup.
- Run the layout-1 upgrade on a scratch workspace and the release check, and write what they printed
  in Decisions.

## Decisions

- 2026-10-26: named v0.06a, not v0.05b1. Copies on v0.05b only see tags shaped like `v0.05b`
  (numbers and one letter) and skip any other tag, so a `b1` would never be offered to them.

- 2026-10-26 slice 1: VERSION is v0.06a; `sh bin/afc version` printed {"version": "v0.06a"}. The `## v0.06a` section has 6 bullets (6 lines, plus heading), covering the four bullets plus FC-041 and FC-042 and the workspace backup (merged into the first bullet). Numbers checked: FC-037 second start 42,241; FC-038 first start 56,247 from 73,310. `workspace_upgrade.upgrade` on a scratch layout-0 workspace with a `maintain` file returned upgraded: true, layout 1, steps [1], with a backup folder made and `maintain` gone. `sh bin/afc release check` on dev, before the commit, said ready: false, problems: "You are not on main (you are on dev)." and "There are uncommitted changes." (the second was this slice's own edits).

## Shipped

Shipped 2026-10-26. Slices: 1.
