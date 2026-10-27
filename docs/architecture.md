# Architecture

Flight Control's own architecture memory. Update when a slice adds, removes or renames a module,
boundary or dependency. Never put secrets, keys or passwords here; name where they live instead.

## 1. Goal

Flight Control is a calm co-pilot inside Claude Code that turns what someone wants to build into
small, working, safe slices. It keeps project data out of its own folder, blocks dangerous tool
calls before they run, and updates itself without any user-side tooling.

## 2. Quality attributes

| Quality | How it is checked |
|---|---|
| Safe by default | Guards run as PreToolUse hooks (exit-2 blocks); five core tests in `tests/test_core.py` |
| No foreign writes | `check_paths` blocks writes outside the active project's folders; live run |
| Maintenance boundary | `check_maintenance` blocks project writes while FC itself is being worked on; live run |
| Standard library only | No `pip install` step; `bin/afc` finds Python 3.10+ and runs directly |
| Notes stay short | This file and each app's `plan/architecture.md` stay under 500 lines; checked at review |

## 3. Diagrams

### 3.1 Context

```
User ──► claude (Claude Code session)
              │
              ├─── reads ──► A-FC/  (this repo: skills, hooks, rules, templates)
              ├─── writes ─► ~/.A-FC/  (registry, workspaces, per-project plans)
              └─── writes ─► app folder  (user's code, one project at a time)
```

### 3.2 Containers

```
┌─────────────────────────────────────────────────────────┐
│  A-FC/ (Flight Control repo)                            │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │  afc/ (CLI +    │  │  .claude/ (skills, agents,   │  │
│  │  hooks)         │  │  hooks, the /afc command)    │  │
│  └─────────────────┘  └──────────────────────────────┘  │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │  rules/         │  │  templates/                  │  │
│  └─────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

~/.A-FC/
  projects.json        ← all projects and the active one
  projects/<name>/     ← one workspace per project
    plan/              ← master-plan, specs, architecture, decisions
```

### 3.3 Components

See section 4.

## 4. Containers and components

| Component | Responsibility | Key files |
|---|---|---|
| Hooks and guards | Block dangerous tool calls before they run (PreToolUse); session-start welcome | `afc/hooks/pretool.py`, `afc/hooks/rules_git.py`, `afc/hooks/rules_maintenance.py`, `afc/hooks/rules_paths.py`, `afc/hooks/rules_secrets.py`, `afc/hooks/rules_resources.py`, `afc/hooks/rules_process.py`, `afc/hooks/session_start.py`, `afc/hooks/common.py`, `afc/hooks/shell_text.py` |
| Plan and specs | Read and write the master plan, start and close specs, archive done specs, record slices | `afc/plan.py`, `afc/cli_plan.py` |
| Workspace and registry | Create, relocate and look up project workspaces; load the active project | `afc/workspace.py`, `afc/workspace_upgrade.py`, `afc/registry.py`, `afc/config.py`, `afc/session_dirs.py` |
| Update and release | Fetch and apply updates from origin; numbered upgrade steps for workspace layout changes | `afc/update.py`, `afc/update_apply.py`, `afc/cli_version.py`, `afc/release.py`, `afc/upgrade_001.py`, `afc/version.py` |
| Add-ons and connectors | Track the allowed MCP server list; swap a project's tools in and out per session | `afc/addons.py`, `afc/connectors.py`, `afc/cli_connectors.py`, `afc/tools.py`, `afc/cli_tools.py`, `afc-addons.json` |
| CLI dispatch and support | Entry points, parser, project setup, slice recording, delivery, settings, ship | `afc/cli.py`, `afc/cli_parser.py`, `afc/cli_project_setup.py`, `afc/cli_slice.py`, `afc/cli_delivery.py`, `afc/cli_settings.py`, `afc/cli_ship.py`, `afc/cli_home.py`, `afc/cli_maintain.py`, `afc/cli_projects.py`, `afc/cli_defaults.py`, `afc/cli_awake.py`, `afc/cli_test.py`, `afc/cli_context.py`, `afc/cli_agents.py`, `afc/ship.py`, `afc/git_ops.py`, `afc/undo.py`, `afc/profile.py`, `afc/rules.py`, `afc/secrets.py`, `afc/fingerprint.py`, `afc/jev.py`, `afc/context_brief.py`, `afc/codegraph.py`, `afc/project_agents.py`, `afc/role_agents.py` |
| Skills | Skill dispatchers the Claude session reads: interview, slice, deliver, architecture, etc. | `.claude/skills/afc-architecture/`, `.claude/skills/afc-capabilities/`, `.claude/skills/afc-deliver/`, `.claude/skills/afc-drift/`, `.claude/skills/afc-enterprise/`, `.claude/skills/afc-interview/`, `.claude/skills/afc-profile/`, `.claude/skills/afc-remote/`, `.claude/skills/afc-setup/`, `.claude/skills/afc-slice/`, `.claude/skills/afc-start/` |
| Agents and workflow | Sub-agent definitions and the build-spec orchestration workflow | `.claude/agents/afc-architect.md`, `.claude/agents/afc-builder.md`, `.claude/agents/afc-checker.md`, `.claude/agents/afc-docs.md`, `.claude/agents/afc-plan.md`, `.claude/agents/afc-research.md`, `.claude/workflows/afc-build-spec.js`, `templates/project/agents/` |
| Templates and rules | Starter files for new projects; rule modules loaded per slice | `templates/`, `rules/` |
| Measurements | Health check, code graph index, review and scan, findings | `afc/cli_health.py`, `afc/index.py`, `afc/cli_index.py`, `afc/review.py`, `afc/cli_review.py`, `afc/scan.py`, `afc/gate.py` |

## 5. Data flow

| Where | What lives there |
|---|---|
| This repo (`A-FC/`) | Skills, agents, hooks, rules, templates, the `afc/` CLI, `docs/`, `tests/` |
| `~/.A-FC/` (or `$AFC_HOME`) | `projects.json` (all project records); `projects/<name>/` workspaces (plan, architecture, decisions, specs, index); no user code |
| User's code folder | The app code and tests only; Flight Control writes nothing there except what a slice builds |

Data never crosses from user repos into this repo. Company resources stay in the workspace; they
are never copied into any repo.

## 6. Deployment

Flight Control runs inside the user's Claude Code session. There is no server, no container and no
deploy step. The user keeps their daily folder on `main` (released tags). Updates are pulled with
`sh bin/afc update` from the origin remote.

Developer copy (`A-FC-dev`) works on `dev`; test copy (`A-FC-test`) uses its own `$AFC_HOME`.
See `CONTRIBUTING.md` for the three-folder pattern.

## 7. Security

Each guard is a `check_*` function in `afc/hooks/rules_*.py`; `afc/hooks/pretool.py` runs them on
every tool call. Exit 2 blocks the call and prints the reason.

| Guard | What it stops | Checked by |
|---|---|---|
| `check_undecided` | Project writes and git before the session has chosen Flight Control or the project | live run |
| `check_paths` | Writes outside the active project's code and workspace folders | one of the five core tests |
| `check_maintenance` | Project writes while maintenance mode is on | live run |
| `check_own_copy` | git changes to A-FC itself while maintenance mode is off; non-fast-forward merges and detached checkouts always | live run |
| `check_secrets` | Secret values (tokens, passwords, keys) in a written file; the reason names the pattern, never the value | one of the five core tests |
| `check_resources` | Writes or copies that would carry company resources out of the workspace | live run |
| `check_git` | Force-push, history rewrites, branch deletion, hard resets, making repos public | one of the five core tests |
| `check_process` | `pkill` and `killall` | live run |
| `check_foreign_home` | Any tool call naming the real `~/.A-FC` from a test copy, reads included | live run |

Secrets never go in files. The user's secret store or environment holds them. The `check_secrets`
guard catches a pattern that looks like a secret before it reaches a file.

## 8. Observability

Flight Control has no runtime logs or metrics. Relevant signals:

- `sh bin/afc check` — health check across all projects; reports `kind`, `path`, `detail`
- `sh bin/afc index search` — code graph queries; stale when the index is older than the code
- `sh bin/afc review` — slice review and scan before approval
- `docs/specs/` and `docs/master-plan.md` — the audit trail of every decision

Nothing personal or secret is logged. Session output stays in Claude Code's own transcript.

## 9. Decision links

- The `## Decisions` section of each spec in `docs/specs/` (archived ones in `docs/specs/archive/`)
- `docs/changelog.md` for what each release changed; `docs/findings.md` for open findings

## 10. Maintenance rules

Files stay under 500 lines; boundaries stay as drawn here; big changes get a dated line in the
spec's Decisions section. `sh bin/afc check` reports dead pointers in any Key files cell and unmapped
`afc/` modules, skills, agents and workflows.
