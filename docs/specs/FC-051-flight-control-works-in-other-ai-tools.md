# FC-051 — Flight Control works in other AI tools

Size: L · Status: in progress · Started: 2026-10-27 · Done: -
Area: safety

Asked for on 2026-10-26: changing Flight Control from Cursor, Antigravity, Codex, GitHub Copilot and
similar tools, not only Claude Code. Scope chosen: the full experience in all four tools.

Why it fails today (seen on 2026-10-26): `/afc mm` run from Cursor refused to turn maintenance mode
on, because Flight Control ties the switch to the Claude Code session ID (`CLAUDE_CODE_SESSION_ID`,
FC-036/FC-041) and Cursor gives none. The same is true of everything else Flight Control enforces: the
guards, the `/afc` command and the `afc-*` skills are Claude Code hooks and features. Another tool
can edit the files, but nothing blocks a risky edit.

What the other tools offer, checked against each vendor's own docs on 2026-10-26 (slice 1):

| Tool | Instructions | Hooks | Can block before an action |
|---|---|---|---|
| Cursor | `AGENTS.md`, `.cursor/rules` | `.cursor/hooks.json` (project), `~/.cursor/hooks.json` | shell, MCP and file reads (`beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile`); file edits only after the fact (`afterFileEdit`); exit code 2 blocks; other failures allow unless `failClosed` |
| Codex | `AGENTS.md` | `<repo>/.codex/hooks.json` or `config.toml`; project hooks load only when the folder is trusted and each hook is reviewed once | `PreToolUse` covers shell (`Bash`), `apply_patch` edits and MCP; its docs call hooks "a useful guardrail, not a complete enforcement boundary" |
| Copilot | `.github/copilot-instructions.md` | `.github/hooks/*.json` with `"version": 1`; CLI, cloud agent (fewer events), app, VS Code (public preview) | `preToolUse` can deny |
| Antigravity | `AGENTS.md` or `GEMINI.md` (workspace, folder and `~/.gemini`), `.agents/rules/*.md`; 24,000 bytes per file | `.agents/hooks.json` (project), `~/.gemini/config/hooks.json` | `PreToolUse` can deny, by JSON on stdout only (no exit codes documented) |

Sources: cursor.com/docs/hooks, learn.chatgpt.com/docs/hooks, docs.github.com (Copilot "About hooks"),
antigravity.google/docs/hooks, /docs/rules and /docs/plugins.

## Goal

Someone can change Flight Control from Cursor, Codex, GitHub Copilot or Antigravity and get the same
protection and the same plain-words flow as in Claude Code, with no step they must remember.
Where a tool cannot block an action, a check at commit time catches it.

## Reaches the apps

Not at first. This is about Flight Control's own repository. Slice 5 decides whether an app's code
folder gets the same instruction files; until then apps are unchanged.

## You'll know it works when

- A1. One command, `sh bin/afc guard`, decides allow or block for an action given as plain input
  (a shell command or a file path), using the same rules the Claude Code hooks use today. The Claude
  Code hooks call it, and give the same answers as before.
- A2. A git pre-commit check and a CI check refuse a commit that breaks a guard rule (project code in
  A-FC, a secret in a file, edits to Flight Control while maintenance mode is off), whichever tool
  made the edit.
- A3. Maintenance mode needs no session ID: with none, `maintain on|off` switches it for the copy's
  current branch (never `main`), and `sh bin/afc maintain status` says `branch`. Claude Code sessions
  keep their own per-session switch, unchanged. (Changed on 2026-10-26 from "on in `dev`, off
  elsewhere", which would have turned it off in worktrees and on for every session in a dev copy.)
- A4. One file, `AGENTS.md`, is generated from `CLAUDE.md` and kept in step by a check. Cursor, Codex
  and Antigravity read `AGENTS.md` themselves (checked in slice 1), so only Copilot gets a pointer
  file, `.github/copilot-instructions.md`.
- A5. For each of Cursor, Codex, Copilot and Antigravity, a hook file calls `afc guard` where that
  tool supports hooks, and the spec records, per tool, what it can and cannot block.
- A6. The `/afc` flow works from a plain `sh bin/afc` start in any tool, with the same short
  numbered next steps. Where a tool has no slash commands, the instructions file says what to type.
- A7. `sh bin/afc check` reports, per tool, which of instructions, hooks and commit check are in
  place, in plain words.

## Out of scope

- Making Claude-only features (subagent routing from FC-050, skills loading) work in other tools.
- Any change that weakens a Claude Code guard.
- Publishing or pushing anything; the user does that.

## Assumptions to confirm

- [x] Codex hooks exist and use `.codex/hooks.json`; they run only after the user trusts them (checked 2026-10-26).
- [x] Antigravity reads `AGENTS.md` and has hooks that can deny (checked 2026-10-26).
- [ ] Cursor cannot block a file edit before it happens (only shell, MCP and reads); the commit check must cover edits. Its docs don't say which hooks the CLI fires.
- [ ] Copilot hooks: public preview in VS Code; other surfaces not labelled preview. Treat as best effort.
- [ ] A branch-based switch (dev = on) is safe: it cannot be on by accident in a user's app.

## Design notes

- The guard logic lives in one place (`afc guard`). Each tool's hook file is a thin caller, so there
  is one set of rules, not four.
- The commit-time check is the one guard that works in every tool, so it is the safety floor; hooks
  are the faster, earlier layer on top.
- Maintenance mode by branch was chosen on 2026-10-26 over a file switch: it works the same in every
  tool and needs no ID. Refined the same day to a fallback used only when no session ID exists.

## Slices

- [x] 1. Confirm what each tool supports — you'll see it by a table of Cursor, Codex, Copilot and
  Antigravity with source links and what each can block, and the assumptions above ticked or struck
  (proves A5)
- [x] 2. One shared guard — you'll see it by `sh bin/afc guard` giving the same answers as today's
  Claude Code hooks on a set of sample actions (proves A1)
- [x] 3. Commit and CI check — you'll see it by a commit that breaks a rule being refused from a plain
  terminal with no Claude Code (proves A2)
- [x] 4. Maintenance mode by branch — you'll see it by `maintain status` saying on in `dev` and off
  elsewhere, with no session ID set (proves A3)
- [x] 5. Instruction files — you'll see it by `AGENTS.md` and the per-tool pointer files matching
  `CLAUDE.md`, and a check that fails when they drift (proves A4)
- [x] 6. Hook adapters — you'll see it by a blocked action in each tool that supports hooks (proves A5)
- [x] 7. `/afc` flow and health line — you'll see it by `sh bin/afc check` listing each tool's state
  (proves A6, A7)

## Tasks

Slice 1:
- docs/specs/FC-051-flight-control-works-in-other-ai-tools.md: replace the table with checked facts

## Decisions

- 2026-10-26: scope is all four tools and the full experience; maintenance mode follows the git
  branch.

## Shipped

- Slice 7 (2026-10-26): `sh bin/afc check` now has an `other_tools` list, one plain line per tool
  (instructions, hook and what it can block, commit check on/off/missing) and a line on turning the
  commit check on; `instructions_out_of_date` is a problem when AGENTS.md or the Copilot pointer
  drifts. A6: any tool starts the flow by following `.claude/commands/afc.md`, which `AGENTS.md`
  points to; `sh bin/afc status` and `plan` work with no Claude Code. All seven slices are built;
  not yet run inside the real tools (see slice 6).
- Slice 6 (2026-10-26): `sh bin/afc hook adapter <cursor|codex|copilot|antigravity>` turns each tool's
  payload into the event the Claude Code guard reads and answers in that tool's words; with no
  Python or a bad `.afc-home` it blocks (exit 2). Hook files: `.cursor/hooks.json`,
  `.codex/hooks.json`, `.github/hooks/flight-control.json`, `.agents/hooks.json`. Cursor blocks shell
  commands and file reads (it has no hook before an edit); the others block shell and edits. Built
  from each vendor's docs and tested with sample payloads, NOT yet run inside the real tools:
  Codex needs the user to trust the hook once; Copilot's `toolArgs` shape and Antigravity's exit
  codes are not documented, so a first real run in each tool should confirm them.
- Slice 5 (2026-10-26): `sh bin/afc instructions` checks and `--write` regenerates `AGENTS.md` (a
  preface for non-Claude tools plus CLAUDE.md) and the Copilot pointer; a test fails when they drift,
  so CI catches it. Apps are unchanged: they get no instruction files yet.
- Slice 4 (2026-10-26): with no session ID, `maintain on|off` uses `maintain.branch.d/<branch>`
  (never on for `main`, expires after 7 days); a session with an ID never reads it. The guard now
  blocks A-FC edits from other tools when it is off and allows them when it is on. The commit check
  does not enforce this: CI has no maintenance state and would fail every pull request.
- Slice 3 (2026-10-26): `sh bin/afc guard --staged` and `--since REF` run the secret rule over changed
  files; `.githooks/pre-commit` (turn on with `git config core.hooksPath .githooks`) and a CI step in
  `tests.yml` call them. Only the secret rule is covered so far: "project code in A-FC" has no
  commit-time form yet, and "editing Flight Control while maintenance is off" waits for slice 4, when
  maintenance follows the branch. A2 is not fully met until then.
