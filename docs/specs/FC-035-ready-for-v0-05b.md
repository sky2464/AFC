# FC-035 — Ready for v0.05b

Size: S · Status: in progress

Asked for on 2026-10-25. Five specs reached `dev` after v0.04a (FC-030 to FC-034), and every one
changes what users and their apps get. Same shape as FC-029.

## Goal

`main` can be released as v0.05b: `VERSION` says `v0.05b`, the release notes are in plain words, and
`sh bin/afc release check` on `main` says `ready: true`. The user merges, tags and publishes.

## Reaches the apps

This is the release: users on v0.04a or older get all of it through the update, which brings every
change in the notes below to their projects and workspaces. Nothing in a user's project changes
until they update.

## You'll know it works when

- `sh bin/afc version` prints `v0.05b` on `dev`.
- `docs/changelog.md` has a `## v0.05b` section of 10 lines or fewer, in plain words, covering only
  what changed since v0.04a:
  - tests run only when you ask (Flight Control keeps five, and your apps get none unless you ask);
  - every spec says how it reaches your apps;
  - one master plan that updates itself wherever the work runs;
  - the test copy stays current and in its own workspace, and an empty start is quiet;
  - a session starts with only the connectors a project uses (a "hi" about 43k tokens, down from
    60k).
- `sh bin/afc release check` on `dev` reports only "not on main".
- No workspace layout changed since v0.04a, so no upgrade step is needed. If a slice finds one did,
  it stops and says so rather than shipping without the step.

## Out of scope

Merging `dev` into `main`, tagging, pushing the tag and publishing the release (the user's steps).
Any new feature.

## Design notes

- Edit `VERSION` and `docs/changelog.md` only. The `## v0.04a` section stays as it is.
- Check for a layout change with `git diff v0.04a..dev -- afc/upgrade_*.py templates/workspace`.
  Today it shows only `templates/workspace/spec.md` (the new "Reaches the apps" heading). That is a
  template for new specs, not a change to the folder layout, so no upgrade step is needed.

## Slices

- [ ] 1. Ready for v0.05b — you'll see it by `sh bin/afc version` printing `v0.05b`, a `## v0.05b`
      changelog section of 10 lines or fewer, and `sh bin/afc release check` on `dev` reporting only
      "not on main"

## Tasks

Slice 1:
- `VERSION`: `v0.05b`.
- `docs/changelog.md`: add `## v0.05b` above `## v0.04a`, five bullets from the list above.
- Run the layout-change check from the design notes and say what it found.

## Decisions

## Shipped
