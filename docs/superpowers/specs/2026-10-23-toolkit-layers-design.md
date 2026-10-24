# Toolkit layers: Flight Control owns its tools — design

Date: 2026-10-23. Status: approved direction (owner said yes to the three layers); details below are
Claude's calls unless marked.

## 1. Why

On 2026-10-23 two add-ons from the owner's claude.ai account (`agent-recall`, `agent-memory`) kept
switching themselves back on and broke Flight Control's clean start with "command not found" errors.
Everything installed on the account loads into every session, so:

- one broken add-on spoils every Flight Control session;
- a work project's tools (its database, its company's ticket system) leak into personal projects;
- a tool set up well in one project has no clean way to travel to the next.

## 2. The idea (agreed with the owner)

Three layers, with Flight Control in charge and the account kept minimal:

| Layer | Lives in | Holds | Travels |
|---|---|---|---|
| **Flight Control** | the `A-FC` folder | its skills, rules, checks, and an **allowed add-on list**; every other account add-on is switched off inside Flight Control sessions | same everywhere |
| **Shared library** | `A-FC/library/` | proven skills (exists) and **MCP recipes** (new): how to run a server, never its secrets | promoted from a project |
| **Project** | `~/.A-FC/projects/<name>/` | that project's skills (folder exists) and **MCP servers** (new) | swapped in on switch |

## 3. Goals

- Flight Control sessions start clean even when account add-ons are broken.
- Only the active project's own skills and MCP servers are loaded; switching projects swaps them.
- A tool proven in one project can be promoted to the library and added to another project.
- The health check reports add-ons that would break a session and turns them off on repair.

## 4. Non-goals and anti-goals

- **Not** copying other people's plugin code into Flight Control (we would own their updates and
  security fixes). The library holds our own skills and MCP *recipes* only.
- **Not** touching the owner's account-wide settings. Everything is done in the `A-FC` folder's
  local, git-ignored files.
- Failure even if it works: a token or password written into any file; a project's MCP server still
  running after switching to another project; the user asked to approve something they can't
  understand.

## 5. Verified facts (2026-10-23)

- A folder's `.claude/settings.json` with `"enabledPlugins": {"agent-recall@synced": false}` makes
  `claude plugin list` show that account add-on as disabled in that folder. So a folder can switch off
  account add-ons. (Only listed names; there is no "deny all others" switch, so Flight Control must
  list them.)

**TL-1 spike results** (Claude Code 2.1.310, scratch folder outside the repo, checked with
`claude -p ... --output-format stream-json --verbose` init event, `claude plugin list --json`):

1. Git-ignored `.claude/skills/project-demo/SKILL.md` (confirmed ignored with `git check-ignore`):
   **loaded** in a new session.
2. Symlinked skill folder `.claude/skills/project-linked` -> folder outside the project: **loaded**.
3. Git-ignored `.mcp.json` server: **loaded and connected** in headless `-p` mode, with or without
   `enableAllProjectMcpServers` / `enabledMcpjsonServers` in `.claude/settings.local.json`. So
   headless runs need no approval. **Unverified:** whether an interactive session shows an approval
   prompt for a new `.mcp.json` server (I can't drive an interactive session here). The pre-approval
   keys are `enableAllProjectMcpServers: true` or `enabledMcpjsonServers: ["<name>"]` in
   `settings.local.json`; I could not prove they matter, so the plan should set `enabledMcpjsonServers`
   to the managed names as a safe default. (A first attempt with a fake non-MCP command only showed
   status `pending`; that was my bad test server, not an approval wait.)
4. `enabledPlugins: {"agent-sdk-dev@claude-plugins-official": false}` in
   `.claude/settings.local.json`: `claude plugin list --json` reports `enabled: false` there while
   other folders keep it on. **Confirmed** (the earlier settings.json check also holds).

Not checked: whether a change applies mid-session (assumed: next start only).

**Chosen mechanism:** skills by **symlink** into `A-FC/.claude/skills/project-<name>/` (fallback
to copy only if a link can't be made); servers in git-ignored **`A-FC/.mcp.json`**, plus
`enabledMcpjsonServers` for the managed names in `settings.local.json` (tracked by `afcManaged`).

## 6. Design

### 6.1 Allowed add-ons

- `A-FC/afc-addons.json` (tracked): `{"allowed": ["superpowers@claude-plugins-official", …]}` — the
  add-ons Flight Control sessions may use. Starts with the ones the skills actually call
  (superpowers) and nothing else; the owner can add more.
- `sh bin/afc addons` reads every add-on Claude Code reports (`claude plugin list --json`, run from
  the A-FC folder) and returns `{"allowed": [...], "blocked": [...], "unknown_state": bool}`.
- **Health check:** a new fixable problem `addon_not_allowed` for each enabled add-on not on the
  list. **Repair** writes `"<id>": false` for each into `A-FC/.claude/settings.local.json` under
  `enabledPlugins` (tracked by a sibling key `afcBlockedAddons`, like `afcGranted`), and says it
  applies from the next start. Add-ons the user turned off themselves are left alone.
- If `claude` isn't on the PATH, `addons` says so in a plain line and the check skips this part.

### 6.2 Project tools

```
~/.A-FC/projects/<name>/
  skills/<skill-name>/SKILL.md    the project's own skills (folder exists today)
  mcp.json                        the project's MCP servers: {"servers": {name: {command, args, env_keys}}}
```

- `env_keys` names environment variables the server needs; values are never stored.
- On `switch`, `resume` and `new`/`adopt`, Flight Control **swaps tools in**:
  - links each project skill into `A-FC/.claude/skills/project-<skill-name>/` (git-ignored pattern
    `.claude/skills/project-*`), removing the previous project's links;
  - writes the project's servers into `A-FC/.mcp.json` (git-ignored), replacing the previous
    project's, keeping any server the user added by hand (tracked by `afcManaged`, like grants).
  - Mechanism confirmed by the TL-1 spike (section 5): symlink and `.mcp.json`.
- On `pause`/`remove` of the active project the swap clears them, like folder access.
- The health check reports tools that don't match the active project, and repair re-swaps.

### 6.3 Library and promotion

- `A-FC/library/skills/` (exists) and new `A-FC/library/mcp/<name>.json` (a recipe: command, args,
  env_keys, a one-line description, the publisher and the date it was vetted).
- `sh bin/afc tools` lists the active project's skills and servers plus what the library offers.
- `sh bin/afc tools add <name>` copies a library skill or recipe into the active project and swaps.
- Promotion stays the existing gate in `afc-capabilities` (scrub, user review, maintenance mode);
  it now covers MCP recipes too, which must contain no secrets, hostnames or tenant IDs.

### 6.4 Skills and /afc

- `afc-capabilities`: install MCP servers into the project's `mcp.json` (never user-wide), then swap;
  offer library tools first, before searching the web.
- `/afc` → More… gains **Tools**: what this project uses, what the library offers, add one.
- Health check explains blocked add-ons in plain words: "Flight Control switched off <name> in its
  own sessions because it isn't on the allowed list. It still works everywhere else."

## 7. Constraints

- Standard library Python; files under 500 lines; every command tested with a scratch home and a
  scratch A-FC root (as `CliTestCase` does), never the real settings.
- No secrets in any file; `env_keys` only.
- The A-FC repo stays free of project data: generated files (`.mcp.json`, `.claude/skills/project-*`,
  `.claude/settings.local.json`) are git-ignored.

## 8. Calls made here (Claude's)

- An allow-list file in the repo rather than a per-user list.
- Project skills reach Claude by links in a git-ignored folder, pending TL-1.
- MCP servers per project in the workspace's `mcp.json`, swapped like folder access.

## 9. Later

Per-project plugins (if Claude Code adds folder-scoped plugin installs), a "tools" section in the
welcome, sharing a library between people.
