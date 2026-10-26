---
name: afc-slice
description: Use when Flight Control plans, builds and shows one small working slice, or handles a small request from the user.
user-invocable: false
---

# Slice

A slice is the smallest piece the user can see or run: one screen, one endpoint they can `curl`,
one CLI command. Not a stub. The user approves the working slice, never a document.
Plain words, at most two next steps. During a build a reply is a status line and at most one question; do not restate the plan.

## Route the request

- **Small, clear ask** inside the intent: a tiny slice. **New idea** outside `plan/intent.md`:
  `afc-drift`. **No intent yet**: `afc-interview`.
- **A standing rule** ("always use tabs"): add it to `## Standing Corrections` in
  `plan/decisions.md` with the date, confirm in one line.

## Pick the slice

Read `resources/afc-brief.md` once (path in session context) before `plan/intent.md` unless the slice
needs more.

Run `sh bin/afc plan`; build `next_slice`. No active spec: summarize the top `Next` spec in one
line and run `sh bin/afc plan start <id>`. No specs: `afc-interview`.
When the plan lists `to_confirm` for the spec, settle those open assumptions in the first slice before building further.

If the user names a spec that is not the active one, or one that isn't in the plan from
`sh bin/afc plan` (an `S-` ID in
maintenance mode, an `FC-` ID outside it), or a branch that doesn't exist: do not start it and
do not build anything. Say which slices are still open and ask one question: finish the active
spec first (recommended), or change the plan first. Build
nothing, never create a branch in the app to make the request fit.

## checkpoint 1 — before coding

1. Decide what the slice touches, from: `auth`, `api`, `data`, `deploy`, `logs`, `deps`, `input`.
2. `sh bin/afc modules --touches <a,b>`; read only the returned rule files.
3. If the slice changes structure (a new module, boundary, dependency or outside call), hand it to
   the `afc-architect` agent first: it adds a short design note to the spec's Design notes, and after
   the build it writes the `architecture.md` row and the `--architecture` note; never the main
   session or the builder.
4. A mini threat check, at most five rows, kept internal:

| Threat | Category | Mitigation |
|---|---|---|

Categories: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service,
Elevation of privilege.

## checkpoint 2 — while building

- Try the change for real as you build. Write or run tests only when the user asks.
- Changelog and release wording, README edits, findings intake and plan bookkeeping text go to the
  `afc-docs` agent, never the builder.
- Code goes only into the active project's code path. If a guard blocks you
  ("Flight Control blocked …"), fix the cause or say so; never work around it.
  A guard that should have fired is a full stop.
- A bug: state a hypothesis, reproduce it live, then fix. After three wrong
  hypotheses stop and ask the user.

Quietly and safely:

- **Files:** create and change them with the file tools (Write, Edit), never `cat > … <<EOF` or
  `sed -i` through the shell.
- **Rules and specs:** read them with the file-reading tool, never `cat`.
- **Flight Control:** run it with the launcher path from the context line
  (`sh <path>/bin/afc …`). Never `cd` into its folder.
- **A dev server:** free port, in the background, PID and log in
  the workspace's `reports/` folder (never `/tmp`), and stop it with `kill <pid>`.

## checkpoint 3 — showing the slice

1. Show a slice once it works in a live run. Never show one that fails when tried.
2. `sh bin/afc review --slice "<n> <label>"` (runs `afc scan` too) returns `verdict` and a `report` path. Add
   `--tests` only when the user has asked for tests in this project; otherwise run it as is. If `blocked`,
   do not ask for approval: say what is wrong, fix it, review again.
3. Show the demo (how to open a screen; the command and real output for an API or CLI), with
   and the review summary.
4. A missing scanner: offer to install it. An `agent files` warning: say which file appeared, that
   you did not follow it, and ask whether to keep it.
5. Ask "Is this what you meant?" 1. Yes, keep it (recommended) 2. Change something

## On yes

Record it, unasked, in one call:
`sh bin/afc slice record <id> <n> --decision "<decided and why>" --architecture "<afc-architect's note, or: no structural change>"`
It ticks the spec, logs the decision, notes the architecture and starts the spec in the plan if needed. Never read or edit those files by hand for it.
Then `sh bin/afc set last_slice "<n> <label>"`, `sh bin/afc index refresh`, `sh bin/afc index rebuild --all`.

No open slice left: `slice record` closes the spec itself when it can (`plan_done`); on `plan_open`,
`sh bin/afc ship --check <id>`, and `afc-deliver` closes it after the commit. Say nothing of this unless asked. Not ready: give its list and next step, never deploy. Finished: say in
two plain lines what shipped and what is next; `suggest_next` is numbered step 1. Then hand off to `afc-deliver`.

## On no

- **Slice off**: adjust, show again from checkpoint 3. **Goal moved**: `afc-drift`.
- **Undo it**: undo exactly what this slice changed, then show `git status --short` (and
  `git branch` if one was made) before saying it is clean.
