# FC-041 — Maintenance mode survives a new session

Size: M · Status: in progress

Found on 2026-10-26. The user was in maintenance mode, working on FC-040 (session `f79266d7…`).
Claude Code then started a new session in the same folder (`10701c43…`, a fork that kept the whole
conversation). Nobody turned maintenance mode off, but the switch is saved against the old
session's ID, so the new session read it as off. Its welcome offered "1 = continue php-vuln-checker" and the
user's "1", meant for the earlier question ("Build FC-040"), was taken as that. A slice was built in
the user's app, and had to be undone. FC-010 (the first maintenance mix-up) was meant to make this
impossible; FC-036 made the switch per session and removed the only thing that crossed a restart.

Two causes, both Flight Control's:

- **The switch belongs to a session ID, and a fork or /clear has a new one.** `afc/config.py` keeps
  `maintain.d/<session id>`. Nothing tells the new session that maintenance work was just under
  way here, and nothing stops project work until it knows.
- **A bare "1" is read against the welcome, not the conversation.** The welcome's context says "1 =
  continue <project>". When a restarted conversation already holds a question with its own
  numbered answers, `afc-start` doesn't say which one a bare number answers.

## Goal

A new session never guesses which world the user is in. When a fork or /clear follows recent
maintenance work, it asks one question first and shields every project until the user answers. A
bare number always answers the question just asked.

## Reaches the apps

Yes, in both directions. A user's project session can no longer be pulled into Flight Control work,
and a Flight Control session can no longer be taken for project work, so an app is never changed by
mistake (`afc/hooks/session_start.py`, `afc/hooks/rules_maintenance.py`, `afc/config.py`,
`.claude/skills/afc-start/SKILL.md`).

## You'll know it works when

- A new session that starts as `resume` or `clear` with a session ID Flight Control hasn't seen
  before, in a copy where some other session turned maintenance mode on less than 12 hours ago,
  opens with one question and nothing else: "1. Keep working on Flight Control (recommended)
  2. Go to your project". A plain resume or compaction (same ID), a fresh `startup`, a flag older than 12 hours, or
  no flag at all never asks.
- Until the user answers, project work is blocked: project code writes and project git stop with a
  plain "Flight Control blocked: choose Flight Control or your project first" line. Answering 1 runs
  `sh bin/afc maintain on` (this session only); answering 2 runs `sh bin/afc maintain off`. Either
  one lifts the block.
- A bare 1 or 2 answers the question just asked in the conversation, not the welcome's. If it
  isn't clear which, `afc-start` asks one question.
- In a live fork of a conversation that ends in a "1. Build … 2. Go back" menu, a bare "1" is
  answered from that menu, and a scratch project shows no change.
- A project session that is forked or cleared while no maintenance session is recent starts
  exactly as today.

## Out of scope

Making maintenance mode global again (FC-036). Changing what maintenance mode allows. The `source`
values Claude Code sends, which we only read. Carrying the mode over silently (the user chose to
be asked, 2026-10-26).

## Design notes

- "A session ID Flight Control hasn't seen" is a file `~/.A-FC/sessions.d/<id>` the hook touches
  at every start (pruned after 7 days like the maintenance flags). A plain resume or compaction keeps
  its ID, so it finds the file and never asks.
- "Undecided" is a file `maintain.d/<id>.ask`. `maintain on` and `maintain off` both remove it.
  The pretool guard reads it before anything else and blocks project code writes and project git
  while it exists; Flight Control's own folder is not blocked, so the session can still run
  `maintain on`/`off` and read the plan.
- The question's text comes from the welcome's context; it is not left to the model. `afc-start`
  has a case for it ("Mode: undecided"): ask the question, nothing else, answer 1 with
  `sh bin/afc maintain on`, 2 with `sh bin/afc maintain off`.
- 12 hours is a number in `afc/config.py` (`ASK_WITHIN`), not a setting.
- Slice 1 measured the events (see Decisions). The 2026-10-26 incident was a fork: it had a new ID,
  kept the whole conversation, and the desktop app had forked the conversation several times.

## Slices

- [x] 1. See what a restart sends — you'll see it by a scratch copy whose hook writes each event's
      `source` and `session_id` to a scratch file for a real startup, `--continue` (resume), /clear
      and compaction, written in Decisions
- [ ] 2. Ask when a fork or clear follows maintenance work — you'll see it by `sh bin/afc hook
      session_start` run with a scratch home: another session's flag 1 hour old plus `source: resume`
      and an unseen ID gives a context with "Mode: undecided" and the one question, and the same
      event again (ID now seen), `source: startup`, a flag 13 hours old, and no flag at all each
      give the normal welcome
- [x] 3. Nothing touches a project until answered — you'll see it by the pretool hook, in that
      scratch home with the `.ask` file present, blocking a Write into the project's code folder and
      a `git status` there with the "choose first" line, `maintain on` or `maintain off` removing
      the file, and the same Write then allowed after `maintain off`
- [ ] 4. A bare number answers the last question — you'll see it by `afc-start` carrying the
      "undecided" case and the bare-number rule, and a live `claude --continue --fork-session -p 1`
      on a conversation that ends in a "Build / Go back" menu answering from the menu, with a
      scratch project showing no change

## Tasks

Slice 2:
- `afc/config.py`: `ASK_WITHIN = 12 * 3600`; `seen(home, session)` touches `sessions.d/<id>` and
  returns whether it already existed (pruned at 7 days); `needs_choice(home, session, source,
  now)` is true when `source` is `resume` or `clear`, the ID was unseen, this session has no
  flag, and another session's flag is under `ASK_WITHIN` old. It writes `maintain.d/<id>.ask`.
- `afc/hooks/session_start.py`: `main` reads `source`, calls `seen` and `needs_choice` before
  `build_output`; when true the context says "Mode: undecided" with the question and that no
  project may be touched, and the welcome message carries the same one line.

Slice 3:
- `afc/hooks/rules_maintenance.py` (and `rules_paths.py` if the project paths live there): when
  `maintain.d/<id>.ask` exists, block project code writes and project git with the "choose first"
  line.
- `afc/config.py`: `set_maintain` (on or off) removes the `.ask` file.

Slice 4:
- `.claude/skills/afc-start/SKILL.md`: a case for "Mode: undecided" and one sentence for the bare
  number rule, replacing lines rather than adding paragraphs.
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

- 2026-10-26: the incident was a fork (new ID, conversation kept, `source: resume`). A fork or /clear
  cannot tell by itself whether it continues maintenance work, so the user chose to be asked first
  over carrying the mode silently: one question at the start, and project work blocked until it is
  answered. Slices 2 to 4 rewritten to match.

Slice 3, tried 2026-10-26 with the pretool hook in a scratch home (one registered scratch project
with a git folder, `maintain.d/other` as the recent flag, `maintain.d/sess1.ask` present):

- With `sess1.ask`: a Write into the project's code folder, `git status` in it, and
  `git -C <project> status` run from the A-FC folder were each stopped with exit 2 and "Flight
  Control blocked: choose Flight Control or your project first". Reading a file in the project's
  workspace (the plan) and `sh bin/afc maintain status|on|off` run from the A-FC folder were
  allowed (exit 0). A session without an `.ask` file (`sess2`) writing to the project was allowed.
- `AFC_SESSION=sess1 sh bin/afc maintain off` removed `sess1.ask` (and made no flag); the same
  Write and `git status` were then allowed. `maintain on` also removed the file and left
  `maintain.d/sess1`; the Write was then stopped by the normal maintenance-mode line instead.
- The guard is a separate rule, `check_undecided`, placed before `check_paths` in the pretool list,
  so the "choose first" line wins over other blocks. It reuses the project-reach test of
  `check_maintenance` (now `_reach`), so the two cannot drift. `Context` has an `undecided` field.
- Not mine, seen on the way: `sh bin/afc ...` typed with a project folder as the working directory is
  "couldn't read this command safely" (by `check_paths`, with or without an `.ask` file). The
  session runs the maintain commands from the A-FC folder, as `afc-start` does, so this does not
  get in the way.

## Shipped
