---
name: afc-slice
description: Use when Flight Control plans, builds and shows one small working slice, or handles a small request from the user.
user-invocable: false
---

# Slice

A slice is the smallest piece the user can see or run: one screen, one menu, one endpoint they can
`curl`, one CLI command. Not a stub. The user approves the working slice, never a document.
Keep every message short, ask one question per message, use plain words, and end with at most two
numbered next steps, the recommended one first.

## Intake: route the request

- **Small, clear ask** inside the intent (fix a label, add a field, rename a button): go straight
  through the three checkpoints as a tiny slice. No interview.
- **New idea or goal** that does not trace to `plan/intent.md`: use `afc-drift`.
- **Nothing agreed yet** (no intent): use `afc-interview` first.
- **A standing rule** ("always use tabs", "never touch the billing folder"): add it to the
  `## Standing Corrections` section of `plan/decisions.md` with the date, confirm in one line, and
  follow it from then on.

## Pick the slice

Run `sh bin/afc plan`. The next open slice of the active spec (`next_slice`) is the one to build.
With no active spec, take the top `Next` spec: say a one-line summary of it, then run
`sh bin/afc plan start <id>`. If there are no specs at all, use `afc-interview`.
Before building, give a two-or-three-line note:

> **Next slice:** a `/health` endpoint that returns `ok`.
> **You'll check it by:** running `curl localhost:8000/health` and seeing `ok`.

## checkpoint 1 — before coding

1. Decide what the slice touches, from: `auth`, `api`, `data`, `deploy`, `logs`, `deps`, `input`.
2. Run `sh bin/afc modules --touches <a,b>` (leave out `--touches` if it touches none).
3. Read only the returned `rules/<module>.md` files. Do not load the others.
4. Do a mini threat check sized to the slice, at most five rows:

| Threat | Category | Mitigation |
|---|---|---|
| Anyone can call the endpoint | Spoofing | Read-only, no data returned |

Categories are STRIDE: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service,
Elevation of privilege. Keep it internal; mention it to the user only if a mitigation changes what
they will see.

## checkpoint 2 — while building

- Write tests first where the stack has tests; then the code to pass them.
- Keep the rules from checkpoint 1 in context. Files stay under 500 lines.
- Code goes only into the active project's code path. The guards are active: if one blocks you
  ("Flight Control blocked …"), do not work around it; fix the cause or tell the user in plain words.
- Check versions of anything you add against current docs, never from memory.

## checkpoint 3 — showing the slice

1. Run the tests.
2. Run `sh bin/afc scan --slice "<n> <label>"` (e.g. `"3 health endpoint"`). It returns a
   one-line `summary` and the path of the full `report`.
3. Show the demo: for a screen, how to open it; for an API or CLI, the exact command and its real
   output. Put the scan summary on one line beside it.
4. If a scanner is missing, say so and offer to install it (with their approval).
5. Ask: "Is this what you meant?"
   1. Yes, keep it (recommended) 2. Change something

## On yes

Without being asked, update the workspace docs:

- The active spec file — tick the slice (`- [x]`) and note any decision under it.
- `plan/decisions.md` — dated entry for anything decided and why.
- `plan/architecture.md` — only if structure changed (new module, boundary, dependency, external
  call).
- Record the slice: `sh bin/afc set last_slice "<n> <label>"`.
- Refresh the indexes: `sh bin/afc index refresh`, then `sh bin/afc index rebuild --all`.

When `sh bin/afc plan` shows no open slice left in the spec, run `sh bin/afc plan done <id>`, tell
the user in one line that the spec is finished, and offer the `suggest_next` spec as numbered step 1.

Then hand off to `afc-deliver`.

## On no

- **The slice is off** (wrong detail, wrong look): adjust it and show it again from checkpoint 3,
  or checkpoint 1 if what it touches changed.
- **The goal itself moved**: use `afc-drift`.
