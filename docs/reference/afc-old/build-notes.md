# Step 1 build notes (branch `step1-core`)

Status at HEAD (wave 3 on top of c54ff27): 20 plan tasks implemented, each reviewed, plus three cross-cutting fix waves. `bun test` 986 pass, `bunx tsc --noEmit` clean, `claude plugin validate --strict` passes. Nothing is installed globally, merged to `main`, or run against a real project. The four evals have never run (the `claude` CLI was logged out in the build environment).

## Open items before dogfooding (from the last re-review)
| # | Item | Severity | Suggested action |
| :- | :--- | :--- | :--- |
| I1 | Bash guard falsely denies reads whose quoted text ends in `>` (`grep -n "=>" CLAUDE.md`, `grep ">" specs/S-001-*.md`) | Important | **Fixed in wave 3 (df7fb90)**: redirects are read outside quotes by one shared tokenizer (`src/core/shellTokens.ts`) |
| I2 | Bash can still write workspace-root brain files (`CLAUDE.md`, `AGENTS.md`, `playbooks/`, `lessons/`); the brain text and README say the AI cannot | Important | **Fixed in wave 3 (7767f4b)**: the Bash guard denies those write forms, as the file tools do |
| I3 | `templates/workspace/AGENTS.md` l.5 said "Reading is allowed from any session"; a project session cannot read other projects | Important (text) | **Fixed in wave 3** (the I3 commit): "A root session can read every project and code folder; a project session reads only its own." |
| C1 | Session registry is keyed by `session_id`. If Claude Code issues a NEW session id on `/clear` or `--resume`, and the new session starts with the code folder as cwd and no `AFC_PROJECT`, guards are silent | Conditional Critical, unverified live | Open: verify in a real session; if it happens, carry the record across SessionEnd(clear)/SessionStart(resume), or require `afc fly` (which sets `AFC_PROJECT`) and say so in the README |
| m1 | `>|` was not a redirect | Minor | **Fixed in wave 3** (df7fb90) |
| m2 | Interpreter and git writes (`python -c`, `bun -e`, `git checkout -- <file>`) are not gated | Minor | **Documented in wave 3** in the README residual risks; not a guard |
| m3 | A spec read redirected to a temp file (`cat specs/S-001-x.md > /tmp/c.md`) was denied | Minor | **Fixed in wave 3** (df7fb90): a redirect is a spec edit only when its target is a spec |
| m5, m6 | README said SessionStart records only inside the workspace; a registered session's SessionEnd with `afc` missing leaves its record until the 7-day prune | Minor | **Documented in wave 3** in the README |
| F1 | Follow-up: find `-exec` read forms (`find . -name CLAUDE.md -exec cat {} \;`) were denied as writes | Important | **Fixed in wave 3** (8352ee7): a find writes only with `-delete` or a writing `-exec` |
| R1 | Residual Bash forms: writes after `cd`/`pushd` in the same command; `ln -s`, `curl -o`, `wget -O`, `patch`, `rsync`, `unzip -o`, `tar -x`, `cp -t`, `install -t`, `sed --in-place=.bak`; ANSI-C `$'…'` and heredoc bodies; a root session's `rm -rf <OtherProject>` without a trailing slash | Minor | **Documented in wave 3** in the README residual risks. Bash checks are best-effort; Claude Code's permission prompts are the second line |

## Rulings I made (decisions taken on your behalf; each cost noted)
1. Subagents inherit the session model; no per-dispatch Haiku tier was available (no cost savings).
2. Spike (Task 0) automated with `claude -p`; S1 `/memory` listing and S3 interactive autocomplete remain unverified by hand.
3. Stopped before the global install, adopting the real workspace, evals and dogfood (they change your setup and need a logged-in `claude`).
4. Plugin commands are namespaced `/flight-control:*`; the hook accepts bare forms too, but all user-facing text now names the prefixed form (bare unregistered slash commands may not reach the hook).
5. `afc fly` stays in default permission mode (no auto accept-edits); the README says how to switch in-session. Costs extra prompts during `/flight-control:build`.
6. `--plugin-dir` plugins don't appear in `claude plugin list`, so `afc fly` requires a real install.
7. Task 4 repos, Task 5 approvals, Task 7 locks, Task 9 emit, Task 10 scaffold deviate from the verbatim plan code for safety (path validation, atomic id reservation, mkdir-claim lock mutex, physical-path identity, rollback). Reviewers drove these.
8. `specflow`: `done` and `dropped` are final (spec §4.2 amended). A `done` approval is now bound to the spec body hash (wave 1). Cost: you cannot drop a done spec.
9. Reviewer calibration from Task 8 on: single developer, honest-but-fallible AI; exotic multi-process or shell-obfuscation cases are Minor. Cost: some rare races are deferred.
10. Bash and MCP-tool checks are best-effort heuristics (spec §7.1); remaining Bash variants are not chased. Cost: a determined AI could still reach another project's content via Bash; Claude Code's own prompts are the second line.
11. `afc approve|drop|unlock` require a real terminal even with `--yes` (stronger than spec §6). Cost: not scriptable. A pty wrapper could still defeat the TTY check (documented residual).
12. Only one spec may be `building` per project. Cost: an abandoned building spec must be finished or dropped first.
13. Subagents share the parent session's id and scope.
14. Root-session `/flight-control:audit` and `:new` stop after `afc new`; you continue with `afc fly <name>` (approvals can't be recorded in root sessions). Spec §8.3 amended.
15. Bash writes to the project's own code folder are not gated (only file tools are), except config/hook paths.
16. Evals run with `--setting-sources project,local`, narrowed git allow-rules and token env vars stripped; they use `--plugin-dir` and an `afc` shim, so no global install is needed.
17. Config corruption (`~/.config/afc/config.json` unreadable and no `AFC_HOME`) leaves the hooks silent everywhere; failing closed would break every Claude session on the machine. Documented.
18. Several Minor findings were deferred; they are listed in the ledger (`.superpowers/sdd/.../progress.md`, git-ignored) and summarized in the README's residual-risk list.

## To use it
1. `cd ~/Documents/Code/afc` (main checkout; merge `step1-core` first, or use the worktree) → `bun install && bun link`
2. `claude plugin marketplace add <repo path>` → `claude plugin install flight-control@afc-local`
3. `afc init` (fresh path) → `afc fly` → `/flight-control:audit <name> <code-path>` → `afc fly <name>` → `/flight-control:audit`
4. Log in (`claude`, `/login`) and run `bun run evals` once; run the live checks listed under C1.
