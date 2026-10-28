---
name: afc-architecture
description: Use when Flight Control needs to know or update the structure of the app, or answer what a change would affect.
user-invocable: false
---

# Architecture

`plan/architecture.md` is the architecture memory. The code graph in the workspace index answers
structure and impact questions, so you do not skim files to guess. Keep every message short, ask one
question per message, use plain words, and end with at most two numbered next steps, the recommended
one first.

Writing `plan/architecture.md` (or `docs/architecture.md` in maintenance) and every structure
decision is the `afc-architect` agent's job, never the main session's or the builder's; reading the
graph and answering questions stays here. Never pass `model` or `effort` when you call an agent; the agent file decides.
In a tool other than Codex, before architecture work run `sh bin/afc model --role architect`;
when `ask` is true and `suggest` is set, ask once in this session whether to switch, then
`sh bin/afc model choose <model>` if they take the switch.

## Keep architecture.md current

It holds: goal, quality attributes, diagrams (context, containers, components), components, data
flow, deployment, security, observability and links to decisions. Update it when a slice changes
structure: a new module, boundary, dependency or external call. Keep it short; a diagram in a code
block beats a paragraph. Big choices get a dated entry in `plan/decisions.md` linked from here.

## Build the code graph

For existing code (adopted projects) or once code grows past a few files, run:

```
sh bin/afc index refresh
```

It reads the app's code (files, imports, classes, functions) and writes the graph into the
workspace `index.db`. Nothing is written into the app repo.

## Answer structure and impact questions

Before reading files by hand:

- "What would changing X affect?" → `sh bin/afc graph impact X`. It returns JSON with `name`
  and `matches` (the linked nodes). Read only the files those matches point to.
- "Where is X?" or "what did we decide about X?" → `sh bin/afc index search "X"`. Add `--all` to
  search across projects.

If the graph is empty or stale (the answer names files that no longer exist), run
`sh bin/afc index refresh` and ask again.

Give the user the answer in plain words, not the JSON: "Changing `save_order` touches the checkout
screen and the nightly export."

## After a slice

When a slice changed structure, refresh the graph with `sh bin/afc index refresh`, then have
`afc-architect` update `plan/architecture.md` and return a one-line note. Never pass `model` or `effort` when you call an agent; the agent file decides. If a new module, skill,
agent or workflow was added or removed, it updates the Key files cell in the Components table so
`sh bin/afc check` finds no unmapped paths. If nothing structural changed, leave both alone.

## Checking the current architecture

When asked "how is this built?" or before a big change:

1. Refresh the graph.
2. Compare what the graph shows with `plan/architecture.md`.
3. Fix the document where it drifted, and tell the user in one or two lines what was out of date.

End with, for example:

1. Carry on with the next slice (recommended)
2. Show me the diagram
