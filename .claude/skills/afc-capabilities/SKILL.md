---
name: afc-capabilities
description: Use when Flight Control starts a project or a slice needs something new, to find, vet and add skills, plugins, MCP servers or connectors.
user-invocable: false
---

# Capabilities

Good tools save work, but every third-party tool is a supply-chain risk. Flight Control searches,
checks, shows the user, and installs only on their yes. Keep every message short, ask one question per
message, use plain words, and end with at most two numbered next steps, the recommended one first.

## When to search

- At project start, once the stack and platform are known.
- When a slice needs something new (a gateway, a container tool, a cloud provider, a design tool).

Do not search on every slice; only when there is a real new need.

## Where to search

0. Our own library first: run `sh bin/afc tools`. If the library already offers a skill or MCP
   recipe that fits, offer it and add it with `sh bin/afc tools add <name>` (on the user's yes).
   Only search further when it has nothing suitable.
1. Plugin search (the plugin catalog) for skills and plugins.
2. The MCP registry for MCP servers and connectors.
3. Web search for current options and recent news about them. Never rely on memory for what exists
   or which version is current.

## Vet before showing

For each candidate, check and show the user this short list:

| Check | What to look for |
|---|---|
| Publisher | who makes it; official vendor or known maintainer |
| Maintenance | last release or commit date; open issues ignored? |
| Access requested | files, network, accounts, tokens it wants |
| Install scope | project-only possible, or user-wide only |

Drop anything with an unknown publisher plus broad access. Show at most two options, the safer one
first, with one line on why.

## Install

- Only on the user's yes, asked in its own message.
- Scope it to the project where possible, never user-wide when project-only works.
- MCP servers go into the project's `mcp.json` in its workspace (`{"servers": {name: {command,
  args, env_keys}}}`), never user-wide and never with secret values: list only variable names in
  `env_keys`. Then run `sh bin/afc switch <project>` to swap it in; it loads from the next start.
- Any sign-in, token or OAuth step is the user's to do; tell them where.
- Record what was added and why in `plan/decisions.md`.

## Nothing suitable

Write a skill with superpowers `writing-skills`:

- Project-only skill: save it in the workspace `skills/` folder.
- Possibly reusable: still save it in the workspace `skills/` first. It may move to the A-FC library
  only through the gate below.

## Promotion gate to library/skills/ and library/mcp/

The A-FC repo is shareable, so anything in `library/skills/` or `library/mcp/` counts as published.
A skill, or an MCP recipe (`library/mcp/<name>.json` with command, args, env_keys, description,
publisher, vetted date), moves there only when all of this holds:

1. **Scrub** it: no company names, hostnames, tenant IDs, internal processes, people, or secrets.
   Replace them with neutral placeholders.
2. Show the scrubbed skill to the user, and they review it and say yes in their own message.
3. Flight Control is in maintenance mode (the user turns it on from `/afc` → More). Outside
   maintenance mode, A-FC is not writable, so the copy waits.

Turn maintenance mode off again when done. If any check fails, the skill stays in the workspace.

End with, for example:

1. Install the first option for this project only (recommended)
2. Skip it for now
