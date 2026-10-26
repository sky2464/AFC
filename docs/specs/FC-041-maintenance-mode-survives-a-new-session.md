# FC-041 — Maintenance mode survives a new session

Size: M · Status: in progress

Found on 2026-10-26. The user was in maintenance mode, working on FC-040 (session `f79266d7…`).
Claude Code then started a new session in the same folder (`10701c43…`, the instruction files were
re-read). Nobody turned maintenance mode off, but the switch is saved against the old session's ID,
so the new session read it as off. Its welcome offered "1 = continue php-vuln-checker" and the
user's "1", meant for the earlier question ("Build FC-040"), was taken as that. A slice was built in
the user's app, and had to be undone. FC-010 (the first maintenance mix-up) was meant to make this
impossible; FC-036 made the switch per session and removed the only thing that crossed a restart.

Two causes, both Flight Control's:

- **The switch dies with the session ID.** `afc/config.py` keeps `maintain.d/<session id>`. A
  resume, clear or compact that changes the ID leaves the switch behind. The hook already receives
  the new session's `session_id` (and, we expect, a `source` of `startup`, `resume`, `clear` or
  `compact`; slice 1 confirms it), but nothing connects the two.
- **A bare "1" is read against the welcome, not the conversation.** The welcome's context says "1 =
  continue <project>". When a restarted conversation already holds a question with its own
  numbered answers, `afc-start` doesn't say which one a bare number answers.

## Goal

A restart never changes which world the user is in. Maintenance mode stays on across a resume, clear
or compact until the user turns it off, and a bare number always answers the question just asked.

## Reaches the apps

Yes, in both directions. A user's project session can no longer be pulled into Flight Control work
after a restart, and a Flight Control session can no longer be taken for project work, so an app is
never changed by mistake (`afc/hooks/session_start.py`, `afc/config.py`,
`.claude/skills/afc-start/SKILL.md`).

## You'll know it works when

- A new session that starts as `resume`, `clear` or `compact` in a copy where the session before
  it had maintenance mode on and was last active less than 12 hours ago starts in maintenance mode.
  Its welcome says in one line: "Maintenance mode carried over from your earlier session." A fresh
  `startup` never carries over, and a flag older than 12 hours never does.
- `sh bin/afc maintain off` in the new session turns the whole line off: the earlier sessions'
  switches are removed too, so a later restart does not bring it back. Other sessions that merely
  have maintenance mode on at the same time are not touched.
- A restart of a project session (maintenance off) never starts in maintenance mode.
- `afc-start` says: when the conversation already holds a question with numbered answers, a bare 1
  or 2 answers that question, not the welcome's. If it isn't clear which, ask one question.
- In a live restart with an unanswered "1. Build … 2. Go back to your projects" menu above it, a
  bare "1" is answered from the menu and no project is touched.

## Out of scope

Making maintenance mode global again (FC-036). Changing what maintenance mode allows. The
`source` values Claude Code sends, which we only read. Carrying a project session's state over; a
project session has no switch to carry.

## Design notes

- A carried switch is a new per-session flag, `maintain.d/<new id>`, whose content is the earlier
  session's ID (the line it came from). `maintain off` follows that chain and removes each flag.
  Fork sessions made from a maintenance session are also resumes, so they inherit the mode and
  `maintain off` in one also clears the line it came from; the guard against that is that carrying
  looks only at the single most recent flag in the same copy, and only once (the line is not
  extended again if the earlier flag was already carried).
- 12 hours is a number in `afc/config.py` (`CARRY_AFTER`), not a setting.
- Slice 1 is a measurement, not a guess: it records what a real resume, clear and compact send
  (`session_id`, `source`) in a scratch copy. If `source` isn't sent, or the ID doesn't change,
  the spec is adjusted before slice 2 is built.

## Slices

- [x] 1. See what a restart sends — you'll see it by a scratch copy whose hook writes each event's
      `source` and `session_id` to a scratch file for a real startup, `--continue` (resume), /clear
      and compaction, written in Decisions
- [ ] 2. Carry the switch over — you'll see it by `sh bin/afc hook session_start` run with a
      scratch home: an earlier flag 1 hour old plus `source: resume` and a new ID gives a maintenance
      welcome with the carry-over line and a flag for the new ID; `source: startup` does not; a flag 13
      hours old does not
- [ ] 3. Off ends the whole line — you'll see it by `maintain off` in the carried session removing
      its flag and the earlier one, a still-running unrelated session's flag staying, and a next
      `resume` event starting without maintenance mode
- [ ] 4. A bare number answers the last question — you'll see it by `afc-start` carrying the rule
      and a live `claude --continue -p 1` on a conversation that ends in a "Build / Go back" menu
      answering from the menu, with a scratch project showing no change

## Tasks

Slice 1:
- In a scratch copy of `dev` only, a throwaway hook line writes `session_id` and `source`. Run a
  startup, a `--continue`, a `/clear` and a compaction. Write the four lines in Decisions, then
  discard the copy. Nothing from it lands on `dev`.

Slice 2:
- `afc/config.py`: `CARRY_AFTER = 12 * 3600`; `carry_maintain(home, session, source, now)` finds
  the newest flag in `maintain.d`, and when it is under `CARRY_AFTER` old and `source` is
  `resume`, `clear` or `compact`, writes `maintain.d/<session>` with the earlier ID inside and
  returns True.
- `afc/hooks/session_start.py`: `main` reads `source` from the event and calls `carry_maintain`
  before `build_output`; the maintenance welcome adds the one-line note when it carried.
- `.claude/commands/afc.md`: nothing changes; `/afc mm` stays the only switch.

Slice 3:
- `afc/config.py`: `set_maintain(..., False)` removes the session's flag and follows the earlier
  IDs inside it, removing each, and no other flag.

Slice 4:
- `.claude/skills/afc-start/SKILL.md`: one sentence under First reply, replacing a line rather than
  adding a paragraph.
- Run the live check and write the result in Decisions.

## Decisions

Slice 1, measured 2026-10-26 with Claude Code 2.1.310 in a scratch folder (a SessionStart hook that
only wrote `source` and `session_id`; run with `claude -p`, so no typed /clear; the folder is
discarded, nothing landed on `dev`):

- startup: `source: startup`, new ID (`5c170ff2`).
- `--continue` (resume): `source: resume`, the SAME ID (`5c170ff2`). `--resume <id>` the same.
- compaction (`/compact`): `source: compact`, the SAME ID.
- `/clear`: `source: clear`, a NEW ID (`56dc4aa8`).
- `--continue --fork-session`: `source: resume`, a NEW ID (`c70a583f`).

So `source` is always sent, but the ID changes only on /clear and on a fork, not on a plain resume or
compaction. Slice 2 as written (carry on resume, clear, compact) is still safe, but a plain resume
or compact needs no carrying because `maintain.d/<id>` is already there; the carry matters for
`clear` and for a forked resume. This does not explain the 2026-10-26 incident (new ID `10701c43`,
source unknown): the spec is adjusted before slice 2 is built, and the first adjustment to check
is what source the incident's session sent. Stopped here as the slice says.

## Shipped
