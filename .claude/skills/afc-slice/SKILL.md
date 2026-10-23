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

Choose the smallest next piece that moves toward the goal in `intent.md` and that the user can check
themselves. Before building, give a two-or-three-line note:

> **Next slice:** a `/health` endpoint that returns `ok`.
> **You'll check it by:** running `curl localhost:8000/health` and seeing `ok`.

Update `## Now` in `plan/progress.md` with the slice.

## checkpoint 1 — before coding

1. Decide what the slice touches, from: `auth`, `api`, `data`, `deploy`, `logs`, `deps`, `input`.
2. Run `python3 -m afc modules --touches <a,b>` (leave out `--touches` if it touches none).
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
2. Run `python3 -m afc scan --slice "<n> <label>"` (e.g. `"3 health endpoint"`). It returns a
   one-line `summary` and the path of the full `report`.
3. Show the demo: for a screen, how to open it; for an API or CLI, the exact command and its real
   output. Put the scan summary on one line beside it.
4. If a scanner is missing, say so and offer to install it (with their approval).
5. Ask: "Is this what you meant?"
   1. Yes, keep it (recommended) 2. Change something

## On yes

Without being asked, update the workspace docs:

- `plan/progress.md` — move the slice from `## Now` to the end of `## Done` (Done is append-only),
  refresh `## Next`.
- `plan/decisions.md` — dated entry for anything decided and why.
- `plan/architecture.md` — only if structure changed (new module, boundary, dependency, external
  call).
- Record the slice: `python3 -m afc set last_slice "<n> <label>"`.
- Refresh the indexes: `python3 -m afc index refresh`, then `python3 -m afc index rebuild --all`.

Then hand off to `afc-deliver`.

## On no

- **The slice is off** (wrong detail, wrong look): adjust it and show it again from checkpoint 3,
  or checkpoint 1 if what it touches changed.
- **The goal itself moved**: use `afc-drift`.
