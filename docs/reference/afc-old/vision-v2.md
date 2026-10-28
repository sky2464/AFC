# Atoosa Flight Control

> Run your own AI CLI (Claude Code, Antigravity, Copilot CLI, Codex) **inside** Flight Control.
> It becomes a senior, security-minded project manager that plans and builds *other* apps —
> so what gets built is what you pictured, with architecture and security right from day one.

## 1. The problem

People picture one thing and the AI builds another. By the time it's "right", they discover
missing architecture, security, and basic engineering practices that should have been there
from the start. Existing tools either live inside the target repo or wrap the AI CLI in a
heavy UI that doesn't feel native.

## 2. What Flight Control is

- **A folder you run your AI CLI in.** Mostly instructions, commands, skills, agents and memory —
  not an app wrapped around the CLI. You chat natively, as usual.
- **A PM for many projects.** Each managed project has its own subfolder with its own memory,
  specs, sessions and history. The actual code lives anywhere on disk.
- **One-way access.** Flight Control reads and writes the project's code folder. The code folder
  only receives must-have files and never knows Flight Control exists.
- **Proposes, you approve.** It suggests the next spec, reorders, flags risks. Nothing starts,
  merges, or is marked done without your OK. Overrides of security/architecture concerns are
  allowed but logged.
- **Adaptive.** Gauges the user's experience early and adjusts depth and jargon — works for
  non-technical builders and for developers.

## 3. Folder layout

```
~/Documents/Code/Atoosa-Flight-Control/        ← the brain (run claude / agy / copilot / codex here)
  AGENTS.md                                    ← FC persona + rules (shared by all AI CLIs)
  CLAUDE.md                                    ← imports AGENTS.md (+ Claude-specific bits)
  .claude/  (commands, skills, agents)         ← the loop as native commands
  playbooks/                                   ← baseline architecture, security, testing practices
  lessons/                                     ← lessons shared across all projects
  portfolio.md                                 ← all projects: status, current spec, next step
  ProjectX/                                    ← ProjectX's memory (see §4)
  ProjectYZ/
  bin/afc                                      ← small helper CLI (see §7)

~/Documents/Code/ProjectX/                     ← actual ProjectX code
~/ProjectYZ/                                   ← actual ProjectYZ code
```

## 4. Per-project memory (`Atoosa-Flight-Control/<Project>/`)

| File | Purpose |
| :--- | :--- |
| `project.md` | Code folder path, chosen AI CLI, stack, user experience level |
| `intent.md` | End goal in the user's words + what success looks like. **Living**, versioned, never hard-locked |
| `architecture.md` | Current architecture + decision log (what, why, when) |
| `security.md` | Threat notes, baseline checklist status, accepted risks / logged overrides |
| `specs/` | One file per spec: goal, acceptance criteria, status (`proposed → approved → building → review → done / dropped`) |
| `roadmap.md` | Ordered list of specs — freely reordered, edited, dropped |
| `sessions/` | Short log per session: what was done, what changed, what's next |
| `lessons.md` | Project-specific lessons (promoted to `/lessons` when general) |
| `CLAUDE.md` / `AGENTS.md` | Loads this project's memory when a session runs in this folder |

Every session and subagent for a project stays scoped to **that project's FC subfolder + its code folder**.

## 5. The loop (every spec)

1. **Before — capture intent.** One question at a time, multiple choice when possible. Confirm
   understanding back in plain language; separate what the user said from assumptions.
   Check against `intent.md`, `architecture.md`, `security.md`; flag contradictions.
2. **During — build.** The AI CLI works in the code folder against the approved spec, following
   the playbooks (TDD, file-size ceiling, no secrets, dependency hygiene, etc.).
3. **After — feedback before the next spec:**
   - **Intent check** — what was built vs. what was wanted, gaps in plain language.
   - **Quality gates** — tests, security scan, architecture rules, 500-line radar, secrets.
   - **Try it + react** — show the user how to run/see it; their reactions update the roadmap.
   - **Lessons** — record what went right/wrong.
4. **Next** — FC proposes the next spec (or a reorder/change to the goal). User approves.

Goals are allowed to change as the user sees progress. FC's job is to keep architecture,
security and practices consistent through every change, not to freeze the plan.

## 6. Native commands (inside the AI CLI)

| Command | What it does |
| :--- | :--- |
| `/portfolio` | Status of all projects and what's next for each |
| `/new <name> <code-path>` | Interview → create project folder, intent, initial architecture/security, first specs |
| `/focus <name>` | Focus this session on one project |
| `/spec` | Propose / refine the next spec with the user |
| `/build` | Build the approved spec in the code folder (may use subagents, same project scope) |
| `/review` | Run the post-spec loop: intent check, gates, try-it, lessons |
| `/replan` | Goal changed? Update intent and reorder/edit/drop specs, re-check architecture & security |
| `/audit` | Onboard or re-check an existing codebase: what's missing (architecture, security, tests) |

Same commands are exposed to non-Claude CLIs via `AGENTS.md` instructions / their native
command formats where supported.

## 7. `afc` helper CLI (small — only what instructions can't do)

```bash
afc fly ProjectX            # cd into FC/ProjectX and launch the chosen AI CLI with the code folder attached
                            #   e.g. claude --add-dir ~/Documents/Code/ProjectX
afc new ProjectX <path>     # scaffold the project memory folder
afc status                  # portfolio summary in the terminal
afc gates ProjectX          # run scans/gates (tests, radar, secrets, deps) and print results
afc connect                 # detect installed AI CLIs (Claude Code, Antigravity, Copilot, Codex, Ollama)
afc emit ProjectX           # write the must-have files into the code folder
afc ui                      # optional: start the localhost GUI
```

Opening the AI CLI manually in the FC folder works too; `afc fly` is the shortcut.

## 8. Files written into the code folder (only must-haves)

- One rules file per AI CLI in use: `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`
- The current approved spec (so a session opened directly in the code folder still has context)

These contain rules and the current spec only — **no paths or references back to Flight Control**.

## 9. Optional GUI

Light, clean localhost view (`afc ui`) that reads and writes the **same files** through a small
local API. Shows portfolio, roadmap, spec status, gate results. Nice to have — never required.
The CLI and files are the source of truth.

## 10. Carry over from v1 (quietly, not verbose)

- AI CLI detection (`afc connect`)
- Scanner + 500-line radar + test detection
- Interview engine + contradiction checker → becomes the `/new`, `/spec`, `/replan` behavior
- Rulebook emit (`afc emit`)
- Calm, clean visual style for the optional GUI

## 11. Non-goals

- No heavy UI as the main way to work
- No storing FC memory inside target projects
- No auto-advancing specs without user approval
- No custom AI engine — always use the user's existing AI CLI subscription

## 12. First milestones

1. **Spike:** confirm how each AI CLI loads instructions/commands when launched from
   `FC/<Project>/` with the code folder attached (Claude Code first, then Copilot, Codex, Antigravity).
2. FC root `AGENTS.md` / `CLAUDE.md` persona + playbooks (architecture, security, testing).
3. Per-project memory template + `afc new` / `afc fly` / `afc status`.
4. `/new` interview and `/spec` → first end-to-end loop on one real project.
5. `/review` with gates (port v1 scanner + radar) and lessons.
6. `/replan`, `/audit`, `/portfolio`.
7. Optional GUI.

## 13. Success looks like

- Starting a new app from FC feels like normal Claude Code / Copilot — just smarter.
- After the first spec, the project already has sound architecture, security baseline and tests.
- The user can change their mind mid-way and FC keeps everything consistent.
- Target repos stay clean; FC can manage many projects side by side.
