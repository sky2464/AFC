# FC-039 — Welcome counts held-back connectors

Size: S · Status: in progress

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
  is the tracked names minus any the user already asked for. One connector reads "1 account
  connector is held back ... say which you need and I'll add it".
- It is said once per copy, not once per workspace: a second clone of Flight Control that shares the
  same `~/.A-FC` still says it on its own first start. A second start in the same copy shows no
  connector line.
- It is said again when the tracked list grows: after an update adds a name, the next start says it
  with the new N. A shrinking list (the user asked for one) says nothing.
- One connector line per welcome. When FC-034 or FC-037 also held something back that start, the
  line shows the larger of the two counts, with that line's own ending ("not used by <name>" or
  "until a project needs them").
- When N is 0, nothing is said. If the memory of what was said can't be read or written, the line
  is said again at the next start rather than never.
- The line adds no more than 60 tokens to the first start (measured with
  `docs/measurements/token_usage.py`, same scratch clone with and without).

## Out of scope

The tracked list's names, the way a connector is turned back on (FC-038 slice 3), and update
behavior. Naming each connector in the welcome.

## Design notes

- N comes from `afc-connectors.json` `tracked_deny` minus the names in the workspace's
  `connectors.json` (`names(load(home))`), so it follows what FC-038 slices 3 and 4 do.
- What was said is remembered per Flight Control folder, not per workspace: `~/.A-FC/connectors-told`
  holds one entry per folder, the folder's path and the tracked names it last told about. A fresh
  clone has a new path, so it says the line; the same clone says it again only when a name appears
  that wasn't in its entry. Nothing is written in the Flight Control folder, so `git status` stays
  clean, and nothing in a project's code folder.
- The line is built by one function so the three ways a connector gets held back (tracked list,
  FC-034 project, FC-037 no project) can't each print their own.

## Slices

- [x] 1. Say it once per copy — you'll see it by three scratch clones sharing one empty `AFC_HOME`:
      each one's first start showing the line with 12, and its second start showing no connector
      line
- [x] 2. Say it again when it grows, and count down when asked — you'll see it by
      `sh bin/afc connectors add Gmail` followed by a start showing no line, then a commit adding a
      name to the tracked list followed by a start showing the line with the new N
- [x] 3. Cheap — you'll see it by `docs/measurements/token_usage.py` on the same scratch clone with
      and without the line, the difference at or under 60 tokens, both numbers in Decisions

## Tasks

Slice 1:
- `afc/connectors.py`: `tracked_held(home)` returns the tracked names not asked for;
  `told(home, folder)` and `mark_told(home, folder, names)` read and write the per-folder entry in
  `home/"connectors-told"` (a failure to read means "not told", a failure to write is ignored).
- `afc/hooks/session_start.py` `_connectors_line`: one function builds the single line from the
  tracked count and the FC-034 / FC-037 count; write the entry after showing it.

Slice 2:
- `told` compares the entry's names with `tracked_held`: say it only when a name is new.

Slice 3:
- Run the measurement and write both numbers in Decisions.

## Decisions

- Slice 3, measured with `docs/measurements/token_usage.py` (floor_context of a one-turn `claude -p` start on two scratch clones, each with its own empty `AFC_HOME`; the "without" clone was marked as told first, so only the line differs): with the line 43048 tokens, without 43045, a difference of 3 (limit 60). The line goes to the welcome message the user reads, not into the model's context. A first try that compared a first start with a second start read 56977 against 43047, but that gap came from other first-start content, not this line, so it was redone as above.

## Shipped
