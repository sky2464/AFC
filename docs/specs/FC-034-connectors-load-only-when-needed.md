# FC-034 — Connectors load only when needed

Size: M · Status: in progress

Found on 2026-10-25 (finding R7 in the master plan). With the account add-ons switched off, a
plain "hi" in a Flight Control session still loads 350 tools, 107 skills and 60,291 tokens (FC-027,
measured with `claude -p hi`). Most of the 350 tools are claude.ai connectors from the user's
account (Gmail, Notion, Slack and the like). `enabledPlugins` doesn't reach them.

Asked for on 2026-10-25: don't switch connectors off for everyone. Be smart: load only what's
needed, or only the ones that mean something for the project, chosen on the fly.

## Goal

A Flight Control session starts with only the connectors that matter for the active project, and
anything else is one plain request away. The start costs far fewer tokens, and nobody loses a
connector they need.

## Reaches the apps

Yes. The Flight Control session is where the user's app gets built, so the lighter start and the
per-project connector list apply to every app. The list is stored per project in its workspace
(`~/.A-FC/projects/<name>/`), never in the app's code folder.

## You'll know it works when

- Where the 60k goes is known first: a measured breakdown of a "hi" start into system prompt,
  skill listing, built-in tools, add-on tools and connector tools, with the connectors' share
  written in Decisions. If tool search already defers connector tools, the plan is adjusted to
  match the number.
- Each project has a short list of connectors it uses. It starts from what the project shows
  (for example a GitHub remote means GitHub; design files mean Figma) and from connectors the user
  names. A project with none starts with no connectors.
- At session start, connectors that aren't on the active project's list are blocked for that
  folder (`deniedMcpServers` in `.claude/settings.local.json`, by connector name), and the
  welcome says once, in one line, how many are held back.
- The user can say "I need Gmail" (or any connector) in plain words. Flight Control adds it to the
  project's list, removes it from the blocked set, and says it loads from the next start; the user
  can also switch it on right away from `/mcp`.
- Switching projects swaps the blocked set to the new project's list.
- Anything the user turned on or off in `/mcp` themselves is never overridden. Allowed
  add-on and plugin handling (FC-027) is unchanged.
- The first reply to "hi" on a project with no connectors uses clearly fewer tokens than 60,291,
  measured with `docs/measurements/token_usage.py` before and after; the number goes in Decisions.

## Out of scope

Org or account settings, the desktop app's own sessions (they're governed by the desktop app, not
these settings), and uninstalling connectors; they keep working in every other folder. Changing
the allowed add-on list. Loading a connector in the middle of a session (Claude Code reads the list
at start).

## Design notes

- **Mechanism.** The research found `deniedMcpServers` in settings takes connector names such as
  `claude.ai Slack`. `disableClaudeAiConnectors` is all-or-nothing and any `true` wins, so it
  can't do "only what's needed". `enabledMcpjsonServers` and friends cover `.mcp.json` servers
  only. The per-connector denial is the one that fits.
- **Same pattern as FC-027.** Reuse the add-on switch-off approach in `afc/addons.py`: write the
  block at session start from the SessionStart hook, with the settings undo on failure, never
  breaking the welcome. Takes effect next start, so the welcome line says "from the next start".
- **Finding connector names.** The list of the user's connectors comes from the session itself
  (the connector names Claude Code reports at start); if it can't be read, nothing is blocked and
  the welcome stays quiet.
- **Choosing relevant ones.** A small fixed map from project facts to connector names, kept in
  `afc-addons.json`'s sibling file, plus whatever the user names. No guessing beyond the map.
- **Tool search.** `ENABLE_TOOL_SEARCH` defers MCP tools to names only by default; check whether
  it is on in the measured start, because it changes how much blocking saves.
- **Unverified.** Reload timing of `deniedMcpServers` isn't documented; slice 1 confirms it with a
  restart.

## Slices

- [x] 1. Where the tokens go — you'll see it by a written breakdown of a "hi" start by part, and a
      restart showing a `deniedMcpServers` entry really removes that connector's tools
- [x] 2. A connector list per project — you'll see it by `sh bin/afc` showing a project's connector
      list, filled from what the project shows, and adding one by name
- [x] 3. Hold back the rest at start — you'll see it by a session on a project with no connectors
      starting with those tools blocked, one welcome line, and a second start saying nothing
- [ ] 4. Ask for one in plain words — you'll see it by saying "I need Gmail", seeing it listed and
      unblocked from the next start, with a `/mcp` choice left untouched
- [ ] 5. Live check — you'll see it by two `claude -p hi` starts on the real `A-FC` folder, before
      and after, with the token numbers written in Decisions

## Tasks

Slice 1:
- Extend `docs/measurements/token_usage.py --parts` (or a short script beside it) to split the
  first turn's context by part from a `claude -p hi` transcript. Run on `dev`, with add-ons off.
- Restart a session with one `deniedMcpServers` entry and compare the tool count. Write both
  results in Decisions.

Slice 2:
- A per-project `connectors` list in the project's registry entry or workspace file
  (`afc/registry.py`, `afc/cli_projects.py`); a small map from project facts to connector names;
  commands to show and add (`sh bin/afc connectors`, `sh bin/afc connectors add <name>`).

Slice 3:
- `afc/hooks/session_start.py` and `afc/addons.py`: build the blocked set (user's connectors that
  aren't on the active list and weren't set by the user in `/mcp`), write `deniedMcpServers`
  to `.claude/settings.local.json` with the undo on failure, one welcome line, nothing on a second
  start.
- Switching project (`afc/cli_projects.py`) recomputes the blocked set.

Slice 4:
- `.claude/skills/afc-capabilities/SKILL.md` (and the `afc-start` hint): when the user names a
  connector, run `sh bin/afc connectors add <name>` and say it loads from the next start or now
  from `/mcp`. Keep the skill within its size limit.

Slice 5:
- Run the two starts, write the numbers in Decisions, and ask the user for an OK.

## Decisions

- 2026-10-25: Not off for everyone. Load only the connectors that mean something for the project,
  chosen automatically, and add more on request (user's choice).

- 2026-10-25 (slice 1): Where the 60k goes, measured with `docs/measurements/start_parts.py` (new:
  runs `claude -p hi` with one part switched off at a time, first turn only, on `dev`, add-ons off).
  The "hi" start is 59,687 tokens (350 tools, 107 skills, 10 connectors). Share: connector tools
  17,392 (29%, 319 of the 350 tools); built-in tools, their instructions and project text 33,437
  (56%); skill listing 1,317 (2%); bare floor 7,541 (13%). Tool search is already on: connector
  tools are listed by name only. With it off (`--tools ""` run) the same start was 318,336 tokens,
  so full connector schemas would cost about 300k. So the most blocking can save is about 17k of
  59.7k (29%), not most of it; the goal "clearly fewer than 60,291" is still met, but the spec should
  not promise more. Slice 5 judges the real number.
- 2026-10-25 (slice 1): Restart check. A start with `deniedMcpServers: [{"serverName": "claude.ai
  Notion"}]` (passed as session settings) went from 350 tools / 10 connectors / 59,685 tokens to 285
  tools / 9 connectors / 57,491 tokens, and Notion was gone from the connector list: 65 tools and
  about 2,200 tokens for one connector. The entry works by connector name and takes effect at the
  next start. Note the entry is an object with `serverName`, not a bare string. Not yet tried from
  `.claude/settings.local.json` itself (slice 3 does it).

## Shipped
