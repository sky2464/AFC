# FC-057 — Cursor edits see maintenance mode

Size: S · Status: done · Started: 2026-10-28 · Done: 2026-10-28
Area: safety

Found on 2026-10-28 after FC-054: in Cursor on `dev`, `sh bin/afc maintain status` said the branch
switch was on, but every Cursor edit to Flight Control's files was still refused with "needs
maintenance mode". Cursor runs the Claude Code edit hook (`afc/hooks/pretool.py`) on its own edits
but sets no `CURSOR_CONVERSATION_ID`, so the hook treated the chat as a Claude Code session, and a
Claude Code session never falls back to the branch switch (FC-054).

Built and merged on `main` as PR #30 (7f68082); brought into `dev` with the merge of `main`.

## Goal

With `/afc mm` on for the branch, Cursor edits to Flight Control's files are allowed, the same as
Cursor shell commands. Claude Code sessions keep their per-session rule.

## Reaches the apps

Yes. The edit hook is shared; every user who edits Flight Control from Cursor gets the fix.

## You'll know it works when

- A1. In Cursor on `dev` with the branch switch on, an edit to a Flight Control file is allowed.
- A2. With the branch switch off, the same Cursor edit is blocked.
- A3. A Claude Code edit still ignores the branch switch and is blocked without its own session
  switch.

## Out of scope

Changing how Claude Code sessions turn maintenance mode on. Any other guard.

## Assumptions to confirm

- [x] Cursor's hook message carries `cursor_version` or `conversation_id`, which Claude Code never
  sends. Confirmed by the live edit to this spec from Cursor on `dev`.

## Design notes

- `pretool._cursor_chat` reads the chat ID from Cursor's own message fields and sets
  `CURSOR_CONVERSATION_ID`, so the FC-054 resolver treats the chat as Cursor's and honours the
  branch switch.
- `afc/hooks/adapter.py` docstring now says Cursor edits go through the Claude Code hook.

## Slices

- [x] 1. Cursor edits see the branch switch — you'll see it by an edit to an A-FC file from Cursor
      on `dev` being allowed with `/afc mm` on, and blocked with it off (proves A1, A2, A3)

## Tasks

Slice 1:
- `afc/hooks/pretool.py`: recognise Cursor by its message fields; mark the chat as Cursor's.
- `afc/hooks/adapter.py`: docstring.
- `tests/test_maintain_branch.py`: three tests for A1, A2, A3.

## Decisions

## Shipped

Shipped 2026-10-28. Slices: 1. Criteria: 0 of 3 proven.
