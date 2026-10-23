---
name: afc-deliver
description: Use when an approved slice needs committing and pushing, a pull request opened, or a new project needs a remote repository.
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

- `{"team_mode": ..., "confirm": false}` — the host answered; use it.
- `{"confirm": true}` — the guess came from local history only. Ask once: "Is anyone else working on
  this project with you?" Then record it: `sh bin/afc set team_mode solo` (or `team`).

## Does it need a remote?

A local-only project is fine; `deliver` then just commits. When the project needs a remote (the user
wants it backed up, shared, or deployed) and has none:

1. Ask: "Should this live on GitHub or Azure DevOps?"
   1. GitHub (recommended for personal projects) 2. Azure DevOps
   If they say AWS: explain in one line that AWS CodeCommit is closed to new customers, so AWS
   projects keep their code on GitHub or GitLab and connect it to AWS pipelines; then ask GitHub or
   Azure DevOps.
2. Ask for the organization if it is not their personal account (one question). For Azure DevOps also
   the project, if it is not configured.
3. Run:
   ```
   sh bin/afc create-remote --host github|azure [--org <org>] [--project <project>]
   ```
   The repository is always private. On `error`, explain in plain words and ask the one question that
   fixes it (for example, not signed in to `gh` or `az`: ask the user to sign in themselves).

## Deliver the slice

Write a short commit message in plain words about what the slice does. Run:

```
sh bin/afc deliver --message "<message>" [--default-deploys] [--protected]
```

Add `--default-deploys` when pushing the default branch triggers a deploy (CI deploy on `main`), and
`--protected` when the default branch is protected. Solo projects in those cases go to a long-lived
working branch; tell the user once.

- `{"pushed": false}` — no remote; committed locally. Say so in one line.
- `{"pushed": true, "pr_needed": false}` — solo: done, no pull request pause.
- `{"pushed": true, "pr_needed": true, "branch": ...}` — team: open a pull request from that branch.

## Team: open a pull request

GitHub:

```
gh pr create --head <branch> --title "<slice>" --body "<body>"
```

Azure DevOps:

```
az repos pr create --source-branch <branch> --title "<slice>" --description "<body>"
```

The body has: a short summary of the slice, the scan line from `afc scan`, and links to the plan docs
(`intent.md`, `progress.md`, the report in `reports/`). A human merges it; never merge it yourself.
Give the user the pull request link.

## Never ask, never do

- Never ask the user to approve routine commits or pushes of approved slices.
- These are always the user's own actions, never yours: making a repository public, force-push,
  rewriting history, deleting branches, merging other people's work, and any production deploy.
  If asked, say so plainly and tell them how they can do it themselves. The guard blocks them anyway.

## Then

1. Start the next slice: <one line> (recommended)
2. Change the plan first
