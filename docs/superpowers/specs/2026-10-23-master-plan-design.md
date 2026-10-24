# Master plan, specs and archive — design

Date: 2026-10-23. Status: draft for the owner. Builds on
`docs/superpowers/specs/2026-10-21-flight-control-design.md` (the Flight Control design).

## 1. Why

Flight Control keeps a short Now/Next/Done list per project (`plan/progress.md`). That works for one
slice at a time, but a project made of several features has no place for:

- the whole picture: which pieces of work the goal breaks into, in order;
- what a piece of work must do before it counts as finished;
- a record of finished work that doesn't bloat the files Claude reads every session.

AgToosa (the owner's earlier framework, `DreamToosa/Docs/`) solves this with a `Master-Plan.md`, one
spec per story and a `Docs/archived/` folder. It works, but it is heavy: a 487-line spec format,
cycles and story points, evidence and review files, and it lives inside the app repo. This design
brings the backbone over in Flight Control's own style.

## 2. What AgToosa does (studied 2026-10-23)

| AgToosa piece | What it does | Keep? |
|---|---|---|
| `Master-Plan.md` | Charter, active cycle, active tasks, backlog, epics, completed (pointer rows), update log, decisions | **Keep the idea**, far fewer sections |
| `spec-DEV-NNN.md` | Goal contract, EARS acceptance criteria, design, STRIDE, task tree, waves, test plan, approval marker | **Keep a short form**; no approval marker (the user approves slices, not specs) |
| `/agtoosa-ship` archive step | Moves spec/review/evidence to `Docs/archived/`, adds a pointer row, prunes the plan | **Keep** |
| Compaction | Over ~200 lines: snapshot the cycle, drop done rows, rotate the update log at 150 rows | **Keep, simplified** |
| `/agtoosa-next` | Reads state, dispatches spec → build → review → ship, or suggests the next backlog story | **Keep** as a read-only `plan` command plus skill routing |
| Cycles, story points, epics | Sprint bookkeeping | Leave out |
| Review and evidence files, capability deltas, version bumps | Heavy governance | Leave out for now (later candidates) |

## 3. Goals

- Each project has one **master plan**: the goal in a line, what's being built now, what's next in
  order, and what's done.
- Each piece of work is a **spec**: small, written by Flight Control, made of slices the user checks.
- Finished specs move to an **archive** with a pointer left behind, so nothing is lost and the plan
  stays short enough to read every session.
- A deterministic command tells Claude where the project stands and what comes next.

## 4. Non-goals and anti-goals

- **Not** asking the user to read or approve spec documents. The user agrees to a two-or-three-line
  summary in chat and approves working slices, as today.
- **Not** sprint cycles, points, epics, review/evidence files or version bumps.
- **Not** putting any of this in the app repo. It lives in the private workspace (`~/.A-FC/`).
- Failure even if it works: a master plan that grows past ~200 lines, a spec over ~120 lines, or
  Claude loading archived specs it doesn't need.

## 5. Design

### 5.1 Files in the workspace

```
~/.A-FC/projects/<name>/plan/
  intent.md          unchanged (the goal, in the user's words)
  master-plan.md     NEW, replaces progress.md
  decisions.md       unchanged
  architecture.md    unchanged
  drift-notes.md     unchanged
  process-steps.md   unchanged
  specs/             NEW: S-001-<slug>.md … one file per spec not yet done
  archive/           NEW: finished specs, index.md, updatelog-<year>.md
```

### 5.2 master-plan.md

Markdown is the source of truth, as everywhere in Flight Control. The `flight-control` commands own
the table rows; Claude may edit prose and reorder `Next` rows by hand.

```markdown
# Master plan

## Goal

<one line from intent.md>. Full intent: [intent.md](intent.md).

## Now

| ID | Title | Size | Spec | Started |
|---|---|---|---|---|

## Next

| ID | Title | Size | Spec |
|---|---|---|---|

## Done

| ID | Title | Done | Spec |
|---|---|---|---|

## Update log

| Date | Event |
|---|---|
```

- `Now` holds at most one spec.
- `Next` is in priority order, top first.
- `Done` keeps the 10 newest rows; older rows live only in `archive/index.md`.
- `Update log` keeps 100 rows; older rows move to `archive/updatelog-<year>.md` (appended, never
  lost).
- Size is `S`, `M` or `L`.
- The `## Now` heading stays, so the existing `status` → `now` field keeps working.

### 5.3 A spec

`plan/specs/S-001-<slug>.md`, IDs counted per project. Target under 120 lines.

```markdown
# S-001 — <title>

Size: M · Status: next · Started: - · Done: -

## Goal

What this piece does and why, in two or three lines.

## You'll know it works when

- When <situation>, then <result the user can see>.

## Out of scope

## Design notes

What it touches (auth, api, data, deploy, logs, deps, input) and a mini threat check, at most five
rows (Threat | STRIDE category | Mitigation).

## Slices

- [ ] 1. <label> — you'll check it by <how>

## Decisions

## Shipped

(Filled in when done: date, slices, commits.)
```

### 5.4 Lifecycle

```
spec new  ──►  Next  ──spec start──►  Now  ──(slices approved one by one)──►  spec done  ──►  archive
```

- **new**: allocates the next ID, writes the spec file from the template, adds a `Next` row.
- **start**: moves the row from `Next` to `Now`, stamps the status and start date. Refused while
  another spec is in `Now`.
- **done**: refused while any slice is unticked. Moves the spec file to `archive/`, fills its
  `Shipped` section, adds a `Done` row (with the archive link) and an `archive/index.md` row, clears
  `Now`, logs it, compacts the plan if needed, and returns the top `Next` row as the suggestion.
- Ticking a slice is done by Claude in the spec file, after the user says yes to the slice.

### 5.5 Commands

| Command | Does |
|---|---|
| `sh bin/afc plan` | Reads only. Returns the active spec (id, title, spec path), its next open slice, the first two `Next` rows, and the done count |
| `sh bin/afc spec new --title "…" [--size S\|M\|L]` | As in 5.4 |
| `sh bin/afc spec start <id>` | As in 5.4 |
| `sh bin/afc spec done <id>` | As in 5.4 |

All act on the active project. All print one JSON object; errors are plain sentences.

### 5.6 How the flow changes

- **afc-interview**: after writing `intent.md`, break the goal into two to five specs, smallest
  useful first, with `spec new`, fill each spec's Goal and "You'll know it works when", then give the
  user the master plan in three to five plain lines and ask one question: start with the first one?
  `spec start` on yes.
- **afc-slice**: pick the next open slice of the active spec (`plan` tells you). On yes: tick it in
  the spec, add any decision, then the existing steps. When no slices are left: `spec done`, tell the
  user in one line, and offer the suggested next spec.
- **afc-drift**: a new goal becomes a new spec in `Next` (or changes the intent, as today).
- **afc-start** (returning) and **/afc**: show the active spec and its next slice; /afc → More…
  gains "Master plan" (shows Now, Next and the last few Done, two at a time).
- **Welcome context**: adds `Active spec: S-002 <title>; next slice: <label>.` when there is one.
- **afc-deliver**: commit messages and PR text name the spec ID.

### 5.7 Index and health

- The project index also indexes `plan/specs/*.md` and `plan/archive/*.md`, so old decisions stay
  searchable without being read every session.
- Health check: a workspace with `progress.md` but no `master-plan.md` is an `old_plan_format`
  problem; `repair` creates `master-plan.md`, carries the old Now/Next/Done text over under a
  `## Earlier progress` note, and moves `progress.md` to `archive/progress-legacy.md`.

## 6. Constraints

- Standard library Python only; files under 500 lines; every new command tested.
- Skills stay within their size limits and load only what the step needs.
- No project data in the A-FC repo.

## 7. Calls made in this design (Claude's, for the owner to check)

- Specs are internal working documents; the user agrees to summaries and approves slices.
- One spec in progress at a time.
- Markdown stays the source of truth.
- `master-plan.md` replaces `progress.md` rather than living beside it.
- No sprint cycles or story points; size is S/M/L only.

## 8. Left to the builder

Table parsing details, slug rules, exact JSON keys beyond those named, wording of plain errors.

## 9. Later candidates

Living system spec (AgToosa's capability deltas folded into `architecture.md`), review notes per
spec, release/version notes per milestone, a `spec pause` command.
