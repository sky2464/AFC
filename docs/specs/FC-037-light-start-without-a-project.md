# FC-037 — Light start without a project

Size: S · Status: next, ready for build

Found on 2026-10-25 in the same fresh clone as FC-036. "hi" cost 73,197 tokens. FC-034 measured a
"hi" at 42,818, but only on a second start with an active project. The connector hold-back in
`afc/hooks/session_start.py` (`_connectors_line`) returns early when there is no active project:

```python
active = reg.active()
if active is None:
    return ""
```

So nothing is held back on the starts where users have no project yet: the first-ever start, every
start before the first project exists, and every maintenance-mode start. Every one of them pays for
all the claude.ai connectors (about 17,000 tokens for 10 connectors, measured in FC-034 slice 1),
no matter how often it happens.

What can't change: Claude Code reads its settings before any hook runs, so the very first start of a
new copy always loads everything. Add-ons (FC-027) have the same limit, and their line already says
"from the next start".

## Goal

With no active project, a start still holds back every claude.ai connector, so the second and every
later start costs about the same as FC-034's project start.

## Reaches the apps

Yes. Every user's first steps toward an app (starting or bringing in a project) happen with no
active project yet. Those turns now carry fewer tokens, through `afc/hooks/session_start.py` and
`afc/connectors.py`, and the first project starts from the same lighter session.

## You'll know it works when

- With no active project (no projects at all, or maintenance mode), the start holds back every
  claude.ai connector that isn't on the workspace's own list. The welcome says so once, in the same
  one line FC-034 uses, without a project name ("held back until a project needs them").
- Saying "I need Gmail" with no active project adds it to a workspace-wide list
  (`~/.A-FC/connectors.json`). It loads from the next start and stays until a project is active.
  When one becomes active, that project's own list decides.
- In a scratch copy of `dev` with an empty workspace and add-ons off, two `claude -p hi` starts:
  the second is at or under 45,000 tokens (FC-034's project start was 42,818), measured with
  `docs/measurements/token_usage.py`. Both numbers go in Decisions.
- Anything the user turned on or off in `/mcp` is still never overridden.

## Out of scope

The very first start of a new copy (settings are read before the hook runs). Changing a project's
connector list (FC-034). A launcher that writes settings before Claude Code starts. That would add a
step to the README's two-command install, so it needs its own decision.

## Design notes

- In `_connectors_line`, use the workspace's list when `reg.active()` is None, through a new
  `connectors.hold_for_workspace(root, home)`. It reuses `load`, `to_hold` and `hold`, so the
  undo on failure and the `/mcp` rule come with it.
- Switching from no project to a project swaps to the project's list, like a project switch
  already does.
- The welcome line drops "(not used by <name>)" when there's no project.

## Slices

- [ ] 1. Hold back with no project — you'll see it by a start in a scratch copy with an empty
      workspace writing `deniedMcpServers` for every claude.ai connector, and the welcome saying so
      in one line
- [ ] 2. Ask for one with no project — you'll see it by "I need Gmail" with no active project putting
      Gmail in `~/.A-FC/connectors.json` (scratch home) and taking it out of `deniedMcpServers`
- [ ] 3. Live check — you'll see it by two `claude -p hi` starts in a scratch copy of `dev` with an
      empty workspace, the second at or under 45,000 tokens, both numbers in Decisions

## Tasks

Slice 1:
- `afc/connectors.py`: `hold_for_workspace(root, home)` calls `hold(root, to_hold(...))` with the
  list from `load(home)` (the same `connectors.json` file name, in the workspace root; missing means
  empty).
- `afc/hooks/session_start.py`: `_connectors_line` calls it when there's no active project, with
  the shorter line.

Slice 2:
- `afc/cli_connectors.py`: with no active project, use `afc_home()` as the list's folder instead of
  raising `NO_ACTIVE`, and return `"project": null`.

Slice 3:
- Run the measurement and write both numbers in Decisions.

## Decisions

## Shipped
