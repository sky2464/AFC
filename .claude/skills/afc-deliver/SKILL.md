---
name: afc-deliver
description: Use when an approved slice needs committing and pushing.
user-invocable: false
---

# Deliver

Commit and ship each approved slice without making the user approve routine git work. Keep every
message short, ask one question per message, use plain words, and end with at most two numbered next
steps, the recommended one first.

## First time per project: solo or team

If `sh bin/afc status` shows no team mode yet (or `unknown`), run:

```
sh bin/afc detect-team
```

- `{"team_mode": ..., "confirm": false}` — already known (recorded earlier, answered by the host, or
  a personal project only you have committed to); use it and do not ask.
- `{"confirm": true}` — the guess came from local history only. Ask once: "Is anyone else working on
  this project with you?" Then record it: `sh bin/afc set team_mode solo` (or `team`).

## Remote and pull requests

A local-only project is fine; `deliver` then just commits. When the user wants the project backed
up, shared or deployed and it has no remote, use `afc-remote`, then come back here.

## Deliver the slice

Write a short commit message in plain words about what the slice does, starting with the spec ID
(e.g. `S-002: health endpoint`). Run:

```
sh bin/afc deliver --message "<message>" [--default-deploys] [--protected]
```

Add `--default-deploys` when pushing the default branch triggers a deploy (CI deploy on `main`), and
`--protected` when the default branch is protected. Solo projects in those cases go to a long-lived
working branch; tell the user once.

- `{"pushed": false}` — no remote; committed locally. Say so in one line. A successful deliver also
  refreshes `resources/afc-brief.md`.
- `{"pushed": true, "pr_needed": false}` — solo: done, no pull request pause.
- `{"pushed": true, "pr_needed": true, "branch": ...}` — team: use `afc-remote` to open a pull
  request from that branch.

## Never ask, never do

- Never ask the user to approve routine commits or pushes of approved slices.
- These are always the user's own actions, never yours: making a repository public, force-push,
  rewriting history, deleting branches, merging other people's work, and any production deploy.
  If asked, say so plainly and tell them how they can do it themselves. The guard blocks them anyway.

## Then

1. Start the next slice: <one line> (recommended)
2. Change the plan first
