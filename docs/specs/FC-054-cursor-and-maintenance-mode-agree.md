# FC-054 — Cursor and maintenance mode agree

Size: M · Status: in progress · Started: 2026-10-27 · Done: -
Area: safety

Found on 2026-10-27 while building FC-053 in Cursor (conversation on `dev`). Maintenance mode
showed on for the branch (`sh bin/afc maintain status` → `scope: branch`), but file writes into
A-FC were blocked with "needs maintenance mode" until someone set
`AFC_SESSION=<CURSOR_CONVERSATION_ID>` and ran `maintain on` again (session scope). The same day,
`sh bin/afc deliver` with maintenance on returned "Nothing new to commit" while A-FC's docs were
dirty: deliver always commits the active project's `code_path` (then `php-vuln-checker`), not
Flight Control. `set last_slice` and `index refresh` wrote into that project's workspace too.

Research (2026-10-27): `maintain_scope` ignores the branch switch whenever any session ID is
present (`afc/config.py`); Cursor chats expose a conversation ID that can make the Write path look
session-scoped while `/afc mm` only flipped the branch flag. `cmd_deliver` always calls `_active()`
(`afc/cli_delivery.py`). Welcome cyber flags and update-check freshness are out of scope here
(follow-up FC-055).

## Goal

In Cursor, the welcome, the guards and `sh bin/afc maintain status` agree on whether maintenance
mode is on. With it on, delivering an FC slice commits Flight Control itself and leaves no
bookkeeping aimed at the active project.

## Reaches the apps

Yes. Maintenance mode, `deliver`, `set` and `index` are shared commands. Every user who edits
Flight Control from Cursor (or another tool that gives a conversation ID) gets the same switch
behaviour. Project-only `deliver` outside maintenance mode is unchanged.

## You'll know it works when

- A1. In a Cursor session on `dev`, after `sh bin/afc maintain on` (or `/afc mm`), three reads
  agree: `maintain status` says on, a write into A-FC is allowed by `afc guard --write`, and a
  write into the active project's code folder is blocked. No manual `AFC_SESSION=…` is required.
- A2. `maintain status` (and the `/afc mm` reply) say in plain words which switch applies
  (this chat, or this copy's branch) and that it is never on `main`.
- A3. With maintenance on and an FC spec's docs dirty in A-FC, `sh bin/afc deliver --message "…"`
  commits in the A-FC folder (not the active project). `set last_slice` and `index refresh` in
  that mode do not write into the active project's workspace. After the commit, `sh bin/afc check`
  reports 0 `root_dirty` for Flight Control's own copy.

## Out of scope

Softening the "security officer" welcome or other cyber-classifier wording (FC-055). Making
`update --check` always refresh. Changing Claude Code's per-session switch behaviour when no
Cursor/other-tool ID is involved. Weakening fail-closed guards. Tagging or publishing a release.

## Assumptions to confirm

- [x] Cursor keeps a branch-wide switch as the default for tools without a Claude session ID; when
  a Cursor conversation ID is present, `/afc mm` must still turn maintenance on for that chat's
  writes without a second manual step (branch fallback and/or setting the conversation's session
  flag). Confirmed by user: build FC-054 before the welcome-cyber follow-up.

## Design notes

- `current_session()` today only reads `CLAUDE_CODE_SESSION_ID` and `AFC_SESSION`. Cursor exposes
  `CURSOR_CONVERSATION_ID` (valid session shape). Recognise it (and leave room for the same idea
  on other tools) so `/afc mm` and the Write path share one identity.
- Prefer one resolver used by the CLI, the Cursor adapter and `afc guard`, so status and blocks
  cannot disagree. When a tool session ID is known but its `maintain.d/<id>` flag is off, still
  honour an active branch switch for that tool family (Cursor/Codex/Copilot/Antigravity), so
  branch-wide `/afc mm` covers every chat on `dev`. Claude Code sessions keep today's rule: a
  session ID never falls back to the branch switch.
- `deliver` (and the maintain-mode paths of `set last_slice` / `index refresh`): when
  `maintain_enabled`, operate on `afc_root()` and skip project brief refresh. Outside maintenance
  mode, behaviour is unchanged.
- No new core test file: Flight Control keeps five tests on guards (FC-030). Prove with live Cursor
  runs and `afc guard` / `deliver` JSON.

## Slices

- [x] 1. One mode answer in Cursor — you'll see it by `/afc mm` (or `maintain on`) then
      `maintain status` on, `afc guard --write` allowing a path under A-FC, and a project-folder
      write blocked, with no `AFC_SESSION=…` prefix (proves A1)
- [x] 2. Say which switch — you'll see it by `maintain status` JSON (or plain line) naming scope
      `session` or `branch` in words the `/afc mm` reply also uses, and refusing on `main`
      (proves A2)
- [x] 3. Deliver Flight Control in maintenance mode — you'll see it by a dirty A-FC docs change,
      `deliver --message "FC-054 probe"` creating a commit in A-FC (not the active app), and
      `set last_slice` / `index refresh` leaving the active project's workspace untouched
      (proves A3)

## Tasks

Slice 1:
- `afc/config.py`: recognise Cursor conversation ID; branch fallback for non-Claude tool sessions
  when the session flag is off but the branch switch is on.
- `afc/hooks/adapter.py` / `cli_maintain.py`: same resolver for status and guards.
- Live Cursor check on `dev`.

Slice 2:
- `afc/cli_maintain.py` and `/afc` / skill wording: plain-words scope in status and mm reply.

Slice 3:
- `afc/cli_delivery.py`: when maintain on, commit `afc_root()`, skip project brief.
- `afc` set / index paths used in maintenance: do not write the active project's workspace.
- Live `deliver` on a throwaway docs line, then reset or keep as the slice commit.

## Decisions

## Shipped
