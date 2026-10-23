# Flight Control

Flight Control is a folder you open in Claude Code that turns the AI into a careful project lead for
your *other* projects. It works out what you really want one question at a time, then builds one small
piece you can see or run, asks "is this what you meant?", and repeats — with security and architecture
practice built in.

It is "just AI prompting": markdown, skills, hooks and small Python (standard library only) scripts.
No app, no runtime, no SDK.

## The three places

| Place | What is in it | Shared? |
|---|---|---|
| `A-FC/` (this repo) | The brain only: `CLAUDE.md`, skills, the `/afc` command, hooks, rule modules, templates | Yes |
| `~/.A-FC/` (or `$AFC_HOME`) | One private workspace per project (plan, resources, reports, index) and the project registry | Never — outside any repo |
| Your app's own repo | Code and tests only | Per that project |

This repo never holds project data.

## Quick start

```
cd A-FC
claude
```

Then just talk ("start a new project called kong-gateway-lab"). `/afc` is the only command: it shows
where you are and one or two next steps; "More…" reveals the rest. Every reply ends with at most two
numbered next steps.

## What is enforced vs instructed

**Hard-enforced (hooks, run on every tool call; they fail closed):**
- Writes outside the active project (and its workspace) are blocked.
- Writes to A-FC itself are blocked unless maintenance mode is on.
- Likely secrets (keys, tokens, quoted password/api_key assignments) are blocked.
- Company resources cannot be copied into an app repo.
- Git commands that lose work or rewrite history (`reset --hard`, `clean -f`, `branch -D`, force push…)
  are blocked.
- Making anything public (e.g. `gh repo create --public`) is blocked; new remotes are private.

**Instructed (skills and `CLAUDE.md`; the AI follows them, nothing forces it):** the one-question
interview, slice size, drift checks, live docs, scans before delivery, drafting (never sending) emails
and forms, the two-step reply style.

**Limits.** Shell-command detection is best effort: commands are read as text, so an unusual spelling
can slip through. The guards protect against accidents by a cooperative AI, not against a hostile one.

## Running the tests

```
python3 -m unittest discover -s tests -v
```

Tests always use a temp `AFC_HOME`; they never touch the real `~/.A-FC`.

## Editing Flight Control itself

The guard blocks edits to A-FC by default. Turn on maintenance mode from `/afc` → More…, or
`python3 -m afc maintain on`; turn it off with `python3 -m afc maintain off` when done.

See `docs/superpowers/specs/2026-10-21-flight-control-design.md` for the full design and
`docs/superpowers/acceptance/` for acceptance results.
