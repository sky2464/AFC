# Master plan, specs and archive — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Flight Control project a master plan, short specs made of slices, and an archive of finished specs, driven by `sh bin/afc plan` and `sh bin/afc spec new|start|done`.

**Architecture:** Markdown in the private workspace stays the source of truth. A new pure module `afc/plan.py` reads and writes the master plan's tables and spec files; a new command module `afc/cli_plan.py` (registered like `cli_projects.py`) exposes the commands. Skills route the conversation through them.

**Tech Stack:** Python 3.10+ standard library only, `unittest`, markdown skills.

**Spec:** `docs/superpowers/specs/2026-10-23-master-plan-design.md` (read it before each task).

## Global Constraints

- Standard library Python only; every file under 500 lines (`tests/test_content.py` enforces it).
- Every command prints one JSON object; failures raise `afc.cli.CliError` with a plain sentence.
- Nothing is ever deleted: finished specs and old files move to `plan/archive/`.
- No project data in the A-FC repo; all of this lives in `~/.A-FC/projects/<name>/plan/`.
- Spec IDs: `S-001`, `S-002`, … counted per project, never reused.
- Size is one of `S`, `M`, `L` (default `M`). At most one spec in `Now`.
- `Done` keeps the 10 newest rows (newest first); `Update log` keeps 100 rows (oldest first).
- Editing Flight Control needs maintenance mode: run `sh bin/afc maintain on` before a task and
  `sh bin/afc maintain off` after its commit. Work on the `dev` branch; one commit per task.
- Run tests with `python3 -m unittest discover -s tests` (also with `python3.12` if installed).

## Review Focus

1. A title containing `|` or a line break must not break the tables: cells replace `|` with `/` and
   collapse whitespace (test in Task 2).
2. A spec file deleted by hand: `spec start`/`spec done` fail with a plain error and leave the master
   plan untouched (test in Task 3).
3. A workspace made before this change (no `plan/specs/` or `plan/archive/`): `spec new` creates the
   folders (test in Task 3).
4. A spec with no slices listed can't be marked done: "S-001 has no slices yet." (test in Task 3).
5. IDs are never reused after a spec is archived (test in Task 2).

---

### Task 1: Templates and workspace layout

**Files:**
- Create: `templates/workspace/plan/master-plan.md`, `templates/workspace/spec.md`
- Delete: `templates/workspace/plan/progress.md` (`git rm`)
- Modify: `afc/workspace.py`
- Test: `tests/test_workspace.py`, `tests/test_content.py`

**Interfaces:**
- Produces: `afc.workspace.PLAN_SUBDIRS = ("specs", "archive")`; `create_workspace()` also creates
  `plan/specs/` and `plan/archive/`. Template placeholders in `spec.md`: `{id}`, `{title}`, `{size}`.

- [ ] **Step 1: Update the tests**
  - In `tests/test_workspace.py`: replace `"progress.md"` with `"master-plan.md"` in `PLAN_FILES`;
    in `test_plan_templates_are_copied_with_headings` compare only files
    (`sorted(p.name for p in plan.iterdir() if p.is_file())`); add
    `test_plan_subfolders`: `(ws/"plan"/"specs").is_dir()` and `(ws/"plan"/"archive").is_dir()`.
  - In `tests/test_content.py`: rename `test_progress_template_sections` to
    `test_master_plan_template_sections`, reading `templates/workspace/plan/master-plan.md`, expecting
    headings `["Goal", "Now", "Next", "Done", "Update log"]`; add `test_spec_template_sections`
    reading `templates/workspace/spec.md`, expecting headings
    `["Goal", "You'll know it works when", "Out of scope", "Design notes", "Slices", "Decisions", "Shipped"]`
    and the first line `"# {id} — {title}"`.
- [ ] **Step 2: Run them, expect failures**: `python3 -m unittest tests.test_workspace tests.test_content`
- [ ] **Step 3: Write both templates** exactly as in the design §5.2 and §5.3. Table headers, in order:
  Now `| ID | Title | Size | Spec | Started |`, Next `| ID | Title | Size | Spec |`,
  Done `| ID | Title | Done | Spec |`, Update log `| Date | Event |`, each followed by
  `|---|…|` and no rows. Spec header line: `Size: {size} · Status: next · Started: - · Done: -`.
  `## Slices` holds one commented example line `<!-- - [ ] 1. <label> — you'll check it by <how> -->`.
- [ ] **Step 4: Add `PLAN_SUBDIRS` and create the subfolders** in `create_workspace()`; `git rm` the old
  progress template.
- [ ] **Step 5: Run the full suite, expect PASS** (the status test still writes its own `progress.md`).
- [ ] **Step 6: Commit** `feat: master plan and spec templates in new workspaces`

### Task 2: `afc/plan.py` — tables, IDs, slices, compaction

**Files:**
- Create: `afc/plan.py`, `tests/test_plan.py`

**Interfaces:**
- Produces (all pure or workspace-path based, no CLI imports):
  - `MASTER = "master-plan.md"`
  - `read_rows(text: str, section: str) -> list[dict[str, str]]` — rows of the first table under
    `## <section>`, keyed by header cells; `[]` if the table has no rows. Raises `ValueError` if the
    section or its table is missing.
  - `write_rows(text: str, section: str, rows: list[dict[str, str]]) -> str` — replaces that table's
    body, keeping its header; cells pass through `cell()`.
  - `cell(value: str) -> str` — `|` → `/`, all whitespace runs → one space, stripped.
  - `slugify(title: str) -> str` — lowercase, runs of non `[a-z0-9]` → `-`, strip `-`, cut to 40
    chars, strip a trailing `-`; empty → `"spec"`.
  - `next_id(ws: Path) -> str` — highest `S-(\d+)` found in the master plan's Now/Next/Done tables,
    `plan/archive/index.md`, and file names in `plan/specs/` and `plan/archive/`, plus one,
    formatted `S-%03d`.
  - `open_slices(spec_text: str) -> list[str]` and `all_slices(spec_text: str) -> list[str]` — labels
    of `- [ ] ` (open) or `- [ ]`/`- [x]` (all) lines under `## Slices`, text after the box.
  - `set_header(spec_text: str, **fields: str) -> str` — rewrites `Status:`, `Started:`, `Done:` in
    the spec's header line (keys `status`, `started`, `done`).
  - `log(text: str, date: str, event: str) -> str` — appends a row to `Update log`.
  - `compact(ws: Path) -> None` — keeps 10 `Done` rows; moves the oldest `Update log` rows beyond 100
    into `plan/archive/updatelog-<YYYY>.md` (year from each row's date; create with
    `# Update log <YYYY>` and the table header if new; append, never overwrite).

- [ ] **Step 1: Write failing tests** in `tests/test_plan.py` (use `AfcTestCase`, copy the real
  template from `afc.config.afc_root()/"templates/workspace/plan/master-plan.md"` into a scratch
  workspace):
  - `test_rows_round_trip`: write two Next rows, read them back equal.
  - `test_cell_keeps_tables_intact`: `cell("a | b\nc") == "a / b c"`; a title with `|` written and read
    back gives one row with Title `"a / b c"`.
  - `test_missing_section_raises`: `read_rows("# x\n", "Now")` raises `ValueError`.
  - `test_slugify`: `slugify("Health endpoint!") == "health-endpoint"`, `slugify("!!!") == "spec"`,
    `len(slugify("x" * 80)) == 40`.
  - `test_next_id_counts_archive`: with `plan/archive/S-007-old.md` present and empty tables,
    `next_id(ws) == "S-008"`; with nothing, `"S-001"`.
  - `test_slices`: text with `- [x] 1. a`, `- [ ] 2. b — check` under `## Slices` and a `- [ ] z`
    under another heading → `open_slices == ["2. b — check"]`, `len(all_slices) == 2`.
  - `test_set_header`: `set_header(t, status="in progress", started="2026-10-23")` changes only those.
  - `test_compact`: 12 Done rows → 10 remain (first 10); 105 log rows dated 2025/2026 → 100 remain and
    5 oldest appended to the right `updatelog-<year>.md`.
- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError`): `python3 -m unittest tests.test_plan -v`
- [ ] **Step 3: Implement `afc/plan.py`** to the interfaces above (regex on `^## `, table lines start
  with `|`).
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `feat: plan module for master plan tables, spec ids and slices`

### Task 3: `afc/cli_plan.py` — `plan`, `spec new|start|done`

**Files:**
- Create: `afc/cli_plan.py`, `tests/test_cli_plan.py`
- Modify: `afc/cli.py` (import, `COMMAND_NAMES`, `register` call — same three places as `cli_health`)

**Interfaces:**
- Consumes: everything in Task 2; `afc.cli._active(reg)`, `afc.cli.CliError`, `afc.cli._today()`
  via the late-import `_cli()` pattern used in `afc/cli_projects.py`; templates from
  `afc.config.afc_root()`.
- Produces: `NAMES = ("plan", "spec")`; `register(sub)`; JSON results:
  - `plan` → `{"goal": str, "now": {"id","title","spec","next_slice"} | None, "next": [{"id","title","size"}] (max 2), "done_count": int}`
  - `spec new --title T [--size S|M|L]` → `{"created": id, "title": T, "size": size, "spec": path}`;
    adds a Next row with Spec `[spec](specs/<file>)`; logs `"<id> added"`.
  - `spec start ID` → `{"started": id, "next_slice": str | None}`; moves the row to Now with
    Started = today; sets the spec's status `in progress`; logs `"<id> started"`.
  - `spec done ID` → `{"done": id, "archived": path, "suggest_next": {"id","title"} | None}`; moves
    the spec file to `plan/archive/`, sets status `done` and Done = today, replaces the `## Shipped`
    body with `Shipped <today>. Slices: <n>.`, inserts a Done row at the top with Spec
    `[<id>](archive/<file>)`, inserts the same row at the top of `plan/archive/index.md` (create
    with `# Archive` and `| ID | Title | Done | Spec |` header, link `<file>`), clears Now, logs
    `"<id> done"`, calls `compact()`.
- Errors (exact text): no master plan → `"This project has no master plan yet. A health check repair adds one."`;
  unknown ID → `"No spec <ID> in the master plan."`; start while Now is busy → `"<ID> is still in progress. Finish it first."`;
  start a spec not in Next → `"<ID> isn't waiting in Next."`; done a spec not in Now → `"<ID> isn't in progress."`;
  open slices → `"<ID> still has <n> open slice(s), starting with: <label>"`; no slices →
  `"<ID> has no slices yet."`; spec file missing → `"The spec file for <ID> is missing: <path>"`;
  empty title → `"Give the spec a title."`.

- [ ] **Step 1: Write failing tests** in `tests/test_cli_plan.py` using `CliTestCase` from
  `tests/test_cli.py` (`self.new()` makes an active project whose workspace has the template):
  - `test_new_adds_a_spec_to_next`: ids S-001 then S-002; files exist under `plan/specs/`; `plan`
    shows both in `next`; size defaults to `M`.
  - `test_new_in_an_old_workspace_creates_folders`: delete `plan/specs` and `plan/archive` first.
  - `test_start_moves_to_now`: `plan` → `now.id == "S-001"`, `now.next_slice` is the first open slice
    after the test writes two slices into the spec file; spec header shows `Status: in progress`.
  - `test_only_one_in_progress`: second start → error text above.
  - `test_done_archives_and_suggests_next`: tick all slices, `spec done S-001` → file now in
    `plan/archive/`, Done row present, `archive/index.md` has it, `suggest_next.id == "S-002"`,
    `plan` → `now is None`, `done_count == 1`.
  - `test_done_refused_with_open_or_no_slices` and `test_missing_spec_file_is_plain` (master plan
    text unchanged after the error).
  - `test_no_master_plan` (delete `master-plan.md`) and `test_unknown_id`.
- [ ] **Step 2: Run, expect FAIL**: `python3 -m unittest tests.test_cli_plan -v`
- [ ] **Step 3: Implement `afc/cli_plan.py`** (argparse: `spec` gets its own sub-subparsers, like
  `index` in `afc/cli_index.py`). For `spec done`, write the archive and master plan only after the
  file move succeeds; if a later write fails, move the file back.
- [ ] **Step 4: Run the full suite, expect PASS** (check `afc/cli.py` stays under 500 lines).
- [ ] **Step 5: Commit** `feat: plan and spec commands with archive on done`

### Task 4: Status and welcome show the active spec

**Files:**
- Modify: `afc/plan.py` (add `now_line`), `afc/cli.py` (`_now_text`), `afc/hooks/session_start.py`
- Test: `tests/test_plan.py`, `tests/test_cli.py`, `tests/test_session_start.py`

**Interfaces:**
- Produces: `afc.plan.now_line(ws: Path) -> str` — `""` without a master plan or with an empty Now;
  else `"S-002 <title> (next slice: <label>)"`, or `"S-002 <title> (all slices done)"`.
- `status` → `now`: `now_line(ws)` when `plan/master-plan.md` exists, else the old `progress.md`
  `## Now` text (keep the existing test passing).
- Welcome context (returning user only): append `" Active spec: <now_line>."` after the project line
  when `now_line` is non-empty.

- [ ] **Step 1: Write failing tests**: `test_now_line` (three cases) in `tests/test_plan.py`;
  `test_status_reads_master_plan` in `tests/test_cli.py` (start a spec, `status.now` starts with
  `"S-001 "`); `test_welcome_names_active_spec` in `tests/test_session_start.py` (registry with an
  active project whose workspace holds a master plan with S-001 in Now).
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full suite, expect PASS.**
- [ ] **Step 5: Commit** `feat: status and welcome name the active spec`

### Task 5: Index specs and archive

**Files:**
- Modify: `afc/index.py` (`_doc_files`)
- Test: `tests/test_index.py`

**Interfaces:**
- `_doc_files` also returns `("plan", "plan/specs/<f>.md", p)` and `("plan", "plan/archive/<f>.md", p)`
  for `*.md` files in those folders (sorted by rel; missing folders are fine).

- [ ] **Step 1: Write the failing test** `test_specs_and_archive_are_searchable`: write
  `plan/specs/S-001-x.md` containing `"quokka"` and `plan/archive/S-000-y.md` containing `"wombat"`,
  rebuild the project index, `search(db, "quokka")[0]["path"] == "plan/specs/S-001-x.md"`, and the
  same for `"wombat"`.
- [ ] **Step 2: Run, expect FAIL.**  **Step 3: Implement.**  **Step 4: Run the full suite, expect PASS.**
- [ ] **Step 5: Commit** `feat: index specs and archived specs`

### Task 6: Health check upgrades old workspaces

**Files:**
- Modify: `afc/cli_health.py` (`find_problems`, `cmd_repair`)
- Test: `tests/test_cli_health.py`

**Interfaces:**
- New problem: `{"kind": "old_plan_format", "project": name, "path": <plan dir>, "fixable": True,
  "detail": "<name>: still uses the old progress list; repair upgrades it to a master plan."}` when
  `plan/progress.md` exists and `plan/master-plan.md` doesn't (only for workspaces that exist).
- Repair: copy the master-plan template into `plan/`, append `"\n## Earlier progress\n\n"` plus the
  old file's text without its first `# ` heading line, create `plan/specs/` and `plan/archive/`, move
  `progress.md` to `plan/archive/progress-legacy.md`; repaired line
  `"Upgraded <name> to a master plan."`.

- [ ] **Step 1: Write the failing test** `test_old_progress_list_is_upgraded`: replace the new
  workspace's `master-plan.md` with a `progress.md` containing `"# Progress\n\n## Now\n\nold slice\n"`;
  `check` lists `old_plan_format`; `repair` → `master-plan.md` exists and contains `"old slice"` under
  `## Earlier progress`, `archive/progress-legacy.md` exists, `left == []`, and `plan` works.
- [ ] **Step 2: Run, expect FAIL.**  **Step 3: Implement.**  **Step 4: Run the full suite, expect PASS.**
- [ ] **Step 5: Commit** `feat: health repair upgrades old progress lists to a master plan`

### Task 7: Skills and /afc follow the master plan

**Files:**
- Modify: `.claude/skills/afc-interview/SKILL.md`, `.claude/skills/afc-slice/SKILL.md`,
  `.claude/skills/afc-drift/SKILL.md`, `.claude/skills/afc-deliver/SKILL.md`,
  `.claude/skills/afc-start/SKILL.md`, `.claude/commands/afc.md`
- Test: `tests/test_content.py`

**Interfaces (wording to add; keep each skill's existing rules and its line limit):**
- **afc-interview, "Write the intent" → after it:** "Break the goal into two to five specs, smallest
  useful first: `sh bin/afc spec new --title "<title>" --size <S|M|L>` for each, then fill each spec's
  Goal, You'll know it works when, and Slices. Tell the user the plan in three to five plain lines and
  ask one question: start with the first one? On yes, `sh bin/afc spec start <id>` and hand off to
  `afc-slice`." Never ask the user to read or approve a spec file.
- **afc-slice:** "Pick the slice" uses `sh bin/afc plan` (the active spec's next open slice) instead of
  editing `progress.md`; no active spec → start the top `Next` spec (`sh bin/afc spec start <id>`)
  after a one-line summary, or use `afc-interview` if there are no specs. "On yes": tick the slice in
  the spec file (`- [x]`), add decisions there and in `decisions.md`; when `plan` shows no open slice
  left, run `sh bin/afc spec done <id>`, tell the user in one line, and offer the suggested next spec
  as step 1. Remove every `progress.md` instruction.
- **afc-drift:** a new goal that fits the intent becomes `sh bin/afc spec new` (lands in Next); one
  that changes the intent follows the existing path.
- **afc-deliver:** commit messages and PR text name the spec ID (e.g. `S-002: health endpoint`); the
  PR body lists `master-plan.md` instead of `progress.md`.
- **afc-start (Returning):** the "last" detail may use the active spec from the context line.
- **/afc:** the normal summary uses `sh bin/afc plan` (active spec and next slice); add More… item
  **Master plan** after Project details: "`sh bin/afc plan`; show Now, then Next two at a time, then the
  last few Done. Finished specs are in the workspace's `plan/archive/`." Renumber the rest.
- [ ] **Step 1: Write failing content tests**: afc-interview contains `"sh bin/afc spec new"` and
  `"sh bin/afc spec start"`; afc-slice contains `"sh bin/afc plan"` and `"sh bin/afc spec done"`;
  no file under `.claude/` contains `"progress.md"`; `afc.md` contains `"**Master plan**"`.
- [ ] **Step 2: Run, expect FAIL.**  **Step 3: Edit the skills.**  **Step 4: Run the full suite, expect PASS.**
- [ ] **Step 5: Commit** `feat: skills drive work through the master plan`

### Task 8: User docs and end-to-end check

**Files:**
- Modify: `README.md` ("How a session goes": one sentence that Flight Control keeps a master plan of
  specs and moves finished ones to an archive in the private workspace), `CONTRIBUTING.md` (add
  `afc/plan.py` and `afc/cli_plan.py` to "What lives where").

- [ ] **Step 1: Edit both docs** (keep `"from your own"` in README; `tests/test_content.py` checks it).
- [ ] **Step 2: End-to-end with a scratch home** (all must print JSON, no errors):

```bash
export AFC_HOME="$(mktemp -d)"
sh bin/afc new --name demo-app --parent "$(mktemp -d)" --git-name Demo --git-email demo@example.com
sh bin/afc spec new --title "Health endpoint" --size S
sh bin/afc spec start S-001
sh bin/afc plan
```

  Then add `- [x] 1. ok` under `## Slices` in the spec file, run `sh bin/afc spec done S-001`, and
  `sh bin/afc plan` shows `"done_count": 1`. Finish with `sh bin/afc remove demo-app --code` (it
  clears the folder access `new` granted in this checkout's `.claude/settings.local.json`), then
  `unset AFC_HOME`. Run this in your developer clone, never in the folder you use day to day.
- [ ] **Step 3: Full suite on every installed Python** (`python3`, `python3.12`), expect OK.
- [ ] **Step 4: Commit** `docs: master plan in README and contributor guide`
