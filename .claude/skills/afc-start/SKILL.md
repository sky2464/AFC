---
name: afc-start
description: Use when a Flight Control session begins or the user wants to start a new project or bring in an existing one.
user-invocable: false
---

# Start

Read the session context line first. Keep every message short, ask one question per message, and
end with at most two numbered next steps, the recommended one first.

## First reply

The welcome line already asked the first question, and the context line says what 1 and 2 mean
("The welcome asked: 1 = …, 2 = …"). If the first message is 1 or 2, that is the answer: go
straight into that path without asking again or greeting at length. For anything else (hi, a
question, a request), answer it briefly, then ask the question below for the situation.

- **Maintenance mode** (the context says `Mode: maintenance`): this session is for working on
  Flight Control itself. Skip the start flow and never offer or open a project. Say in one line that
  maintenance mode is on and projects are set aside, then ask what to work on:
  1. Keep working on Flight Control (recommended) 2. Go back to your projects (`/afc mm off`)
  If asked to build or change a project, say it needs `/afc mm off` first.
- **Projects but none active** (`sh bin/afc status` returns `"active": null` and a `projects`
  list): 1 = pick a project, 2 = start a new one (`afc-setup`). To pick: "Which project do
  you want to work on?" and offer up to two of them as numbered steps (more via
  `sh bin/afc list`, two at a time), then `sh bin/afc switch <name>`. Never loop back to `/afc`
  for this.
- **Only paused projects** (`status` returns `"active": null`, an empty `projects` list and a
  `paused` list): 1 = resume one, 2 = start a new one (`afc-setup`). To resume: "Which one do
  you want to pick up again?" and offer up to two of the paused projects as numbered steps, then
  `sh bin/afc resume <name>`.
- **Returning** (an active project exists): 1 = continue *<project>*, 2 = something else.
  Asked again it is: "Welcome back — continue *<project>* (last: <last slice>, or the active spec from the context line "Active spec: …"), or something else?"
  1. Continue *<project>* (recommended) 2. Something else
  If they continue, run `sh bin/afc status`, then hand off to `afc-interview` (or `afc-slice` if
  the intent is already agreed). For something else, ask what they want: a new project or another
  of their projects.
- **First run** (no projects; `status` returns `"active": null`, an empty `projects` list and no
  `paused` list):
  1 = a new project (`afc-setup`), 2 = one already on this computer (`afc-setup`).
  Asked again it is: "Are you starting a new project, or working on one that already exists on
  this machine?"
  1. A new project 2. One that already exists

## New or existing project

Use `afc-setup` to start a new project (what to build, name, folder, git identity) or to bring in
one that already exists. It hands off to `afc-interview` when it is done.
