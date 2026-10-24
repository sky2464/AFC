# Master plan — build stories

Design: `docs/superpowers/specs/2026-10-23-master-plan-design.md` (read it first).
Build the stories in order, one commit each, on `dev`.

**Every story:** turn on maintenance mode (`sh bin/afc maintain on`), write the tests first, run
`python3 -m unittest discover -s tests` until it passes, commit, then `sh bin/afc maintain off`.
Standard library only, files under 500 lines, errors are plain sentences, nothing is ever deleted.

**Commands this builds:**

| Command | Does |
|---|---|
| `sh bin/afc plan` | Show the active spec, its next slice, the next two specs, the done count |
| `sh bin/afc plan add "<title>" [--size S\|M\|L]` | New spec in Next |
| `sh bin/afc plan start <id>` | Next → Now (one at a time) |
| `sh bin/afc plan done <id>` | Now → archive, suggest the next spec |

---

## MP-1 · Templates and folders

As a new project, I start with a master plan and a place for specs and finished work.

- [ ] Add `templates/workspace/plan/master-plan.md` with headings Goal, Now, Next, Done, Update log
      and these empty tables: Now `ID | Title | Size | Spec | Started`, Next `ID | Title | Size | Spec`,
      Done `ID | Title | Done | Spec`, Update log `Date | Event`.
- [ ] Add `templates/workspace/spec.md` (outside `plan/`): first line `# {id} — {title}`, header
      `Size: {size} · Status: next · Started: - · Done: -`, headings Goal, You'll know it works when,
      Out of scope, Design notes, Slices, Decisions, Shipped.
- [ ] Remove `templates/workspace/plan/progress.md`.
- [ ] `afc/workspace.py`: `PLAN_SUBDIRS = ("specs", "archive")`, created inside `plan/`.

**Tests:** `tests/test_workspace.py` (plan files list, subfolders), `tests/test_content.py` (both
templates' headings).

## MP-2 · Plan module

As Flight Control, I can read and update the master plan and specs safely.

- [ ] New `afc/plan.py` with: `read_rows(text, section)`, `write_rows(text, section, rows)`,
      `cell(value)` (`|` → `/`, whitespace collapsed), `slugify(title)` (max 40 chars, `"spec"` if
      empty), `next_id(ws)` (`S-001`…, counts the archive too, never reuses), `open_slices(spec_text)`,
      `all_slices(spec_text)`, `set_header(spec_text, status=, started=, done=)`,
      `log(text, date, event)`, `compact(ws)`.
- [ ] `compact`: Done keeps its 10 newest rows (newest first); Update log keeps 100 rows, older ones
      appended to `plan/archive/updatelog-<year>.md`.

**Tests:** new `tests/test_plan.py`: rows round trip, a title with `|` stays one row, missing section
raises `ValueError`, slugs, `next_id` with an archived `S-007` gives `S-008`, open vs all slices,
header update, compaction.

## MP-3 · Plan commands

As a user, Flight Control tracks each piece of work from idea to done.

- [ ] New `afc/cli_plan.py` registered in `afc/cli.py` like `cli_health.py`: `plan`, `plan add`,
      `plan start`, `plan done` (design §5.4 for exactly what each does).
- [ ] `plan` returns `{"goal", "now": {"id","title","spec","next_slice"} or null, "next": [max 2],
      "done_count"}`.
- [ ] `plan done` moves the spec file to `plan/archive/`, fills its Shipped section, adds the Done
      row and an `plan/archive/index.md` row, clears Now, logs it, compacts, returns `suggest_next`.
- [ ] Plain errors for: no master plan, unknown ID, another spec in progress, starting one not in
      Next, finishing one not in Now, open slices, no slices yet, spec file missing, empty title.
- [ ] `plan add` creates `plan/specs/` and `plan/archive/` if an older workspace lacks them.

**Tests:** new `tests/test_cli_plan.py` using `CliTestCase`: the full add → start → done flow, one in
progress at a time, refusals leave the master plan unchanged, old workspace without folders.

## MP-4 · Status and welcome show the active spec

As a returning user, I see which spec I'm on and the next slice.

- [ ] `afc/plan.py`: `now_line(ws)` → `"S-002 <title> (next slice: <label>)"`, or `""`.
- [ ] `status` → `now` uses `now_line` when `master-plan.md` exists, else the old `progress.md` text.
- [ ] Welcome context adds `Active spec: <now_line>.` for a returning user.

**Tests:** `tests/test_plan.py`, `tests/test_cli.py`, `tests/test_session_start.py`.

## MP-5 · Specs are searchable

As Flight Control, I can find old decisions without reading the archive every session.

- [ ] `afc/index.py` `_doc_files` also indexes `plan/specs/*.md` and `plan/archive/*.md`.

**Tests:** `tests/test_index.py`: a word in a spec and a word in an archived spec are both found.

## MP-6 · Old projects get upgraded

As a user with an older project, a repair moves me to the master plan without losing anything.

- [ ] `afc/cli_health.py`: new fixable problem `old_plan_format` (has `progress.md`, no
      `master-plan.md`).
- [ ] `repair` adds `master-plan.md`, carries the old text over under `## Earlier progress`, creates
      the folders, and moves `progress.md` to `plan/archive/progress-legacy.md`.

**Tests:** `tests/test_cli_health.py`: check finds it, repair fixes it, `plan` then works.

## MP-7 · Skills work through the master plan

As a user, the conversation follows the plan: the goal becomes specs, slices tick off, finished specs
archive.

- [ ] **afc-interview:** after the intent, add two to five specs (`plan add`), fill their Goal, "You'll
      know it works when" and Slices, tell the user the plan in three to five lines, ask one question:
      start with the first? Then `plan start`. Never ask the user to approve a spec file.
- [ ] **afc-slice:** take the next slice from `plan`; on yes, tick it in the spec; when none are left,
      `plan done` and offer the suggested next spec. No more `progress.md`.
- [ ] **afc-drift:** a new goal inside the intent becomes `plan add`.
- [ ] **afc-deliver:** commits and PRs name the spec ID; the PR lists `master-plan.md`.
- [ ] **/afc:** summary uses `plan`; More… gains **Master plan** (Now, Next two at a time, recent Done).

**Tests:** `tests/test_content.py`: interview names `plan add` and `plan start`, slice names `plan`
and `plan done`, no `progress.md` under `.claude/`, `/afc` has **Master plan**.

## MP-8 · Docs and end-to-end check

As a new user, the README tells me Flight Control keeps a master plan and an archive.

- [ ] README "How a session goes": one sentence on the master plan and archive (keep the phrase
      "from your own"). CONTRIBUTING: add `afc/plan.py` and `afc/cli_plan.py`.
- [ ] In a developer clone with a scratch `AFC_HOME`: `new`, `plan add`, `plan start`, tick a slice,
      `plan done`, `plan` shows `done_count: 1`; finish with `remove --code`.
- [ ] Full suite passes on every installed Python (`python3`, `python3.12`).
