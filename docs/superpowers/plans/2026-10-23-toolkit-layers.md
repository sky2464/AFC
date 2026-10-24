# Toolkit layers — build stories

Design: `docs/superpowers/specs/2026-10-23-toolkit-layers-design.md` (read it first).
Build in order, one commit each, on `dev`.

**Every story:** turn on maintenance mode (`sh bin/afc maintain on`), write the tests first, run
`python3 -m unittest discover -s tests` until it passes, commit, then `sh bin/afc maintain off`.
Standard library only, files under 500 lines, plain errors, no secrets in any file, tests use
`CliTestCase` (scratch home and scratch A-FC root), never the real settings.

**Commands this builds:**

| Command | Does |
|---|---|
| `sh bin/afc addons` | Which account add-ons are allowed or blocked in Flight Control sessions |
| `sh bin/afc tools` | The active project's skills and MCP servers, and what the library offers |
| `sh bin/afc tools add <name>` | Copy a library skill or MCP recipe into the active project |

---

## TL-1 · Spike: how Claude Code picks up tools (throwaway)

As the builder, I know which mechanism works before building on it.

- [ ] In a scratch folder with its own `.claude/`, check and write down:
      1. a skill in a git-ignored `.claude/skills/project-demo/SKILL.md` shows up in a new session;
      2. a symlinked skill folder there shows up too;
      3. a server in a git-ignored `.mcp.json` loads, and whether Claude asks to approve it;
      4. `enabledPlugins: false` in `.claude/settings.local.json` disables an account add-on there.
- [ ] Record results and the chosen mechanism in section 5 of the design doc. No product code.

## TL-2 · Allowed add-on list

As a user, Flight Control knows which account add-ons belong in its sessions.

- [ ] Add `afc-addons.json` at the repo root: `{"allowed": ["superpowers@claude-plugins-official"]}`.
- [ ] New `afc/addons.py`: `allowed(root) -> list[str]`, `reported(root) -> list[dict]` (runs
      `claude plugin list --json` from `root`; returns `[]` and a flag when `claude` is missing),
      `blocked(root) -> list[str]` (enabled and not allowed).
- [ ] New command `sh bin/afc addons` in a new `afc/cli_tools.py`, registered like `cli_health.py`.

**Tests:** new `tests/test_addons.py` with `claude` replaced by a fake script on `PATH` (as
`tests/test_launcher.py` does): allowed vs blocked, `claude` missing → plain flag, bad JSON → plain
error.

## TL-3 · Health check switches off add-ons that don't belong

As a user, a broken account add-on never spoils a Flight Control start again.

- [ ] `afc/cli_health.py`: problem `addon_not_allowed` (fixable) per blocked add-on, with the plain
      detail from design §6.4.
- [ ] `afc/session_dirs.py`: `block_addons(root, ids)` writes `"<id>": false` under
      `enabledPlugins` in `.claude/settings.local.json` and tracks them in `afcBlockedAddons`;
      ids later added to the allowed list are unblocked on the next repair.
- [ ] Repair line: "Switched off <n> add-on(s) in Flight Control sessions; this applies from the next
      start."

**Tests:** `tests/test_cli_health.py`: check finds it, repair writes it, a user's own `false` entries
and other keys stay, allowing an add-on again removes the block.

## TL-4 · Project tools swap in on switch

As a user, only the active project's skills and MCP servers are loaded.

- [ ] Workspaces gain `mcp.json` (`{"servers": {}}`) via the workspace template.
- [ ] New `afc/tools.py`: `swap_in(root, ws)` and `clear(root)` using the TL-1 mechanism; skills land
      in `.claude/skills/project-<name>/`, servers in `.mcp.json`, both tracked so a user's own
      entries survive; `env_keys` only, values never written.
- [ ] Call `swap_in` wherever folder access is granted (`switch`, `resume`, `new`, `adopt`) and
      `clear` wherever it is cleared (`pause`, `remove` of the active project). Roll back with the
      existing `Undo` on failure.
- [ ] `.gitignore`: `.mcp.json`, `.claude/skills/project-*`.

**Tests:** new `tests/test_tools.py`: switching between two projects swaps skills and servers, a
hand-added server stays, pause clears, a server entry with a literal token value is refused with a
plain error.

## TL-5 · Health check covers project tools

As a user, a repair fixes tools that don't match the active project.

- [ ] `afc/cli_health.py`: problem `tools_out_of_sync` (fixable) when the loaded project skills or
      servers differ from the active project's; repair calls `swap_in` or `clear`.

**Tests:** `tests/test_cli_health.py`: delete a linked skill by hand → check finds it → repair
restores it.

## TL-6 · Library MCP recipes and `tools add`

As a user, a tool proven in one project can be added to another in one step.

- [ ] `library/mcp/` (with `.gitkeep`) for recipes: `{command, args, env_keys, description,
      publisher, vetted}`.
- [ ] `sh bin/afc tools` → `{"project": {"skills": [...], "servers": [...]}, "library":
      {"skills": [...], "servers": [...]}}`.
- [ ] `sh bin/afc tools add <name>` copies a library skill or recipe into the active project, then
      swaps; plain errors for unknown name, already there, no active project.

**Tests:** new `tests/test_cli_tools.py`: list, add skill, add server, the three errors.

## TL-7 · Skills and /afc use the layers

As a user, Flight Control offers my proven tools first and keeps new ones in the project.

- [ ] **afc-capabilities:** offer library tools first (`sh bin/afc tools`); install MCP servers into
      the project's `mcp.json`, never user-wide; promotion gate also covers MCP recipes (no secrets,
      hostnames or tenant IDs).
- [ ] **/afc** → More… gains **Tools** (this project's tools, the library, add one).
- [ ] Health check wording for blocked add-ons as in design §6.4.

**Tests:** `tests/test_content.py`: capabilities names `sh bin/afc tools`, `/afc` has `**Tools**`.

## TL-8 · Docs and end-to-end check

- [ ] README FAQ: "Why are some of my add-ons off in Flight Control?" (one short answer).
      CONTRIBUTING: new files.
- [ ] In a developer clone with a scratch `AFC_HOME`: two projects, a library recipe added to one,
      switch back and forth, `tools` shows the right set each time; `check` is clean.
- [ ] Full suite on every installed Python.
