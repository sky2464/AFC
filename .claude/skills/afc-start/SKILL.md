---
name: afc-start
description: Use when a Flight Control session begins or the user wants to start a new project or bring in an existing one.
user-invocable: false
---

# Start

Read the session context line first. Short messages, one question each, at most two numbered next steps.

## First reply

The welcome already introduced Flight Control: never introduce Flight Control again. If the first
message is 1 or 2, go into that path (the context line says what they mean), unless the conversation
already holds a question with numbered answers: a bare 1 or 2 answers that question, not the
welcome's (if unclear which, ask one question). On a greeting, say
hello in a few words, then the welcome's question once. Otherwise answer briefly, then ask the
situation's question.

- **A newer release is out** (context says so): ask first: 1. Update now (recommended):
  `sh bin/afc update`. 2. Not now: `sh bin/afc update --skip <new>`, then the project
question. Anything else: answer briefly, then ask the update question. Never both in one message.
- **Undecided** (`Mode: undecided`): ask only the one question from the context line, nothing else.
  1 runs `sh bin/afc maintain on`, 2 runs `sh bin/afc maintain off`, then carry on as that mode.
  Until answered, touch no project.
- **Maintenance mode** (`Mode: maintenance`): this session is for working on
  Flight Control itself. Skip the start flow and never offer or open a project. Say in one line that
  maintenance mode is on and projects are set aside, then ask what to work on:
  1. Keep working on Flight Control (recommended) 2. Go back to your projects (`/afc mm off`)
  A project request needs `/afc mm off`.
- **Projects but none active** (`status` shows `"active": null` and a `projects` list): 1 = pick
  one, 2 = start a new one (`afc-setup`). Ask "Which project do you want to work on?", offer up to
  two as numbered steps (more via
  `sh bin/afc list`, two at a time), then `sh bin/afc switch <name>`. Never loop back to `/afc`
  for this.
- **Only paused projects**: 1 = resume one (`sh bin/afc resume <name>`), 2 = start a new one.
- **Returning** (an active project): "Welcome back — continue *<project>* (last: <last slice>), or
  something else?" 1. Continue (recommended) 2. Something else. On continue,
  run `sh bin/afc status`, then `afc-interview` (or `afc-slice` if the intent is agreed). On
  something else, ask: a new project or another of theirs?
- **First run** (no projects): "Are you starting a new project, or working on one that already
  exists on this machine?" 1. A new project 2. One that already exists (both `afc-setup`).
- **"Held back" connector line in the welcome**: if the user then names one ("I need Gmail"), follow
  `afc-capabilities` (Account connectors); do not ask more.
