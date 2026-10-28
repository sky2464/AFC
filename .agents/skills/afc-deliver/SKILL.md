---
name: afc-deliver
description: Use when an approved slice needs committing and pushing.
user-invocable: false
---

# Deliver

Commit and ship each approved slice. Plain words, at most two next steps.

## First time per project: solo or team

If `sh bin/afc status` shows no team mode (or `unknown`), run `sh bin/afc detect-team`.

- `"confirm": false` — known; use `team_mode`, do not ask.
- `{"confirm": true}` — a local-history guess. Ask once: "Is anyone else working on this project
  with you?" Then `sh bin/afc set team_mode solo` (or `team`).

## Remote

Local-only is fine; `deliver` then just commits. To back up, share or deploy with no remote, use `afc-remote`.

## Deliver the slice

Record the slice first with `sh bin/afc slice record` (`afc-slice`); never edit plan files by hand to do it.
After the commit, if `sh bin/afc plan` still shows the spec in Now with no open slice, run `sh bin/afc plan done <id>`; say nothing of it unless asked.
Changelog and release wording, README edits, findings intake and plan bookkeeping text are written
by the `afc-docs` agent before the commit, never by the builder. Never pass `model` or `effort` when you call an agent; the agent file decides.
Write a short plain commit message starting with the spec ID (e.g. `S-002: health endpoint`):

```
sh bin/afc deliver --message "<message>" [--default-deploys] [--protected]
```

Add `--default-deploys` when pushing the default branch deploys, `--protected` when it is
protected; solo projects then use a working branch (tell the user once).

- `{"pushed": false}` — no remote; committed locally. Say so in one line. A successful deliver also refreshes `resources/afc-brief.md`.
- `{"pushed": true, "pr_needed": false}` — solo: done.
- `{"pushed": true, "pr_needed": true, "branch": ...}` — team: `afc-remote` opens a pull request.

## Never ask, never do

- Never ask the user to approve routine commits or pushes of approved slices.
- These are always the user's own actions, never yours: making a repository public, force-push,
  rewriting history, deleting branches, merging other people's work, and any production deploy.
  If asked, say so and tell them how to do it themselves. The guard blocks them anyway.

## Then

1. Start the next slice: <one line> (recommended)
2. Change the plan first
