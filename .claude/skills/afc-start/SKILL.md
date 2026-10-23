---
name: afc-start
description: Use when a Flight Control session begins or the user wants to start a new project or bring in an existing one.
user-invocable: false
---

# Start

Read the session context line first. Keep every message short, ask one question per message, and
end with at most two numbered next steps, the recommended one first.

## First reply

- **Projects but none active** (`sh bin/afc status` returns `"active": null` and a `projects`
  list): "Which project do you want to work on?" and offer up to two of them as numbered steps
  (more via `sh bin/afc list`, two at a time), then `sh bin/afc switch <name>`. Never loop
  back to `/afc` for this.
- **Returning** (an active project exists): run `sh bin/afc status` and say
  "Welcome back — continue *<project>* (last: <last slice>), or something else?"
  1. Continue *<project>* (recommended) 2. Something else
  If they continue, hand off to `afc-interview` (or `afc-slice` if the intent is already agreed).
- **First run** (no projects; `status` returns `"active": null` and an empty `projects` list): "Are you starting a new project, or working on one that already
  exists on this machine?"
  1. A new project 2. One that already exists

## New project

Ask each of these in its own message, in this order:

1. **Parent folder** — where the app folder should go (Mac or Windows style is fine),
   e.g. `/Users/me/Documents/Code/`.
2. **What to build** — "What would you like to build?" Keep their words; they become the intent.
3. **Name** — use theirs, or offer two or three short lowercase-with-dashes suggestions based on what
   they said.
4. **Git identity** — which name and email this project commits as.
5. **AI trailer** — whether commits carry an AI co-author line (default: off for work projects).

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
