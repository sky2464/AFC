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
  list): 1 = pick a project, 2 = start a new one (see New project). To pick: "Which project do
  you want to work on?" and offer up to two of them as numbered steps (more via
  `sh bin/afc list`, two at a time), then `sh bin/afc switch <name>`. Never loop back to `/afc`
  for this.
- **Only paused projects** (`status` returns `"active": null`, an empty `projects` list and a
  `paused` list): 1 = resume one, 2 = start a new one (see New project). To resume: "Which one do
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
  1 = a new project (see New project), 2 = one already on this computer (see Existing project).
  Asked again it is: "Are you starting a new project, or working on one that already exists on
  this machine?"
  1. A new project 2. One that already exists

## New project

A new project takes at most four questions from "1" to a proposed plan. Work out everything you
can and state it; ask only what you cannot know.

1. **What to build** — "What would you like to build?" Ask this first, before any folder. Keep
   their words; they become the intent.
2. **Work out the rest.** Run `sh bin/afc defaults` and use its answer:
   - **Name** — use theirs, or suggest one short lowercase-with-dashes name from what they said.
     Ask for a name only if you cannot suggest one.
   - **Folder** — `parent` is the recommended folder and is never iCloud-synced. If `parent` is
     null and `suggest_create` is set, propose creating that folder. If both are null, ask for a
     folder (Mac or Windows style is fine), and tell them to avoid iCloud-synced ones.
   - **Git identity** — `git_name` and `git_email` are stated with their `source`, not asked. Ask
     only when `"source": "none"`: which name and email this project commits as.
   - **AI trailer** — off. State it; do not ask.
3. **One confirming question.** Say all of it together and ask once, e.g. "I'll set up
   `php-vuln-checker` in `~/Code`. Commits will use Navid <navid@example.com>, with no AI co-author
   line; say if you want another. OK?" Change only what they correct.

Then run:

```
sh bin/afc new --name <name> --parent <parent> --git-name "<name>" --git-email <email> [--ai-trailer]
```

- On `{"error": ...}`: explain in plain words and ask the one question that fixes it.
- If the result has a `warning` (for example an iCloud-synced folder on a work project), say it in
  one line and offer to pick another folder.
- If any `granted` path is not yet usable in this session (writing there fails or is refused), tell
  the user in one line: "Please type `/add-dir <path>` so I can work in the new folder."
- When the project needs a remote, it is created private (`afc-deliver`). Never make it public.

Then hand off to `afc-interview`, starting with the intent.

## Existing project

1. Ask for the project's folder path (one question).
2. Run `sh bin/afc adopt --name <name> --path <path>` (name: the folder name unless they give
   one). Handle `error`, `warning` and `granted` as above.
3. **Study before asking.** Without bothering the user, look at: the folder structure and main
   languages, existing docs (README, docs folder), tests and how they run, CI setup, and git state
   (branch, remotes, recent history, uncommitted changes). Then use `afc-architecture` to build the
   architecture picture.
4. Give a short summary in plain words: what it is, how it is built, what looks healthy, what looks
   risky.

Then hand off to `afc-interview` with informed questions.
