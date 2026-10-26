# FC-032 — Every spec reaches the apps

Size: S · Status: done

Asked for on 2026-10-25: the goal of everything built in Flight Control, and of every improvement,
is that it applies in the end to the apps Flight Control builds for users. Today that lives only in
one person's notes. Nothing in the master plan, the spec template or the planning helper asks it,
so a spec can be about Flight Control alone and nobody notices (FC-031's first slice is one).

## Goal

Every FC spec says how its change reaches the apps Flight Control builds, or says plainly that it
can't. The rule is written into Flight Control itself, not left in notes.

## Reaches the apps

Does not reach the apps, because it only changes how Flight Control's own specs are written and
checked; project specs and their skills stay as they are.

## You'll know it works when

- The master plan's Goal ends with one line: every change must reach the apps Flight Control builds
  for users.
- The spec template has a short `## Reaches the apps` section, placed after Goal. The section is
  one or two lines naming the skill, rule, template or command in a user's project that changes,
  or "does not reach the apps, because …".
- The planning helper (`.claude/agents/afc-plan.md`) refuses to call a spec ready for build while
  that section is empty.
- `sh bin/afc plan` shows a spec as not ready when its section is missing or empty, so "ready for
  build" can't be said by mistake.
- FC-030 and FC-031 have the section filled in.

## Out of scope

Rewriting finished specs. Judging whether the stated path is good. Any change to how apps are built.

## Design notes

- Touch `templates/workspace/spec.md` only if FC specs use it; FC specs are in `docs/specs/`, so
  also add the section to the FC spec shape that `afc-plan` follows.
- "Ready" is read from a `Status:` line ending in "ready for build"; the check is a few lines in
  `afc/plan.py` / `afc/cli_plan.py`.
- Keep the master plan and agent text to a line or two each.

## Slices

- [x] 1. The rule and the section — you'll see it by the master plan Goal line, the new template
      section, and the `afc-plan` rule all being there
- [x] 2. Plan flags missing sections — you'll see it by `sh bin/afc plan` marking FC-031 as not
      ready until its section is filled, then ready

## Tasks

Slice 1: add the Goal line to `docs/master-plan.md`; add `## Reaches the apps` to
`templates/workspace/spec.md` and to the FC spec shape; add the rule to `.claude/agents/afc-plan.md`;
fill the section in FC-030 and FC-031.

Slice 2: in `afc/plan.py` read a spec's `Reaches the apps` section and set `ready: false` when it's
missing or empty; `afc/cli_plan.py` prints `ready` per Next row.

## Decisions

## Shipped

Shipped 2026-10-25. Slices: 2.
