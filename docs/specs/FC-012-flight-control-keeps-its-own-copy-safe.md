# FC-012 — Flight Control keeps its own copy safe

Size: M · Status: in progress · Started: 2026-10-25 · Done: -

Asked for on 2026-10-24, after an update session changed Flight Control's own code with a hand
`git merge` while maintenance mode was off, and left that copy on a detached HEAD.

## Goal

A copy of Flight Control can't be damaged by the work of updating or fixing it. Git that changes
the `A-FC` folder needs maintenance mode, just like every other change there; the folder's own git
health is part of the health check, with a safe repair for the one case that can be repaired; and
when a guard should have stopped something but didn't, Flight Control stops instead of carrying on.

Today the write guard covers file writes into `A-FC` (`afc/hooks/common.py`, "is inside the A-FC
repo and needs maintenance mode") but sees nothing of what git does, so `git merge`, `git pull` and
`git checkout <tag>` all reach Flight Control's own code with the guard silent.

## You'll know it works when

- When maintenance mode is off and a session runs git that changes the `A-FC` folder (`merge`,
  `pull`, `switch`, `checkout`, `cherry-pick`, `revert`, `stash`, `apply`, `am`, `tag`), then it is
  blocked with the maintenance-mode reason, and git that only reads (`status`, `log`, `diff`,
  `show`, `describe`, `tag --list`, `rev-parse`, `ls-remote`, `branch` with no change) still works.
- When maintenance mode is on, then those same commands run in the `A-FC` folder as usual, and the
  project guard (FC-010) is unchanged.
- When a merge in the `A-FC` folder would not fast-forward, then it is blocked with one sentence
  saying to do it themselves, whatever the mode.
- When a git command would leave the `A-FC` folder on a detached HEAD (a tag or commit target, or
  `--detach`), then it is blocked and the reason names the branch to use instead.
- When `sh bin/afc check` runs, then it reports the `A-FC` folder's own problems in plain words —
  detached HEAD, uncommitted changes, a branch that is neither `main` nor `dev`, no `origin` remote
  — and says nothing about it when the folder is clean and on `main` or `dev`.
- When git can't be run at all, then the health check says so once and reports no git problems,
  rather than guessing.
- When `sh bin/afc repair` runs on a detached HEAD whose commit is already on `main`, then the
  folder is back on `main` with nothing lost; a dirty tree, or a commit that is on no branch, is
  left untouched with a one-sentence reason.
- When Flight Control has said an action needs maintenance mode and that action nonetheless
  succeeds with maintenance mode off, then it stops, says so in one sentence, changes nothing else,
  and offers the health check.

## Out of scope

The update flow itself and knowing which version is installed (FC-011). Project repositories' git,
which the maintenance guard already covers (FC-010). Anything that stays the user's own action:
force-push, history rewrites, deleting branches, merging other people's work. Two further findings
from the same review — argparse errors that don't name their allowed values (`sh bin/afc maintain`
→ `Missing state.`) and the first question being asked twice (SessionStart welcome, then
`afc-start`) — are real but belong elsewhere; they are not queued yet.

## Design notes

- **Where the rule goes.** `afc/hooks/rules_maintenance.py` already finds the folders a git command
  works in (`_git_locations`, following `-C`, `--git-dir` and `--work-tree`) and blocks project git
  while maintenance mode is on. FC-012 adds the mirror image: git whose location is `ctx.root`
  needs maintenance mode. Keeping both in that module keeps all the mode-dependent rules together;
  `dangerous_git` in `rules_git.py` stays what it is — the work-losing git that is blocked
  everywhere, in every mode.
- **Reading or changing.** One list of read-only git subcommands, allowed anywhere in any mode;
  everything else counts as changing. An unknown subcommand counts as changing, so a new git verb
  is guarded by default rather than waved through.
- **Fast-forward only.** `merge` is allowed in the `A-FC` folder only with `--ff-only`, and
  `--no-ff`, `--squash` or a plain `merge` of anything that isn't already an ancestor is blocked.
  Whether it would fast-forward is checked with `git merge-base --is-ancestor`, the same
  shell-out-with-git pattern `_scan_commit` already uses, falling back to the block when git can't
  answer.
- **No detached HEAD.** For `checkout` and `switch`, block `--detach` and any target that isn't an
  existing local branch (checked with `git rev-parse --verify refs/heads/<name>`). This is the wart
  that matters most: FC-011 refuses to update a copy that isn't on `main`, so a detached HEAD
  silently ends that copy's ability to update itself ever again.
- **Root health.** `find_problems` in `afc/cli_health.py` walks the registry only. Add one root
  section that runs git in `afc_root()` once, with a short timeout, and reports nothing when git is
  unavailable. The problems are described the way the others are (`_problem(kind, path, fixable,
  detail)`), so `/afc` → Health check explains them two at a time with no new wording rules.
- **Repair.** Only the safe case is fixable: detached HEAD, clean tree, and the commit contained in
  `main` → `git switch main`. Everything else is reported, never fixed, in keeping with the rule
  that risky git stays the user's own action.
- **The behavioural half.** The guard can only cover what it can see. CLAUDE.md's "When a guard
  blocks" section gets a companion: when something that needed maintenance mode happened without
  it, that is a full stop, not a line in a summary. The session this spec comes from said "It
  updated without a maintenance-mode prompt" and carried on.

## Slices

- [x] 1. Changing git in the `A-FC` folder needs maintenance mode — you'll check it by
      `git merge --ff-only <tag>` in the `A-FC` folder being blocked with maintenance mode off and
      running with it on, while `git status` works in both (tests: read-only versus changing
      subcommands, unknown subcommand treated as changing, `-C` / `--git-dir` / `--work-tree`
      locations, project git unaffected)
- [x] 2. No detached HEAD and no surprise merges — you'll check it by `git checkout <tag>` and a
      non-fast-forward `git merge` being blocked with a one-sentence reason, while `git switch dev`
      still works in maintenance mode (tests: `--detach`, tag and commit targets, existing branch
      allowed, `--no-ff` and `--squash` blocked, git unavailable blocks rather than allows)
- [x] 3. The health check sees the `A-FC` folder — you'll check it by `sh bin/afc check` on a
      detached copy naming the problem in plain words, and saying nothing about git on a clean copy
      on `main` (tests: detached, dirty, unexpected branch, missing `origin`, git unavailable)
- [x] 4. Repair puts a stranded copy back — you'll check it by `sh bin/afc repair` moving a clean
      detached copy whose commit is on `main` back onto `main`, and leaving a dirty copy or a commit
      that is on no branch untouched with a reason (tests: both repaired and refused cases)
- [x] 5. A guard that should have fired is a full stop — you'll check it by CLAUDE.md covering the
      case where something needing maintenance mode happened without it, and the skills that act on
      guard output following it (content tests)

## Decisions

- 2026-10-24: Git that changes the `A-FC` folder needs maintenance mode; git that only reads never
  does. An unknown git subcommand counts as changing.
- 2026-10-24: In the `A-FC` folder, merges are fast-forward only and `checkout`/`switch` take an
  existing local branch — no merge commits made by Flight Control, and never a detached HEAD.
- 2026-10-24: `repair` fixes only a clean detached HEAD whose commit is already on `main`;
  everything else is reported, because risky git stays the user's own action.
- 2026-10-25: Slice 3 approved as built. The root problems are reported and never fixable here; repair is slice 4. Git runs in the A-FC folder with a 3-second timeout, twice per welcome, so the welcome can take up to about 6 seconds more in the worst case. Untracked files count as uncommitted changes; git-ignored files do not. Not built yet: the "says so once" line for git that can't run, which is carried to a later slice. Slices 1, 2, 4 and 5 are not built.
- 2026-10-25: Slices 1, 2, 4 and 5 approved as built, plus the "says so once" note for git that
  can't run (`sh bin/afc check` returns a `note`). Pulls in the `A-FC` folder must be `--ff-only`
  in every mode, like merges. Left open as minor: `git checkout -` isn't resolved, a failed
  `git switch main` during repair isn't explained, and `rebase` is allowed with maintenance on.

## Shipped
