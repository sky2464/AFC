---
name: afc-setup
description: Use when the user starts a new project or brings in one that already exists on their computer.
user-invocable: false
---

# Setup

Set up a new project or bring in an existing one.

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
- When the project needs a remote, it is created private (`afc-remote`). Never make it public.

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
