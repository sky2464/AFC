---
name: afc-remote
description: Use when a project needs a remote repository, or a team project needs a pull request opened.
user-invocable: false
---

# Remote and pull requests

The rare parts of delivering: a project's first remote, and a team's pull request. When done, go
back to `afc-deliver`.

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

## Team: open a pull request

GitHub:

```
gh pr create --head <branch> --title "<spec ID>: <slice>" --body "<body>"
```

Azure DevOps:

```
az repos pr create --source-branch <branch> --title "<slice>" --description "<body>"
```

The body has: a short summary of the slice, the scan line from `afc scan`, and links to the plan docs
(`intent.md`, `master-plan.md`, the report in `reports/`). A human merges it; never merge it yourself.
Give the user the pull request link.
