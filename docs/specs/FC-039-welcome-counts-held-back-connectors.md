# FC-039 — Welcome counts held-back connectors

Size: S · Status: next, ready for build

Left open by FC-038 on 2026-10-25. FC-038 ships a list of 12 claude.ai connectors in the tracked
`.claude/settings.json` (`tracked_deny` in `afc-connectors.json`), so they are held back from the
very first start. The welcome's connector line (FC-034, `_connectors_line` in
`afc/hooks/session_start.py`) only counts connectors it blocks itself, from the session's own
connector report. A connector the tracked list already blocks never shows in that report, so on a
new copy the line is empty and the user is never told that Gmail, Notion and the others are off.
They find out when "read my email" fails.

## Goal

The first welcome in a new copy says once, in one plain line, that account connectors are held back
and how to get one, so a missing connector is never a surprise.

## Reaches the apps

Yes. Everyone's first session, where they start their first app, now says which connectors are off
and that one plain request brings it back (`afc/hooks/session_start.py`, `afc/connectors.py`). The
connector a project needs (FC-034) stays reachable the same way.

## You'll know it works when

- The first welcome in a new copy, with the tracked list active, shows one line: "🔌 N account
  connectors are held back to keep the start light; say which you need and I'll add them", where N
  is the tracked names minus any the user already asked for.
- It is said once per copy, not every start: after it has been said, a start with nothing new held
  back shows no connector line. A later FC-034 or FC-037 line for newly held-back connectors still
  shows as today, and the two never appear together in one welcome (one line, the larger count).
- When N is 0, nothing is said.
- The line adds no more than 60 tokens to the first start (measured with
  `docs/measurements/token_usage.py`, same scratch clone with and without).

## Out of scope

The tracked list's names, the way a connector is turned back on (FC-038 slice 3), and update
behavior. Naming each connector in the welcome.

## Design notes

- N comes from `afc-connectors.json` `tracked_deny` minus the names in the workspace's
  `connectors.json` (`names(load(home))`), so it follows what FC-038 slices 3 and 4 do.
- "Once per copy" is a marker file in the workspace root (`connectors-told`), written after the
  line is shown. Nothing in the project's code folder.
- Where both counts exist, the line uses the larger one: they are the same set seen from two sides.

## Slices

- [ ] 1. Say it once — you'll see it by a first start in a scratch clone with an empty workspace
      showing the line with 12, a second start showing no connector line, and after
      `sh bin/afc connectors add Gmail` plus a new marker, the line saying 11
- [ ] 2. Cheap — you'll see it by `docs/measurements/token_usage.py` on the same scratch clone with
      and without the line, the difference at or under 60 tokens, both numbers in Decisions

## Tasks

Slice 1:
- `afc/connectors.py`: `tracked_held(home)` returns the tracked names not asked for.
- `afc/hooks/session_start.py` `_connectors_line`: when `tracked_held` is non-empty and
  `home/"connectors-told"` is missing, return the line and write the marker; keep the existing
  lines otherwise.

Slice 2:
- Run the measurement and write both numbers in Decisions.

## Decisions

## Shipped
