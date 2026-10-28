---
name: afc-setup
description: Use when the user starts a new project or brings in one that already exists on their computer.
user-invocable: false
---

# Setup
## New project

At most four questions from "1" to a proposed plan. Work out what you can and state it.

1. **What to build** — "What would you like to build?" First, before any folder. Keep their words;
   they become the intent.
2. **Work out the rest** with `sh bin/afc defaults`:
   - **Name** — theirs, or one short lowercase-with-dashes suggestion.
   - **Folder** — `parent` is the recommended folder and is never iCloud-synced. If `parent` is
     null and `suggest_create` is set, propose creating that folder. If both are null, ask for a
     folder and tell them to avoid iCloud-synced ones.
   - **Git identity** — `git_name` and `git_email` are stated with their `source`, not asked,
     unless `"source": "none"`.
   - **AI trailer** — off; state it.
3. **One confirming question**, all together: "I'll set up `php-vuln-checker` in `~/Code`, committing
   as Navid <navid@example.com>, no AI co-author line. OK?"

Then run:

```
sh bin/afc new --name <name> --parent <parent> --git-name "<name>" --git-email <email> [--ai-trailer]
```

- On `{"error": ...}`: explain in plain words and ask the one question that fixes it.
- A `warning` (an iCloud-synced folder): say it in one line, offer another folder.
- A `granted` path not usable yet: "Please type `/add-dir <path>` so I can work in the new folder."
- When the project needs a remote, it is created private (`afc-remote`). Never make it public.

Then hand off to `afc-interview`.

## Existing project

1. Ask for the folder path.
2. `sh bin/afc adopt --name <name> --path <path>` (name: the folder name unless given). Handle
   `error`, `warning` and `granted` as above.
3. **Study before asking**: structure, docs, tests, CI, git state; then `afc-architecture`.
4. Summarize in plain words: what it is, how it is built, what looks healthy or risky.

Then hand off to `afc-interview` with informed questions.
