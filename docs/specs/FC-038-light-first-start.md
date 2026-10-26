# FC-038 — Light first start

Size: M · Status: in progress

Found on 2026-10-25 in a fresh clone of `main` (see FC-036 and FC-037). The very first start of a
new copy loaded 73,197 tokens for "hi". FC-034 and FC-037 hold connectors back, but they do it from
the SessionStart hook, and Claude Code has already read its settings by then, so the saving only
shows from the second start. The first start is the one every new user sees, and it is the heaviest.

What can and can't be done before the hook runs:

- **Project settings are read at start.** A `deniedMcpServers` list in the tracked
  `.claude/settings.json` of the Flight Control folder is in place before the first start. The
  connector names are known (`claude.ai Gmail`, `claude.ai Notion`, and so on, as FC-034 found).
- **A tracked list can't know this user's connectors.** It can only name the common ones, so a
  connector it doesn't name still loads on the first start, and one the user turned on in `/mcp`
  would be blocked by it.
- **Add-ons are user-specific.** Which ones a user has can't be listed in a tracked file, so their
  first-start cost stays (FC-027 already says "from the next start").
- **A launcher step** (`sh bin/afc start` in place of `claude`) could set everything first, but
  adds a step to the README's two-command install. It is the fallback, not the first choice.

## Goal

The very first "hi" in a new copy costs clearly fewer tokens, with no extra step for the user and
nothing taken away from a connector they use.

## Reaches the apps

Yes. The first start is where every user begins their first app, and the same tracked list applies
to every session in the Flight Control folder, so the lighter session carries into building the app
(`.claude/settings.json`, `afc/connectors.py`, `afc/hooks/session_start.py`).

## You'll know it works when

- Slice 1 settles, by measurement, two open questions and writes both answers in Decisions: whether
  a `deniedMcpServers` list in the tracked `.claude/settings.json` applies on the first start, and
  whether an `allowedMcpServers` entry in `.claude/settings.local.json` (or `/mcp`) still turns one
  of them back on. If the first is no, the rest of the spec stops and the launcher goes to the
  user as a decision.
- A fresh clone of `dev` started with `claude -p hi` uses at least 12,000 fewer tokens than the
  same clone without the list (FC-034 measured about 17,400 for 10 connectors), both numbers in
  Decisions, measured with `docs/measurements/token_usage.py`.
- A connector the user turned on in `/mcp` before the update, or asks for in plain words, loads from
  the next start, and Flight Control never writes over a choice made in `/mcp`.
- The welcome says nothing new on the first start. Its existing connector line (FC-034) still says
  how many were held back, counting the tracked ones.
- Updating to this release is enough: no new README step, and no change to the two-command install.

## Out of scope

A launcher or wrapper command (only if slice 1 says the tracked list fails). Add-ons on the first
start. Changing a project's own list (FC-034) or the no-project hold-back (FC-037).

## Design notes

- The list is built from the connector names `afc/connectors.py known()` can return plus the common
  ones, written as `deniedMcpServers` objects with `serverName` (a bare string is rejected, as FC-034
  found). Keep it in `afc-connectors.json`'s sibling data so the tracked settings and the hold-back
  code share one list.
- `.claude/settings.json` is tracked and shared, so it must not hold anything user-specific: names
  only.
- The hook's `deniedMcpServers` write in `settings.local.json` and the tracked list add together; the
  hook never removes a tracked entry, only adds a connector to `allowedMcpServers` when a user asks
  for it.
- Anything touching the guard or maintenance mode needs the daily folder updated first (see
  CONTRIBUTING): this edits `.claude/settings.json`, so the build is in maintenance mode on `dev`.

## Slices

- [x] 1. Does a tracked list work on the first start? — you'll see it by two first-start
      `claude -p hi` runs in a scratch clone of `dev`, with and without a tracked
      `deniedMcpServers` list, the connector count and token numbers in Decisions, plus one run
      with an `allowedMcpServers` entry showing it wins or not
- [ ] 2. Ship the list — you'll see it by `git diff` on `.claude/settings.json` showing only
      `deniedMcpServers` names, and a fresh scratch clone's first `claude -p hi` using at least
      12,000 fewer tokens than without it
- [ ] 3. Asking for one still works — you'll see it by `sh bin/afc connectors add Gmail` in a
      scratch home putting Gmail in the allow entry and the next start's connector list including
      it, with a connector turned on in `/mcp` left alone

## Tasks

Slice 1:
- Make a scratch clone of `dev` with an empty home; run `claude -p hi` with the project's tracked
  `.claude/settings.json` as is, then with `deniedMcpServers` for the ten claude.ai names, and
  record tools, connectors and tokens. Repeat with a `settings.local.json` `allowedMcpServers`
  entry for one name.

Slice 2:
- `afc-connectors.json` sibling: the name list. `.claude/settings.json`: add `deniedMcpServers`
  from it. A short check in `sh bin/afc check` that the tracked list and the data file agree.

Slice 3:
- `afc/connectors.py` `release`: also add the name to `allowedMcpServers` when it is in the tracked
  list. `afc/cli_connectors.py` reports it.

## Decisions

- Slice 1 measurement (2026-10-25): fresh clones of `dev` at 3af3853, each with its own empty
  workspace (`AFC_HOME`), one `claude -p hi` each (first start), first prompt counted as in
  `docs/measurements/token_usage.py`; tools and connectors read from the stream-json init line.
  - Without a tracked list: 73,310 tokens, 546 tools (515 from servers), 74 servers, all 10
    claude.ai connectors listed (9 connected, Canva needs sign-in). (An earlier plain run gave 73,283.)
  - With `deniedMcpServers` (10 `serverName` objects) in the tracked `.claude/settings.json`:
    56,247 tokens, 227 tools (196 from servers), 69 servers, no claude.ai connector listed.
    Answer 1: YES, a tracked list applies on the first start. Saving 17,063 tokens, above the
    12,000 target. The rest still loaded here are add-ons (user-specific, out of reach as noted).
  - Same tracked list plus `allowedMcpServers` for `claude.ai Notion` in `settings.local.json`:
    43,153 tokens, 28 tools, 0 servers; Notion stayed off. Answer 2: NO, an allow entry does not
    turn a denied connector back on (deny wins).
  - Extra: the allow entry on its own (no deny list): 43,098 tokens, 28 tools, 0 servers, Notion
    not loaded either. So `allowedMcpServers` here behaves as a strict allowlist that switches off
    every other server, and in this headless run did not bring Notion in. Slice 3 must not rely on
    an allow entry to release a connector; it should remove the name from the denying list the
    user controls instead, and the tracked list cannot be overridden from `settings.local.json`.
    This needs deciding before slice 3.

## Shipped
