# Flight Control (A-FC) — Design

*Date: 2026-10-21 · Status: draft for approval · Owner: sky2464*

## 1. Intent and the why

Flight Control is a folder you open in an AI coding tool (Claude Code first) that turns the AI into a
disciplined project lead for your *other* projects. You type `claude` in the A-FC folder, tell it which
project to work on (new or existing), and it plans, builds, tests and documents that project — while
the A-FC folder itself only holds the "brain": rules, workflows, skills, hooks and templates.

It exists because of a concrete failure. Building a Kong API gateway test project in Antigravity, the
user answered a few shallow questions, was handed pages of plans nobody could really picture, said
"approved", and got a web app that wasn't what they imagined — then spent more time reshaping it than
building it. The lesson: **approving a big plan you can't see is not alignment.** Flight Control works
the other way: understand intent deeply, build one small visible piece, confirm, repeat.

The second reason is security and architecture. The user wants top-grade SecDevOps, architecture and
security practice built into every feature by default — including enterprise realities (SSO, Entra/AD,
secrets managers, approved hosting, internal request processes) that most users don't know to ask about.
**Flight Control is the brain: it works out what's needed; the user answers plain questions.**

It must stay "just AI prompting" — no app to lock into, no runtime, no SDK. Markdown, skills, hooks and
small scripts that Claude Code already understands.

## 2. Goals

1. **Intent-first, one-question-at-a-time interview** that researches before asking and builds each
   question on the last answer, producing a full picture that is *not locked*.
2. **Slice-by-slice delivery:** build the smallest piece the user can see or run, show it, ask "is this
   what you meant?", then continue.
3. **Drift detection:** when requests or the AI's own work pull away from the stated goal, stop and run a
   short re-alignment interview.
4. **Live documentation:** plans, decisions, progress and architecture are updated after every slice,
   without the user asking.
5. **Security and architecture by default**, scaled to the project profile, built into each slice, with
   the non-negotiables hard-enforced by hooks.
6. **Project profiling from plain questions** (personal / prototype / MVP / work / enterprise), deciding
   which documents, rules and enterprise steps apply.
7. **Enterprise guidance:** tell the user exactly what to look up in their company wiki, collect it into
   the project's resources folder, and flag people-side steps ("request X from the identity team — here's
   a draft email") when they come due.
8. **Clean separation:** brain in A-FC, project management in a private workspace, code only in the app repo.
9. **Capability discovery:** find current skills, plugins, MCP servers and connectors relevant to each
   project, vet them, install on approval — or write a new skill when none exists.
10. **Git/SecDevOps autonomy** sized to the project (see §9).

## 3. Non-goals (for the MVP)

- Supporting Codex, Antigravity, Cursor, etc. (later, by translating the same brain).
- A runtime, server, UI or installer product.
- Registry/packs, cross-framework import/export, capsules, proof graphs, issue-tracker sync,
  dashboards/metrics (all present in AgToosa; deliberately left out).
- Deploying to production.

## 4. Anti-goals — failure even if it "works"

- Producing big plan documents the user is expected to approve without being able to picture them.
- Building a whole solution before the user has confirmed the first slice.
- Showing the user lists of commands, workflows or options — more than two choices at a time.
- Asking the user to make decisions Flight Control should make itself (e.g. "is this enterprise?",
  "which auth protocol?").
- Interrogation: many questions at once, or questions it could answer by looking.
- Writing code, docs or company material into the wrong place — especially company documents reaching
  the public A-FC GitHub repo or a cloud-synced folder.
- Rules that exist on paper but aren't enforced (AgToosa's hooks were verified not to fire — see §12).
- Instruction bloat: AgToosa carries ~8,600 lines of workflow docs; Flight Control must load only what
  the current step needs.

## 5. Constraints

- **Claude Code first.** Use its native mechanisms: `CLAUDE.md` (the brain's entry point), skills,
  slash commands, hooks (`settings.json`), and access to directories outside the A-FC folder.
- Claude Code **cannot speak first**. On launch a SessionStart hook can show a welcome banner; the first
  real reply comes after the user types anything (even "hi"). The welcome flow is designed around this.
- Hook input arrives as JSON on **stdin** (AgToosa's hooks read an env var instead and silently never
  fire). Every hook ships with a test proving it blocks what it claims to block.
- The A-FC repo will be on GitHub (possibly public). It must never contain project data.
- **Own naming only.** Every folder and file Flight Control creates — in the app repo, the workspace or
  A-FC — uses Flight Control's own names. No third-party tool names (e.g. `graphify-out/`) appear
  anywhere; tool outputs are redirected or renamed into Flight Control's structure.
- Platform: macOS now; paths must also work on Windows later (avoid hard-coded `/` assumptions in docs
  and scripts where practical).

## 6. Where things live

Three places, always separate:

| Place | Contents | Shared? |
|---|---|---|
| `A-FC/` (this repo) | Brain only: `CLAUDE.md`, skills, commands, hooks, rule modules, templates, reusable skill library | Yes — GitHub |
| `~/.A-FC/` (workspace root, location configurable) | One private workspace per project + the project registry | Never — outside any repo |
| The app's own repo (e.g. `~/Documents/Code/kong-gateway-lab/`) | Code and tests only | Per that project |

Workspace layout:

```
~/.A-FC/
  projects.md                    ← registry: name, code path, workspace path, profile, status, last active
  projects/<project-name>/
    plan/        intent.md, decisions.md, progress.md (Now / Next / Done), drift-notes.md,
                 architecture.md (architecture memory)
    resources/   documents the user feeds in (company policies, wiki exports, standards)
    reports/     test results, scan outputs, review notes
    index.db     rebuildable SQLite index of this project, incl. the code graph (see §6.1, §11)
    skills/      skills specific to this project only
```

Why `~/.A-FC/`: outside any git repo (company docs can't be pushed by accident), outside `~/Documents`
(often iCloud-synced, which can breach company policy), one place to back up or wipe. Hidden in
Finder, so "open workspace" is offered from the `/afc` menu (§7.0).

### 6.1 Storage (user decision, 2026-10-21)

**Files are the truth; SQLite is a rebuildable index.**

- Plans, decisions, progress, resources and reports stay as readable files. Anything machine-only that
  must survive (e.g. scan results) is also written as a file (a JSON sidecar next to each report).
- Each project has `index.db` in its workspace: full-text search over its docs and resources, the code
  graph, and links between code, slices, decisions and findings. One cross-project index,
  `~/.A-FC/index.db`, answers questions across all projects (e.g. every open security warning, what
  shipped this month); it never contains company resources.
- Deleting either database loses nothing — Flight Control rebuilds it from files. Rebuilds are
  written to a new file and swapped in atomically, so a failed rebuild never leaves a broken index.
- The index is refreshed after every slice using file fingerprints (incremental), so it never goes stale.
- Databases live in the workspace, never in the app repo.
- Reference design: the user's Agtoosa2 project, which already uses this pattern (markdown truth,
  gitignored `graph.db` with nodes/edges, FTS5, fingerprints, snapshots, federated repos). Borrow the
  schema ideas; fix what it gets wrong for Flight Control (DB inside the app repo, stale index, 30 MCP
  tools of context cost, files over 500 lines).

**Tests:** test *code* lives in the app repo (it must run in CI); test *outputs and reports* go to
`reports/`.

## 7. The user experience

### 7.0 Simple by default (user decision, 2026-10-22)

Absolutely simple and clean: **"1, 2, 3 — done. Next: 1, 2, 3."**

- Every Flight Control reply ends with **at most two** numbered next steps, the recommended one first
  (e.g. "1. Build the health endpoint (recommended) 2. Change the plan first"). Never a menu of
  everything it can do.
- **One visible command: `/afc`.** It shows where you are and the one or two next steps. A "More…"
  choice reveals everything else (status details, switch project, open workspace, help, maintenance
  mode, settings). Plain language works for all of it.
- Skills, rule modules, the CLI and workflows are internal. They are hidden from the slash menu where
  Claude Code allows, and never listed to the user unless asked.
- Default replies use no jargon; technical detail is available on request.
- The interview still asks one question per message (§8.1).

### 7.1 Launch

The user runs `claude` in `A-FC/`. A banner says what Flight Control does and that `/afc` is the only command
to remember. On the user's first message, Flight Control:

- If projects exist in the registry: "Welcome back — continue *kong-gateway-lab* (last: slice 3, health
  endpoint), or something else?"
- Otherwise: "Are you starting a new project, or working on one that already exists on this machine?"

### 7.2 New project

1. Ask for the parent folder (Mac or Windows style), e.g. `~/path/to/projects/`.
2. "What would you like to build?" — e.g. *"An API gateway to learn how Kong works and prepare for an
   interview."*
3. Name: use theirs, or offer a few suggestions.
4. Ask which git identity (name/email) this project commits as, and whether commits carry an AI
   co-author trailer (default: off for work/enterprise profiles). Stored per project in the registry.
5. Create the app folder and must-have starter files (git init, README, .gitignore), the remote repo
   when the project needs one (§9 — **private by default**), the workspace, and the registry entry. For work/enterprise profiles, warn if the
   parent folder is inside an iCloud-synced location.
6. Enter the working loop (§8), starting with intent.

### 7.3 Existing project

1. Ask for the project path.
2. **Study before asking:** read the code and structure, build an architecture picture (§11), check
   existing docs, tests, CI and git state.
3. Present a short summary of what it found, then enter the working loop with informed questions.


## 8. The working loop

```
Intent → Research → Interview (one question at a time) → Full picture (open, not locked)
   → Slice: plan small → build → check → show → "is this what you meant?"
        ↳ yes → update docs → commit → next slice
        ↳ no  → adjust the slice (or re-interview if the goal itself moved)
   → Drift check runs throughout
```

### 8.1 Intent and interview

- Start with **what the user is trying to get done and why**, not features.
- **Research first:** the target project, its architecture, and the web/docs for the domain (e.g. current
  Kong versions and patterns). Never assume versions from memory.
- **One question per message.** Each builds on the previous answer. Infer anything answerable with high
  confidence and *state it* instead of asking. Open questions first; offer 2–3 options (one marked
  recommended) only when the user is stuck or the choice is genuinely technical.
- Output: `plan/intent.md` — goal, who it's for, what success looks like, non-goals, assumptions, risks,
  open questions (AgToosa's Goal Contract fields). It stays editable; nothing is "locked".

### 8.2 Slices

- A slice is **the smallest piece the user can see or run**: one menu, one screen, one endpoint they can
  `curl`, one CLI command. Not a stub.
- For non-visual work (APIs, infra), "show" means a runnable command and its real output.
- Before each slice: a two-or-three-line note of what it is and how the user will check it.
- Approval is of the **working slice**, never of a long document.

### 8.3 Drift

Flight Control watches for two kinds of drift:

- **Intent drift:** new requests that don't trace to `intent.md`, or its own next slice not serving the
  goal.
- **Code drift:** the codebase diverging from `architecture.md` (changed boundaries, new dependencies,
  new external calls).

Response is proportional: a one-line check ("this is heading toward X instead of Y — still right?") for
small drift; a short re-alignment interview when the goal itself seems to have changed. Outcomes go in
`drift-notes.md` and update `intent.md`.

### 8.4 Live docs

After every slice, without being asked: `progress.md` (Now/Next/Done), `decisions.md` (what was decided
and why), `architecture.md` when structure changed, and reports in `reports/`.

## 9. Git and delivery

Flight Control does SecDevOps itself, as far as the project calls for:

| Situation | Behaviour |
|---|---|
| Local or hosted repo, **single developer** | Commit each approved slice and (if a remote exists) push, continuously. **No PR pause.** |
| Hosted repo with **more than one contributor** (GitHub, Azure DevOps first) | Feature branch → push → open a PR with summary, scan results and links to plan docs. A human merges. |
| AWS | CodeCommit is closed to new customers; AWS projects typically mean GitHub/GitLab connected to AWS pipelines — treat as the row above. |

- **Creating remotes (user decision):** for new projects Flight Control creates the remote repo itself
  (GitHub or Azure DevOps), **always private by default**. Making any repo public — at creation or
  later — requires asking the user first and getting an explicit yes.
- **Detecting contributors:** for hosted repos, ask the host (`gh` / `az repos`) for collaborators and
  recent authors, combined with the profile; local `git log` alone is not enough. When unsure, ask once
  and record the answer in the registry.
- **Single-developer branch:** push straight to the default branch, unless that branch triggers deploys
  or is protected — then use a long-lived working branch and tell the user once.

Always needs the user: changing repo visibility to public, force-push, history rewrites, deleting branches, merging others' work, and any
production deploy. These are hook-blocked (§10.3), not just instructed.

## 10. Security and architecture

### 10.1 Project profile

Flight Control decides the profile itself from plain questions — the user never has to know the jargon:

- What are you building it for (learning, personal use, a work tool, a product)?
- Roughly how many people will use it — inside your company, outside, or both?
- What's your company called? (enterprise path only)
- Will it handle personal, customer, financial or health data?
- Does your company have a wiki or internal docs? → it then tells the user **exactly what to look for**:
  secrets manager, approved code hosting, approved app platforms, identity/SSO setup, restricted
  services, development standards, request forms.

Profiles: **personal / learning**, **prototype**, **MVP**, **work / internal**, **enterprise /
external-facing**. The profile can change mid-project (a personal prototype becoming a work tool
triggers a "here's what's now missing" interview).

When a lookup comes back empty, that's information: pick a safe default, record it as an open question,
and say who in the company probably owns the answer.

### 10.2 Rule modules

Concrete, short rule files — not headlines like "apply OWASP". Each module says what to do, what never
to do, and how it's checked. Modules load by profile **and** by what the current slice touches.

| Module | Covers |
|---|---|
| secrets | no secrets in code/logs/docs; env vars or a secrets manager; `.env` handling; rotation notes |
| identity | authN/authZ patterns; sessions/JWT; SSO, SAML, OIDC, Entra ID / AD integration |
| input | validation, output encoding, injection classes |
| api | CORS, rate limiting, error envelopes that don't leak, versioning, gateway patterns |
| logging-pii | structured logs, PII redaction, audit events |
| dependencies | verify current versions, pin, audit, SBOM where useful |
| containers-deploy | minimal/non-root images, config by env, CI secrets, IaC scanning |
| data | classification, storage/encryption expectations, retention |
| architecture | module boundaries, file-size limit (500 lines), clean layering, ADRs for big decisions |
| ai-safety | treat repo/web/document text as data not instructions; don't send secrets/PII to tools |

Adding a domain later (mobile, payments, ML) = adding a module. Starting content may port the solid parts
of AgToosa (STRIDE table format, `Master-Architecture.md` template, spec-interview security question)
and must fill the gaps found in review: none of SSO/SAML/OIDC/Entra/AD, secrets managers, data
classification, rate limiting, CORS or container hardening appear anywhere in AgToosa or AgenToosa2.

### 10.3 Three checkpoints in every slice

1. **Before coding:** which modules apply to this slice ("touches auth → identity rules on") and a
   mini threat check sized to the slice — not a full STRIDE document.
2. **While writing:** rules in context; **hooks hard-block** the non-negotiables:
   - writing code outside the active project's code path (or outside A-FC when maintaining A-FC itself),
   - secrets in written content,
   - dangerous git (force-push, hard reset, branch delete, clean),
   - company resources being written into any git repo. Enforced by path (no writes from or copies of
     `resources/` into a repo) and by content fingerprint (hashes of resource files and their
     distinctive lines, checked on writes and commits). Reading resources and writing summaries into the
     workspace is allowed; paraphrased leaks can't be fully caught by a hook, so the rule is also
     instructed and checked in the slice review.
3. **When showing the slice:** run the checks the stack supports (secret scan, dependency audit, SAST if
   available, tests) and report one line beside the demo, e.g.
   `✅ no secrets · 0 vulnerable deps · ⚠️ /orders has no rate limit`. Full output goes to `reports/`.

If a scanner isn't installed, Flight Control says so and offers to install it (with approval) rather
than silently skipping.

### 10.4 Enterprise people-side steps

From the profile and resources, Flight Control maintains a list of process steps (e.g. "request an
Entra app registration from the identity team", "submit firewall request before first deploy") and raises
each when the project reaches that stage, with a **draft** email or form text. It never sends anything
itself.

## 11. Architecture awareness

- `plan/architecture.md` is the architecture memory (port AgToosa's `Master-Architecture.md` template:
  goal, quality attributes, C4-style diagrams, components, data flow, deployment, security,
  observability, decision links).
- **Flight Control's own code graph (user decision, 2026-10-22; replaces graphify).** A small
  standard-library extractor reads the app's code (files, imports, classes and functions for Python via
  its built-in parser; imports/exports for JS/TS) and writes nodes and links straight into the project's
  `index.db` (§6.1). "Check the current architecture" and "what would this change affect?" are answered
  from that graph rather than the AI skimming files. No third-party graph tool, no wrapper, nothing
  written into the app repo. Agtoosa2's parsers and schema are the reference; scope stays small and grows
  only when a project needs another language.

## 12. Capability discovery

- At project start and whenever a slice needs something new, search for current skills, plugins, MCP
  servers and connectors relevant to the project (e.g. Kong, Docker, the cloud provider).
- Treat third-party ones as **supply-chain risk**: check publisher, maintenance, and the access they
  request; present them; install only on the user's yes, scoped to the project where possible.
- If nothing suitable exists, write a skill (superpowers `writing-skills`): reusable ones go to the A-FC
  skill library; project-only ones go to the workspace `skills/`.
- **Promotion gate:** a skill only moves into the A-FC library after a scrub (no company names,
  hostnames, tenant IDs, internal processes, secrets) and the user's explicit review — the A-FC repo is
  shareable, so library content is treated as published.

## 13. Carried over from AgToosa / AgenToosa2

Reviewed both on 2026-10-21. AgenToosa2 (~520 lines) is the early version; AgToosa (v0.3.63, ~8,600
lines of workflow docs) is the mature one. Flight Control does **not** fork AgToosa: AgToosa installs
`Docs/` into each target repo and approves full specs before building — both opposite to this design.

| | Items |
|---|---|
| **Port (rewritten, shorter)** | Smart interview (infer first, one question, options with a recommendation), Goal Contract fields, intake routing (small asks go straight through; big/security asks get the full loop), Standing Corrections (remembered always/never rules), Now/Next/Done roadmap (AgenToosa2's simpler form), architecture memory template, STRIDE table format, never-assume-versions rule, git guardrail script |
| **Fix while porting** | Approval on working slices, not specs; drift covers intent as well as files; hooks read stdin and are tested (AgToosa's `settings.json` pipes `$CLAUDE_TOOL_INPUT`, which is empty — verified the git guardrail passes `git reset --hard` as installed, while the same script blocks it when given stdin) |
| **Add** | Profiling, enterprise discovery and people-side steps, `~/.A-FC` workspace and registry, path-guard hook, concrete rule modules, own code graph in the index, capability discovery |
| **Leave out** | Multi-platform adapters, packs/registry, interchange, capsules, proof graph, issue sync, dashboard/metrics, 700-line verifier |

## 14. Success

- **First real run:** use Flight Control to build the Kong API gateway learning project. Success = the
  user confirms each slice matched what they pictured, and never had to rebuild something because the
  plan was misunderstood.
- Every hard rule in §10.3 has a test that proves the hook blocks it.
- A fresh session can resume a project from the workspace alone ("welcome back…").
- Company documents are provably never inside a git repo.

## 15. Left to the builder

- Exact file names and structure inside `A-FC/` (skills vs commands vs `CLAUDE.md` sections), as long as
  only what the current step needs is loaded.
- How the active project's code path is granted to the session (additional directories, permissions
  settings, or a restart step) — prefer no restart; if unavoidable, tell the user in one line.
- How hooks learn the active project (e.g. reading the registry).
- Which concrete scanners to recommend per stack (e.g. Gitleaks, Semgrep, `npm audit`, `pip-audit`,
  Trivy), and the exact wording of rule modules.
- Wording of the welcome banner and help text.
- Whether A-FC maintenance itself (improving the brain) needs a separate mode.

## 16. Calls made by Claude (not explicitly decided by the user)

- The single command is named `/afc`; its "More…" choice holds everything else.
- Mini threat check per slice instead of a full STRIDE document.
- Third-party skills/MCPs installed only with approval, scoped per project.
- Reusable created skills → A-FC library; project-only → workspace.
- "More than one contributor" as the trigger for PRs.
- Enterprise emails/forms are drafted, never sent.
- GitHub and Azure DevOps supported first for PRs.
- Git identity and AI co-author trailer asked per project; trailer off by default for work/enterprise.
- Contributor detection via the host's API; solo mode pushes to the default branch unless it deploys or
  is protected.
- Company-resource hook uses path + content fingerprint; paraphrase is caught by review, not the hook.
- Library promotion requires scrub + user review.
- iCloud warning for work/enterprise code folders (code location stays the user's choice).
- The Kong first run is scoped by Flight Control's own interview (local Docker assumed unless the user
  says otherwise).
