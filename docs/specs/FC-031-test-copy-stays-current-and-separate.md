# FC-031 — Test copy stays current and separate

Size: M · Status: next

Found on 2026-10-25 in an `A-FC-test` session (no projects, maintenance mode off). The user typed
`/afc` twice, then asked "any project running?". What went wrong, in the order the user saw it:

1. **An old Flight Control answered.** `A-FC-test` is a copy of A-FC stuck at FC-009, 154 commits
   behind `dev`. Its first reply introduced Flight Control again, which FC-028 had already fixed.
   Nothing told the user the copy was old, so testing it says nothing about today's build.
2. **A red error before any reply.** `/afc` runs `sh bin/afc status; sh bin/afc plan` together.
   With no active project, `plan` returns an error and exits 1, so Claude Code shows "Error: Exit
   code 1" for what is a normal empty start. Today's `dev` still does this.
3. **A vague health line that came back.** "The health check found 2 problems. I can look." gave no
   detail and no way to fix them. The second `/afc` said it again: "still shows 2 problems, and I
   haven't looked into them." Both were leftover folder permissions for php-vuln-checker, which
   `sh bin/afc repair` fixes with no decision needed.
4. **The second `/afc` just repeated the first.** Same welcome question, same health line, with
   nothing new to say.
5. **The test copy looked into the real workspace.** Those leftover permissions in
   `A-FC-test/.claude/settings.local.json` still gave it access to the real php-vuln-checker
   folders. Asked "any project running?", Claude ran its own `ls` on `~/.A-FC/projects`, found
   php-vuln-checker there and recommended bringing it in. A test copy must never read, offer or
   touch projects from the real workspace.
6. **Behind-the-scenes talk.** The answer named raw paths (`~/A-FC-test-home`, `~/.A-FC/`) and
   said "this test setup can't see it". That breaks plain words by default.
7. **A missing workspace looked like an empty one.** The test home `~/A-FC-test-home` doesn't
   exist. `status` reports no projects without saying so, which is part of why Claude went
   looking elsewhere.

Not Flight Control's doing: the dropped letters in the pasted text ("what you waking pieces", "onn
this computer", "a phder") match lines cut at the terminal's wrap points when the text was copied.
The skill text is whole.

## Goal

A test copy runs today's Flight Control and stays inside its own test workspace. An empty start is
quiet: no red errors, no repeated lines, and any health problem is named in plain words with its
fix.

## Reaches the apps

Does not reach the apps, because it only concerns Flight Control's own test copy and the `/afc`
start; no skill, rule or template in a user's project changes.

## You'll know it works when

- A session in a test copy that is behind `dev` says so once, in one plain line, and offers to
  bring the copy up to date as step 1. The health check lists it as `fixable`, and `repair` moves
  the copy to the tip of `dev` without touching anything else.
- In a test-home session, reading or listing the real `~/.A-FC` (or a project folder registered
  only there) is blocked with a "Flight Control blocked:" line. Flight Control never offers a
  project from another workspace. `repair` removes leftover permissions that point into the real
  workspace.
- When the test home folder doesn't exist yet, the start context says so ("the test workspace is
  empty and will be made with the first project"), so Claude has no reason to look elsewhere.
- `/afc` with no projects shows no error: `plan` is only called when there is an active project,
  or `plan` returns a plain "no active project" result that exits 0.
- The health line names what is wrong in plain words ("2 leftover folder permissions from an old
  project") and offers the fix as a numbered step. It is said once per session; a later `/afc` in
  the same session does not repeat it.
- A second `/afc` with nothing changed is one short line plus the same two steps, not a copy of the
  first reply.
- Answers in a test copy don't name workspace paths unless the user asks.

## Out of scope

Creating or deleting test copies, or a command to make one. Changes to the real workspace or to
php-vuln-checker. The welcome banner's text. Auto-running `repair` without the user saying yes.

## Design notes

- Test copies are git worktrees of A-FC on a detached commit (`A-FC-test` is one). Compare `HEAD`
  with `dev` in the same repository; only check when the workspace is a test home, so normal
  installs never see this.
- The block in slice 2 belongs in the pretool hook's path rules (`afc/hooks/rules_paths.py`), keyed
  on the test home from `.afc-home` or `AFC_HOME`.
- Slice 3 touches `.claude/commands/afc.md` (call order), `afc/cli_plan.py` (no-project result) and
  the health line in `afc/hooks/session_start.py`. Keep skill text short: replace lines, don't add
  paragraphs.

## Slices

- [x] 1. A test copy knows it is behind — you'll see it by a live run that makes a worktree behind
      `dev`, sees `check` report it as fixable and the start context carry one line, and sees
      `repair` move it to the tip of `dev`
- [x] 2. A test copy stays in its own workspace — you'll see it by a live run where a test-home
      session's `ls` or read of the real `~/.A-FC` is blocked, `repair` drops permissions pointing
      there, and a missing test home is named in the start context
- [ ] 3. A quiet empty start — you'll see it by a live run where `/afc` with no projects makes no
      failing call, the health line names the problem and its fix and is said once per session,
      and a live run in an up-to-date `A-FC-test` with two `/afc` and "any project running?"
      shows no error, no repeat and no other workspace

## Decisions

## Shipped
